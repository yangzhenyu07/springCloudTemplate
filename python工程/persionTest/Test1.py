
def test(*args):
    print(args)  # 打印元组


if __name__ == '__main__':
    test(1, 2, 3)  # 输出: (1, 2, 3)
    test("a", "b")  # 输出: ('a', 'b')
    test()
