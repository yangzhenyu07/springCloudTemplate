import pytest

from pkg.response import HttpCode



class TestAppHandler:
    """app控制器的测试类"""

    # parametrize：参数化装饰器，会自动生成2组测试用例
    # 第1组：data = None
    # 第2组：data = "你好，你是谁?"
    @pytest.mark.parametrize("data", [None, "你好，你是谁?"])
    def test_ping(self, data, client):
        # 向接口 POST 请求，json body 携带 data1=query
        resp = client.post("/yzy/ping", json={"data": data})
        # 分支判断：根据 query 的值校验业务返回码
        assert resp.status_code == 200
        if data is None:
            assert resp.json.get("code") == HttpCode.VALIDATE_ERROR
        else:
            assert resp.json.get("code") == HttpCode.SUCCESS