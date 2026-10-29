from injector import Injector

from internal.server import Http
from internal.router import Router
from config import Config
import dotenv
from .module import ExtensionModule
from pkg.sqlalchemy import SQLAlchemy
from flask_migrate import Migrate


# 将env 加载到环境变量
dotenv.load_dotenv()
# 将扩展模块传递到Injector里
injector = Injector([ExtensionModule])
conf = Config()
app = Http(__name__, router=injector.get(Router),
           conf=conf,
           db = injector.get(SQLAlchemy),
           migrate = injector.get(Migrate),
)

if __name__ == '__main__':

    app.run(host='0.0.0.0', port=8080)
