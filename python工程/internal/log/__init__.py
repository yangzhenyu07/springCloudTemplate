import logging
import logging.handlers
import os


def get_logging(class_name: str):
    # 获取class_name的logger
    _logger = logging.getLogger(class_name)
    # 设置logger的级别
    _logger.setLevel(level=logging.INFO)
    # 如果logger没有handler，则添加
    if not _logger.handlers:
        # 设置日志格式
        formatter = logging. \
            Formatter('[%(asctime)s] %(filename)s [%(funcName)s] [line:%(lineno)d] - %(levelname)s: %(message)s')
        # 设置控制台输出的handler
        console = logging.StreamHandler()
        # 设置控制台输出的级别
        console.setLevel(logging.INFO)
        # 设置控制台输出的日志格式
        console.setFormatter(formatter)

        _logger.addHandler(console)
        _logger.propagate = False
    return _logger


# logger = get_logging_by_file(__file__)
# 定义一个函数，用于根据文件名获取日志配置
def get_logging_by_file(filename: str):
    # 获取文件名
    file_name = os.path.basename(filename)
    # 调用get_logging函数，传入文件名
    return get_logging(file_name)



if __name__ == '__main__':
    logger = get_logging_by_file(__file__)
    logger.info("12312312")