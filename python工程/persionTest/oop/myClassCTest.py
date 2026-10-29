from vo.myClassC import MyClassC

"""
 测试类的多继承使用
"""
if __name__ == '__main__':

    # 在 Python 里，如果有多个父类，你直接用 self.method() 调用时，解释器会按照 MRO（方法解析顺序） 来决定调用哪个父类的方法。
    """
    先从当前类本身找方法。

    如果没有，就按照继承的父类顺序找（从左到右）。

    如果父类本身也有多继承，就继续递归查找，但会遵循 C3 线性化算法。
    """
    print("判断调用父类job方法的顺序")
    print(MyClassC.mro())
    myClass = MyClassC()
    myClass.super_job()
    MyClassC.job_A()
    myClass.job_B()
    MyClassC.must_implement()







