
import pytest

from app.http.app import app


@pytest.fixture
def client():
    """
    pytest fixture：Flask 测试客户端
    作用：创建一个模拟客户端，用来向Flask接口发请求，代替真实的浏览器/postman
    """
    # 开启Flask测试模式，很多异常会直接抛出，方便测试捕获
    app.config["TESTING"] = True
    # 创建Flask内置的test_client，模拟http请求
    with app.test_client() as client:
        # yield 是fixture的核心：
        # yield之前：【前置准备】，在测试函数执行前运行
        yield client
        # yield之后：【后置清理】，测试函数跑完之后才执行
