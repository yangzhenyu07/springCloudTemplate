from dataclasses import dataclass

from injector import inject
from flask import request
from internal.exception import ValidateErrorException
from internal.schema import CreateAppForm,UpdateAppForm
from internal.service import SeqService
from internal.log import get_logging_by_file
from pkg.response import success_json
from pkg.utils.json_util import JsonUtil

logger = get_logging_by_file(__file__)

@inject
@dataclass
class SqlHandler:
    """ sql 测试类 应用控制层 """

    seqService : SeqService

    def add(self):
        """ POST """
        # data = request.json.get('data') 不带校验
        # 校验
        req = CreateAppForm(data=request.get_json())
        if not req.validate():
            # val =  validate_error_json(req.errors)
            raise ValidateErrorException("校验未通过,",req.errors)
        app = self.seqService.create_app(req)
        logger.info(f"新增成功,数据:{JsonUtil.to_json_str_truncate(app)}")
        return success_json("新增成功")


    def update(self):
        """ POST """
        # data = request.json.get('data') 不带校验
        # 校验
        req = UpdateAppForm(data=request.get_json())
        if not req.validate():
            # val =  validate_error_json(req.errors)
            raise ValidateErrorException("校验未通过,",req.errors)
        self.seqService.update_app(req)
        logger.info(f'更新成功,id:{req.id.data}')
        app = self.seqService.get_app(req.id.data)
        return success_json(app.to_dict())

    def get(self, id:str):
        """ GET """
        # 校验

        if not id or not id.strip():
            # val =  validate_error_json(req.errors)
            raise ValidateErrorException("校验未通过,","id 不能为空")
        app = self.seqService.get_app(id)
        logger.info(f'查询结果:{JsonUtil.to_json_str_truncate(app)}')
        return success_json(app.to_dict())

    def delete(self, id:str):
        """ GET """
        # 校验

        if not id or not id.strip():
            # val =  validate_error_json(req.errors)
            raise ValidateErrorException("校验未通过,","id 不能为空")
        self.seqService.delete_app(id)
        logger.info(f'删除成功,id:{id}')
        return success_json("删除成功")

