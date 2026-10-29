#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""运费报价脚本。

【为什么要有这个脚本】
    Agent Skills 规范里，scripts/ 下的代码是**被执行**的，不是被读进上下文的：
    模型跑 `python scripts/quote.py 1.2 800`，只把 stdout 拿回来，
    脚本源码本身**一个 token 都不占**。

    好处有两个：
      ① 省钱：同样一份逻辑，读进来要几百 token，执行只要几十 token 的输出
      ② 稳：计算逻辑是确定性的，不会像模型心算那样每次结果不一样

    【Java 对照】
        相当于把易错的算式固化成一个工具类方法，
        让模型调用 `FeeCalculator.quote(1.2, 800)`，而不是每次自己算一遍。

用法：
    python scripts/quote.py <重量kg> <距离km>
"""
import sys

BASE = 8.0        # 起步价
PER_KG = 1.5      # 每公斤
PER_KM = 0.1      # 每公里


def quote(weight_kg: float, distance_km: float) -> dict:
    """算运费，返回明细（不只是个数字，方便模型复述）。"""
    weight_fee = weight_kg * PER_KG
    distance_fee = distance_km * PER_KM
    total = BASE + weight_fee + distance_fee
    return {
        "起步价": round(BASE, 2),
        "重量费": round(weight_fee, 2),
        "距离费": round(distance_fee, 2),
        "合计": round(total, 2),
    }


def main() -> None:
    if len(sys.argv) != 3:
        print("用法: python scripts/quote.py <重量kg> <距离km>")
        sys.exit(1)
    try:
        w = float(sys.argv[1])
        d = float(sys.argv[2])
    except ValueError:
        print("错误: 重量和距离必须是数字")
        sys.exit(1)

    r = quote(w, d)
    print(f"运费明细：起步价 {r['起步价']} 元 + 重量费 {r['重量费']} 元 "
          f"+ 距离费 {r['距离费']} 元 = 合计 {r['合计']} 元")


if __name__ == "__main__":
    main()
