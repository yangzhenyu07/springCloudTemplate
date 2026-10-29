def test(**kwargs):
    print(kwargs)  # 打印字典


if __name__ == '__main__':
    test(a=1, b=2)         # 输出: {'a': 1, 'b': 2}
    test(name="Kimi")      # 输出: {'name': 'Kimi'}
    test()                 # 输出: {}
