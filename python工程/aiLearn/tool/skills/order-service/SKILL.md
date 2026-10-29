---
name: order-service
description: >
  订单域能力。查询订单状态与物流轨迹、计算快递运费。
  触发场景：用户问「订单到哪了」「物流进度」「我的订单什么状态」「运费多少钱」「什么时候送达」。
  不适用于：商品库存查询、退款政策咨询（那是别的 skill 的事）。
# 下面是 deepagents 的扩展字段（标准 spec 里没有）：声明本 skill 绑定的工具。
# 只有 agent 读完本 SKILL.md 之后，这些工具才会进入上下文；
# 在此之前调用会按 unknown tool 失败 —— 这就是「工具跟着 skill 一起加载」。
#
# ⚠️ 实测坑：这里必须是**空格分隔的字符串**，不能写成 YAML 列表。
#    写成列表会告警：should be a space-separated string of tool names
metadata:
  include_tools: logistics_track calc_shipping_fee
---

# 订单服务

处理订单状态、物流轨迹、运费估算三类问题。

## 一、判断用户要什么

| 用户说法 | 走哪条 | 用什么 |
|---|---|---|
| 「到哪了」「什么时候到」「快递」 | 物流轨迹 | `logistics_track` |
| 「运费多少」「寄过去多少钱」「邮费」 | 运费估算 | `calc_shipping_fee` |
| 「订单状态」「付款了吗」 | 订单状态 | `logistics_track` 先查，状态从结果里读 |

## 二、物流轨迹查询

直接调 `logistics_track(order_no=订单号)`。

- 订单号形如 `SO001`，用户没给就**先问**，不要猜。
- 返回里的「预计送达」是**估算值**，回答时带上「预计」二字，别当承诺。

## 三、运费估算

调 `calc_shipping_fee(weight_kg=重量, distance_km=距离)`。

公式：起步价 8 元 + 重量 × 1.5 元/kg + 距离 × 0.1 元/km。

- 用户只给重量没给距离，就问距离，不要自己编一个默认值。
- 需要精确报价时用脚本：`python scripts/quote.py <重量kg> <距离km>`
  （脚本是**执行**的，不占上下文，比让模型心算稳）

## 四、回答规范

1. 先给结论（到哪了 / 多少钱），再补细节。
2. 数字必须来自工具返回值，**不许自己算、不许编**。
3. 信息不全就问，不要假设。
