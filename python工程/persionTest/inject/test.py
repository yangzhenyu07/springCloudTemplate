from dataclasses import dataclass

from injector import inject, Injector
"""
依赖注入使用测试
"""
class A:
    name: str = "yangzhenyu"

"""B 自动将A 注入进来"""
@inject
@dataclass
class B:
    a : A
    def print_a(self):
        print(f"[@dataclass] Class A 的name为{self.a.name}")


if __name__ == '__main__':
    """依赖注入使用"""
    injector = Injector()
    b = injector.get(B)
    b.print_a()
