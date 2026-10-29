"""
 类定义
"""


class MyClassA:

    def __init__(self, name, age):  # 类似于java 中的构建函数
        self._name = name  # 私有变量约定，前面加下划线
        self._age = age

        # getter

    @property  # 类似于 java 中的get方法
    def name(self):
        return self._name

    # setter
    @name.setter # 类似与 java 中的 set 方法
    def name(self, value):
        self._name = value

    @property
    def age(self):
        return self._age

    @age.setter
    def age(self, value):
        self._age = value

    def test(self):  # 类似java 中的私有方法
        print(f"Hello, {self._name},age : {self._age}")
