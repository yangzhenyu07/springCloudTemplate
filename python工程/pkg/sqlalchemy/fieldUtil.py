from flask_wtf import FlaskForm
from wtforms import StringField, Field
from wtforms.validators import DataRequired, Length, ValidationError


class JSONField(Field):
    """自定义WTForms JSON字典字段，适配PostgreSQL JSONB"""
    def process_formdata(self, valuelist):
        if not valuelist:
            self.data = {}
            return
        raw = valuelist[0]
        if not isinstance(raw, dict):
            raise ValidationError(message="该字段必须是JSON对象")
        self.data = raw
