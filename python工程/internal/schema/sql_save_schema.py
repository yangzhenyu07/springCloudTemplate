from flask_wtf import FlaskForm
from wtforms import StringField, HiddenField
from wtforms.validators import DataRequired, Length, UUID
from pkg.sqlalchemy import JSONField

class CreateAppForm(FlaskForm):
    """创建应用 VO"""
    name = StringField("应用名称", validators=[
        DataRequired(message="应用名称不能为空"),
        Length(min=1, max=255, message="应用名称长度限制1~255")
    ])
    icon = StringField("图标地址", validators=[
        Length(max=255, message="图标地址最长255")
    ], default="")
    config = JSONField("应用配置")


class UpdateAppForm(FlaskForm):
    """更新应用 VO"""
    id = StringField("id",validators=[DataRequired()])

    name = StringField("应用名称", validators=[
        DataRequired(message="应用名称不能为空"),
        Length(min=1, max=255, message="应用名称长度限制1~255")
    ])
    icon = StringField("图标地址", validators=[
        Length(max=255, message="图标地址最长255")
    ])
    config = JSONField("应用配置")
