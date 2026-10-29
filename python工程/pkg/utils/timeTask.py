import time
from functools import wraps

from internal.log import get_logging_by_file

logger = get_logging_by_file(__file__)


def sec_to_hms(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60  # 不转int，保留小数
    return f'{h:02d}:{m:02d}:{s:.2f}'  # 秒保留2位小数


def time_task(task_name=None, remark="无备注"):
    """
    带参数的耗时记录装饰器
    Parameters
    ----------
    task_name: str 可选，任务名称（默认用函数名）
    remark: str 可选，任务备注（默认"无备注"）
    Returns
    -------
    装饰器函数
    """

    # 第一层：接收装饰器的自定义参数
    def decorator(fn):
        # 第二层：接收被装饰的函数
        @wraps(fn)  # 保留原函数的元信息
        def wrapper(*args, **kwargs):
            # 第三层：执行函数并记录耗时
            start_time = time.time()
            res = fn(*args, **kwargs)  # 执行原函数
            elapse_time = time.time() - start_time

            # 优先使用传入的task_name，否则用函数名
            final_task_name = task_name if task_name else fn.__name__
            # 拼接日志信息，包含自定义参数
            logger.info(
                f"Task [{final_task_name}] 耗时: {sec_to_hms(elapse_time)} | 备注: {remark}"
            )
            return res

        return wrapper

    return decorator



