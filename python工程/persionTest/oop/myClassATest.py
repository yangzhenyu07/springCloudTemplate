from vo.myClassA import MyClassA

"""
 测试类定义的使用
"""
if __name__ == '__main__':
    #  初始化实例
    myClass = MyClassA('yzy', 30)
    # 调用 test，不传 self，Python 自动把 myClass 当作 self、即 self 是方法内部用来引用当前对象的“把柄”，调用时不传
    myClass.test()
    print('========================================================================')
    # myClass.age = 35 会自动调用你类里定义的 age setter 方法
    myClass.age = 35
    myClass.test()

