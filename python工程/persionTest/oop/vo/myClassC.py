"""
 多继承
 python的多继承，其实就相当于java中的继承加实现
"""
from .myA import MyA
from .myB import MyB


class MyClassC(MyA, MyB):

    def super_job(self):
        print("调用父类的job_A方法")
        super().job_A()

    @staticmethod
    def job_A():
        print("重写父类 MyA 的 job_A方法")

    def job_B(self): # 强制调用某个父类的方法
        print("强制调用某个父类的job方法")
        MyB.job(self)   # 用当前对象 self 来调用 MyB 的 job

    @staticmethod
    def must_implement():
        print("子类实现父类的must_implement方法")

