from dataclasses import dataclass

from flask import Flask,Blueprint
from injector import inject

from internal.handler import AppHandler,SqlHandler


@inject
@dataclass
class Router:

    app_handler: AppHandler
    sql_handler: SqlHandler

    """ 路由 """
    def register_router(self, app: Flask):
        """ 注册路由 """
        #  1. 创建一个蓝图
        bp = Blueprint("router", __name__, url_prefix="/yzy")

        # 2. 将url与对应的控制器方法做绑定
        bp.add_url_rule("/ping",view_func=self.app_handler.ping, methods=["POST"])
        bp.add_url_rule("/pingGet",view_func=self.app_handler.pingGet, methods=["GET"])
        # add
        bp.add_url_rule("/add",view_func=self.sql_handler.add, methods=["POST"])

        # update
        bp.add_url_rule("/update",view_func=self.sql_handler.update, methods=["POST"])

        # get
        bp.add_url_rule("/get/<string:id>",view_func=self.sql_handler.get, methods=["GET"])

        # del
        bp.add_url_rule("/delete/<string:id>",view_func=self.sql_handler.delete, methods=["GET"])


        # 3. 在应用上注册蓝图
        app.register_blueprint(bp)

