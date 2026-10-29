from pkg.utils.timeTask import time_task
import time
from internal.log import get_logging_by_file

logger = get_logging_by_file(__file__)

@time_task()
def hhh(str1, **kwargs):
    time.sleep(10)
    logger.info(f'str1:{str1}')
    logger.info(f'打印字典:{kwargs}')
    return f'处理完成: {str1}'


if __name__ == '__main__':
    hhh('哈哈啊', kkk=231, ooo=22)