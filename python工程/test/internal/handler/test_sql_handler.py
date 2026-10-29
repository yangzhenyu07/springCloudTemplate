"""
TestSqlHandler 单元测试：增(add) / 查(get) / 改(update) / 删(delete)

核心约定
--------
1. 真实调用：通过 Flask test_client 打真实路由，完整走
   test_client → Router → SqlHandler → SeqService → SQLAlchemy → PostgreSQL，
   全程不使用 mock / patch；接口返回的业务码要用 db.session 回查数据库做二次校验。
2. 数据自净：用例造出来的数据统一登记进 id 池，用例结束（无论通过还是失败）
   自动从库里删除，不污染 yzy_db。

运行方式
--------
    ./yzy/Scripts/python.exe -m pytest test/internal/handler/test_sql_handler.py -v -s

前置条件
--------
1. PostgreSQL 已启动，.env 中的 yzy_db 可连（postgresql://yzy:yzy@127.0.0.1:5432/yzy_db）
2. app 表已创建（见 sql/init.sql）
3. 注意：FLASK_ENV=development 时，非 CustomException 的异常会被 Http 直接 re-raise，
   因此这里只断言「业务异常」（校验失败 / 数据不存在）的返回码，不断言数据库底层异常。
"""
import uuid

import pytest

from app.http.app import app as flask_app
from internal.extension.database_extension import db
from internal.model import App
from pkg.response import HttpCode


# ============================ fixtures & 辅助函数 ============================

@pytest.fixture(autouse=True)
def _quiet_sql():
    """测试期间关闭 SQL echo，否则 -s 模式下 SQL 日志会把断言输出淹掉"""
    with flask_app.app_context():
        engine = db.engine
        origin = engine.echo
        engine.echo = False
    yield
    with flask_app.app_context():
        db.engine.echo = origin


@pytest.fixture
def tracker():
    """登记本用例造出来的数据（id + name），yield 之后统一清理"""
    t = {"ids": [], "names": []}
    yield t
    _cleanup(t)


def _cleanup(t):
    """删除测试数据，id 与 name 双条件兜底，防止某条数据没拿到 id 时漏删。
    清理失败只告警不抛错，避免掩盖用例本身的失败。
    """
    ids, names = t["ids"], t["names"]
    if not ids and not names:
        return
    with flask_app.app_context():
        try:
            if ids:
                db.session.query(App).filter(App.id.in_(ids)).delete(synchronize_session=False)
            if names:
                db.session.query(App).filter(App.name.in_(names)).delete(synchronize_session=False)
            db.session.commit()
        except Exception as e:  # noqa: BLE001
            db.session.rollback()
            print(f"[warn] 清理测试数据失败, ids={ids}, names={names}, err={e}")


def _fetch(app_id):
    """按 id 回查数据库，返回 dict。
    注意：离开 app_context 后 ORM 实例会 detach，属性访问会报 DetachedInstanceError，
    所以这里在 context 内部先转成 dict 再返回。
    """
    with flask_app.app_context():
        row = db.session.query(App).filter(App.id == app_id).first()
        return row.to_dict() if row else None


def _create_app(client, t, name_prefix="ut_app"):
    """通过【真实的 add 接口】造一条数据，返回 (app_id, payload, resp)

    add 接口目前只返回 "新增成功" 提示语、不带 id（见 SqlHandler.add），
    所以新增后回查数据库拿 id，用于后续的 get / update / delete 用例。
    造出来的数据会同时登记 id 和 name 到 tracker，用例结束自动清理。
    """
    name = f"{name_prefix}_{uuid.uuid4().hex[:8]}"
    payload = {
        "name": name,
        "icon": f"https://cdn.example.com/{name}.png",
        "config": {"model": "gpt", "temperature": 0.7},
    }
    resp = client.post("/yzy/add", json=payload)
    assert resp.status_code == 200
    assert resp.json["code"] == HttpCode.SUCCESS

    with flask_app.app_context():
        row = (
            db.session.query(App)
            .filter(App.name == name)
            .order_by(App.created_at.desc())
            .first()
        )
        assert row is not None, "add 接口返回成功，但库中查不到数据"
        app_id = str(row.id)

    t["ids"].append(app_id)
    t["names"].append(name)
    return app_id, payload, resp


class TestSqlHandler:
    """SqlHandler 增删改查 —— 真实调用测试类"""

    # ============================== 增：add ==============================

    def test_add_success(self, client, tracker):
        """正常新增：接口返回 success，且数据真实落库、字段与请求一致"""
        app_id, payload, resp = _create_app(client, tracker)

        assert resp.status_code == 200
        assert resp.json["code"] == HttpCode.SUCCESS
        assert resp.json["data"] == "新增成功"

        # 回查数据库，校验真实落库结果
        row = _fetch(app_id)
        assert row is not None
        assert row["name"] == payload["name"]
        assert row["icon"] == payload["icon"]
        assert row["config"] == payload["config"]
        # id / account_id 由服务端生成，校验是合法 UUID
        assert uuid.UUID(row["id"]) == uuid.UUID(app_id)
        assert uuid.UUID(row["account_id"])
        # 时间字段非空
        assert row["created_at"] and row["updated_at"]

    @pytest.mark.parametrize("payload, case", [
        ({}, "空 payload"),
        ({"icon": "https://x.com/a.png", "config": {}}, "缺少必填的 name"),
        ({"name": "", "config": {}}, "name 为空字符串"),
        ({"name": "a" * 256, "config": {}}, "name 超长(>255)"),
    ])
    def test_add_validate_error(self, payload, case, client, tracker):
        """参数校验失败：返回 validate_error，且错误信息能定位到具体字段"""
        resp = client.post("/yzy/add", json=payload)
        assert resp.status_code == 200, case
        assert resp.json["code"] == HttpCode.VALIDATE_ERROR, case
        # ValidateErrorException 把 wtforms 的 errors 原样带回
        assert resp.json["data"], case

    # ============================== 查：get ==============================

    def test_get_success(self, client, tracker):
        """正常查询：返回数据与库中一致"""
        app_id, payload, _ = _create_app(client, tracker)

        resp = client.get(f"/yzy/get/{app_id}")
        assert resp.status_code == 200
        assert resp.json["code"] == HttpCode.SUCCESS

        data = resp.json["data"]
        assert data["id"] == app_id
        assert data["name"] == payload["name"]
        assert data["icon"] == payload["icon"]
        assert data["config"] == payload["config"]

        # 接口返回与数据库直查结果比对
        assert data["name"] == _fetch(app_id)["name"]

    def test_get_not_found(self, client):
        """查询不存在的 id：返回 not_found"""
        not_exist_id = str(uuid.uuid4())
        resp = client.get(f"/yzy/get/{not_exist_id}")
        assert resp.status_code == 200
        assert resp.json["code"] == HttpCode.NOT_FOUND

    def test_get_created_at_is_not_null(self, client, tracker):
        """查询结果的 created_at / updated_at 有值（校验 default 生效）"""
        app_id, _, _ = _create_app(client, tracker)
        data = client.get(f"/yzy/get/{app_id}").json["data"]
        assert data["created_at"] is not None
        assert data["updated_at"] is not None

    # ============================== 改：update ==============================

    def test_update_success(self, client, tracker):
        """正常更新：接口返回更新后的完整数据，且库中已真实变更"""
        app_id, payload, _ = _create_app(client, tracker)

        new_name = f"ut_app_updated_{uuid.uuid4().hex[:8]}"
        new_icon = "https://cdn.example.com/updated.png"
        resp = client.post("/yzy/update", json={
            "id": app_id,
            "name": new_name,
            "icon": new_icon,
            "config": {"model": "claude"},
        })
        assert resp.status_code == 200
        assert resp.json["code"] == HttpCode.SUCCESS

        data = resp.json["data"]
        assert data["id"] == app_id
        assert data["name"] == new_name
        assert data["icon"] == new_icon

        # 回查数据库确认真实更新
        row = _fetch(app_id)
        assert row["name"] == new_name
        assert row["icon"] == new_icon
        # update_app 只改 name / icon，config 不应被改动
        assert row["config"] == payload["config"]

    def test_update_not_found(self, client):
        """更新不存在的 id：返回 not_found"""
        resp = client.post("/yzy/update", json={
            "id": str(uuid.uuid4()),
            "name": "whatever",
            "icon": "https://x.com/a.png",
            "config": {},
        })
        assert resp.status_code == 200
        assert resp.json["code"] == HttpCode.NOT_FOUND

    @pytest.mark.parametrize("payload, case", [
        ({"name": "new_name"}, "缺少 id"),
        ({"id": "dummy", "icon": "https://x.com/a.png"}, "缺少 name"),
    ])
    def test_update_validate_error(self, payload, case, client, tracker):
        """更新参数校验失败：返回 validate_error，且不改动库中数据"""
        app_id, origin, _ = _create_app(client, tracker)
        payload = dict(payload)  # parametrize 的参数是共享对象，拷贝一份避免污染其他用例
        if payload.get("id") == "dummy":
            payload["id"] = app_id

        resp = client.post("/yzy/update", json=payload)
        assert resp.status_code == 200, case
        assert resp.json["code"] == HttpCode.VALIDATE_ERROR, case

        # 校验失败的数据不应落库
        row = _fetch(app_id)
        assert row["name"] == origin["name"], case
        assert row["icon"] == origin["icon"], case

    # ============================== 删：delete ==============================

    def test_delete_success(self, client, tracker):
        """正常删除：接口返回成功，且库中数据真实消失"""
        app_id, _, _ = _create_app(client, tracker)
        assert _fetch(app_id) is not None

        resp = client.get(f"/yzy/delete/{app_id}")
        assert resp.status_code == 200
        assert resp.json["code"] == HttpCode.SUCCESS
        assert resp.json["data"] == "删除成功"

        assert _fetch(app_id) is None, "接口返回删除成功，但库中数据仍在"

        # 删除后再查，应为 not_found
        assert client.get(f"/yzy/get/{app_id}").json["code"] == HttpCode.NOT_FOUND

    def test_delete_not_found(self, client):
        """删除不存在的 id：返回 not_found"""
        resp = client.get(f"/yzy/delete/{str(uuid.uuid4())}")
        assert resp.status_code == 200
        assert resp.json["code"] == HttpCode.NOT_FOUND

    # ============================== 全链路 ==============================

    def test_crud_flow(self, client, tracker):
        """完整链路：增 → 查 → 改 → 查 → 删 → 查，逐步校验状态一致性"""
        # 1. 增
        app_id, payload, _ = _create_app(client, tracker)

        # 2. 查：与新增时的 payload 一致
        data = client.get(f"/yzy/get/{app_id}").json["data"]
        assert data["name"] == payload["name"]
        assert data["icon"] == payload["icon"]

        # 3. 改
        new_name = f"ut_app_flow_{uuid.uuid4().hex[:8]}"
        resp = client.post("/yzy/update", json={
            "id": app_id, "name": new_name, "icon": "icon_flow", "config": {},
        })
        assert resp.json["code"] == HttpCode.SUCCESS

        # 4. 查：应拿到新值
        data = client.get(f"/yzy/get/{app_id}").json["data"]
        assert data["name"] == new_name
        assert data["icon"] == "icon_flow"
        assert _fetch(app_id)["name"] == new_name

        # 5. 删
        assert client.get(f"/yzy/delete/{app_id}").json["code"] == HttpCode.SUCCESS
        assert _fetch(app_id) is None

        # 6. 查：已删除，返回 not_found
        assert client.get(f"/yzy/get/{app_id}").json["code"] == HttpCode.NOT_FOUND
