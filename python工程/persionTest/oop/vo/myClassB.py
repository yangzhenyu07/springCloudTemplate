"""
 类变量、实例变量、静态方法、类方法
"""


class MyClassB:
    # 类变量（类似于 Java 的 static 变量）
    species = "Homo sapiens"

    # 类方法（用 @classmethod 装饰，类似 Java 中的 static + class 操作）
    @classmethod
    def show_species(cls):  # 第一个参数 必须是类本身 cls（类似 Java 的 Class<?> clazz）、不能直接访问实例变量（因为它不依赖实例）
        print(f"Species: {cls.species}")

    # 静态方法（不依赖实例或类变量，类似 Java 的 static 方法）
    @staticmethod
    def is_adult(age):
        return age >= 18

    # 实例方法（对象调用）
    def test(self):  # 类似java 中的私有方法
        print(f"Hello, {self._name},age : {self._age}")

    def __init__(self, name, age):  # 类似于java 中的构建函数
        # 实例变量（对象独有）
        self._name = name  # 私有变量约定，前面加下划线
        self._age = age

        # getter

    @property  # 类似于 java 中的get方法
    def name(self):
        return self._name

    # setter
    @name.setter  # 类似与 java 中的 set 方法
    def name(self, value):
        self._name = value

    @property
    def age(self):
        return self._age

    @age.setter
    def age(self, value):
        self._age = value
