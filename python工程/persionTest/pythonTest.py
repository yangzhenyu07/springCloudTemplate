from dataclasses import dataclass
from internal.log import get_logging_by_file
# ======================
# 全局配置 & logging
# ======================
logger = get_logging_by_file(__file__)

COUNT = 10

# ======================
# 基础示例函数
# ======================

def demo_multi_assign():
    """ 函数示例: 多个变量赋值"""
    a, b, c = 1, 2, 3
    logger.info(f"a={a}, b={b}, c={c}")


def demo_single_assign(value):
    """ 函数示例: 单个变量赋值"""
    a = value
    logger.info(f"value={a}")
    return a


def demo_while(val):
    """ 函数示例: while 循环"""
    logger.info("while start")
    flag = True
    while flag:
        if COUNT <= val:
            flag = False
        logger.info(f"val={val}")
        val += 1
    logger.info("while end")


def demo_for(vals):
    """ 函数示例: for 循环"""
    for val in vals:
        logger.info(val)


# ======================
# list / map 示例
# ======================

def demo_while_else(val):
    """ 函数示例: while ... else ..."""
    logger.info("while-else start")
    while COUNT >= val:
        logger.info(f"val={val}")
        val += 1
    else:
        logger.info("while-else end")


# ======================
# list / map 示例
# ======================

def demo_list():
    """ 函数示例: list 示例"""
    data = ['nacos', 'yaml_sentinel', 'yaml_cluster', 'yaml_redis']
    logger.info(data)
    logger.info(data[0])
    logger.info(f"length={len(data)}")
    return data


def demo_map():
    """函数示例: map 示例"""
    data = {
        'nacos': 1,
        'yaml_sentinel': 2,
        'yaml_cluster': 3,
        'yaml_redis': 4
    }
    logger.info(data.get('yaml_redis', 0))
    logger.info(data.get('test', 0))
    return data


# ======================
# switch / if 示例
# ======================

def get_log_level(module, config_map):
    """函数示例: 模拟 switch，根据模块名返回日志级别"""
    if module == 'nacos':
        return 1
    elif module == 'yaml_sentinel':
        return 2
    elif module == 'yaml_cluster':
        return 3
    elif module == 'yaml_redis':
        return 4
    else:
        return config_map.get(module, 0)


# ======================
# 判空 & 包含判断
# ======================

def demo_check():
    """函数示例: 包含判断 & 判空"""
    lst = ['a', 'b']
    mp = {'a': 1}

    if 'a' in lst:
        logger.info("a in list")

    if 'a' in mp:
        logger.info("a in map")

    if not []:
        logger.info("empty list")

    if not {}:
        logger.info("empty map")

    obj = None
    if obj is None:
        logger.info("object is None")


# ======================
# 配置合并 & dataclass
# ======================

def merge_config():
    """函数示例: 默认配置 + 自定义配置 合并"""
    default_config = {
        'timeout': 30,
        'retry': 3,
        'log_level': 'INFO'
    }
    custom_config = {
        'retry': 5,
        'log_level': 'DEBUG'
    }
    return {**default_config, **custom_config}


@dataclass
class Config:
    timeout: int
    retry: int
    log_level: str


# ======================
# 异常处理示例
# ======================

def demo_exception():
    """函数示例: 异常处理示例"""
    try:
        result = 10 / 0
        return result
    except ZeroDivisionError as e:
        logger.error(f"ZeroDivisionError: {e}")
    except Exception as e:
        logger.error(f"Unknown error: {e}")
    finally:
        logger.info("finally executed")


# ======================
# main：只做流程编排
# ======================

def main():
    logger.info("program start")
    logger.info(demo_multi_assign.__doc__)
    demo_multi_assign()
    logger.info("_" * 80)
    logger.info(demo_single_assign.__doc__)
    demo_single_assign(4)

    logger.info("_" * 80)
    logger.info(demo_while.__doc__)
    demo_while(0)
    logger.info("_" * 80)
    logger.info(demo_while_else.__doc__)

    demo_while_else(0)
    logger.info("_" * 80)
    logger.info(demo_for.__doc__)
    vals = ["yang", "zhen", "yu"]
    demo_for(vals)
    logger.info("_" * 80)

    logger.info(demo_list.__doc__)
    lst = demo_list()
    logger.info("_" * 80)
    logger.info(demo_map.__doc__)

    mp = demo_map()
    logger.info("_" * 80)
    logger.info(get_log_level.__doc__)

    level = get_log_level('yaml_redis', mp)
    logger.info(f"log level={level}")
    logger.info("_" * 80)
    logger.info(demo_check.__doc__)

    demo_check()
    logger.info("_" * 80)
    logger.info(merge_config.__doc__)

    final_cfg_dict = merge_config()
    cfg = Config(**final_cfg_dict)
    logger.info(cfg)
    logger.info("_" * 80)
    logger.info(demo_exception.__doc__)

    demo_exception()

    logger.info("program end")


if __name__ == "__main__":
    main()
