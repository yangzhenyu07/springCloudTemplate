# pkg/utils/json_util.py
import json
from datetime import datetime, date


class JsonUtil:
    """JSON工具类"""

    @staticmethod
    def json_default(obj):
        """json.dumps 默认转换处理器"""
        if isinstance(obj, datetime):
            return obj.strftime("%Y-%m-%d %H:%M:%S")
        if isinstance(obj, date):
            return obj.strftime("%Y-%m-%d")
        raise TypeError(f"无法序列化类型: {type(obj)}")

    @staticmethod
    def to_json_str(data, ensure_ascii: bool = False, indent: int | None = None) -> str:
        """
        对象转json字符串，适配datetime/date，用于日志打印
        :param data: 字典 / 带to_dict()方法的model实例 / 普通对象
        :param ensure_ascii: 是否中文转unicode，日志默认False保留中文
        :param indent: 格式化缩进，日志一般不传，压缩一行
        :return: json字符串
        """
        if hasattr(data, "to_dict") and callable(data.to_dict):
            data = data.to_dict()
        return json.dumps(data, ensure_ascii=ensure_ascii, default=JsonUtil.json_default, indent=indent)

    @staticmethod
    def to_json_str_truncate(data, max_len: int = 2000, ensure_ascii: bool = False) -> str:
        """带截断，防止超大config把日志打爆炸"""
        s = JsonUtil.to_json_str(data, ensure_ascii=ensure_ascii)
        if len(s) > max_len:
            s = s[:max_len] + "...[truncated]"
        return s
