"""
 多继承 父类1
 python的多继承，其实就相当于java中的继承加实现
"""
from abc import ABC, abstractmethod


class MyB(ABC):

    def job(self):
        print('=========MyB==========')

    """
    抽象类必须继承 ABC。

    抽象方法用 @abstractmethod 装饰。

    子类必须实现所有抽象方法，否则无法实例化。
    """
    @abstractmethod
    def must_implement(self):
        """子类必须实现这个方法"""
        pass
