from vo.myClassB import MyClassB

"""
 测试类定义的使用
"""
if __name__ == '__main__':
    #  初始化实例、初始化该类的实例变量
    myClass = MyClassB('yzy', 30)
    print('=========通过对象调用实例方法、测试初始化是否成功============')
    myClass.test()
    # 修改实例变量
    print('=========修改实例变量、将30改成55============')
    myClass.age = 55
    print('=========通过对象调用实例方法、测试实例变量是否修改成功============')
    myClass.test()
    print('=========调用类变量============')
    print(f'类变量:{MyClassB.species}')
    print('=========调用静态方法============')
    print(f'调用静态方法:{MyClassB.is_adult(myClass.age)}')
    print('=========调用类方法============')
    MyClassB.show_species()



