from flask_wtf import FlaskForm
from wtforms import StringField
from wtforms.validators import DataRequired, Length


class CheckReq(FlaskForm):
    """基础聊天接口请求验证"""
    # 必填、长度最大为2000
    data = StringField("data", validators=[
        DataRequired(message="data数据是必填"),
        Length(max=2000, message="data数据最大长度是2000"),
    ])
