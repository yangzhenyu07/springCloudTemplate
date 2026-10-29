
from flask_migrate import Migrate
from injector import Module, Binder

from internal.extension.database_extension import db
from internal.extension.migrate_extension import migrate
from pkg.sqlalchemy import SQLAlchemy


class ExtensionModule(Module):
    """扩展模块的依赖注入"""

    def configure(self, binder: Binder) -> None:
        # binder.bind 等价于 java 中的`@Bean`，往容器注册 Bean
        # 重写的 `SQLAlchemy` 的实例
        binder.bind(SQLAlchemy, to=db)
        # flask_migrate.Migrate 的实例，用来做数据库迁移
        binder.bind(Migrate, to=migrate)
