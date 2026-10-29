import uuid
from dataclasses import dataclass

from injector import inject

from internal.model import App
from pkg.sqlalchemy import SQLAlchemy
from internal.schema import CreateAppForm,UpdateAppForm
from internal.exception import NotFoundException
from internal.log import get_logging_by_file
from pkg.utils.json_util import JsonUtil
logger = get_logging_by_file(__file__)

@inject
@dataclass
class SeqService:
    """应用服务逻辑"""
    db: SQLAlchemy

    def create_app(self, form: CreateAppForm) -> App:
        with self.db.auto_commit():
            # 1.创建模型的实体类
            account_id: str = str(uuid.uuid4())
            app = App(
                name=form.name.data,
                account_id=account_id,
                icon=form.icon.data,
                config=form.config.data
            )
            # 2.将实体类添加到session会话中
            self.db.session.add(app)
        return app

    def get_app(self, id: str) -> App:

        app = self.db.session.query(App).get(id)
        if not app:
            logger.error("未查询到数据")
            raise NotFoundException("未查询到数据")
        logger.info(f"查询到App数据, app_id:{id}, data:{JsonUtil.to_json_str_truncate(app)}")
        return app

    def update_app(self, form: UpdateAppForm) -> App:
        with self.db.auto_commit():
            app = self.get_app(form.id.data)
            app.name = form.name.data
            app.icon = form.icon.data
        return app

    def delete_app(self, id: str) -> App:
        with self.db.auto_commit():
            app = self.get_app(id)
            if not app:
                logger.error("未查询到数据,查询失败")
                raise NotFoundException("未查询到数据,查询失败")
            self.db.session.delete(app)
        return app