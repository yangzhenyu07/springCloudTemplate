import os


from internal.schema.app_schema import CheckReq

from pkg.response import success_json, validate_error_json, success_message
from internal.exception import ValidateErrorException
from internal.log import get_logging_by_file

logger = get_logging_by_file(__file__)

class AppHandler:
    """ 应用控制层 """

    def ping(self):
        """ POST """
        # data = request.json.get('data') 不带校验
        # 校验
        req = CheckReq()
        if not req.validate():
            # val =  validate_error_json(req.errors)
            logger.info("校验未通过")
            raise ValidateErrorException("校验未通过,",req.errors)

        logger.info(req.data)
        return success_json({"ping":"pong", "data":req.data.data})

    def pingGet(self):
        """ GET """
        flaskDebug = os.getenv('FLASK_DEBUG')
        return success_message(f"ping:pong,flaskDebug:{flaskDebug}")
