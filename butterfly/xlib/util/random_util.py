#!/usr/bin/python
# coding=utf8
"""
# Author: wangbin34(meetbill)
# Created Time : 2020-08-16 09:20:00

# File Name: random_util.py
# Description:
    加权随机算法，使用 bisect 模块来实现二分搜索，选取的时间复杂度是 O(logn)

    # 在 L 中查找 x，x 存在时返回 x 最右侧的位置，x 不存在返回应该插入的位置
    bisect.bisect_right(L,x)
"""

import random
import bisect


def weight_choice(data, weight):
    """
    Args:
        :data   : list 数据列表，例如 ["A", "B", "C"]
        :weight : list 对应的权重序列，例如 [1，5，3]
    Returns:
        数据列表中的随机值
    """
    # 权重累加列表
    weight_sum = []
    sum = 0
    for a in weight:
        sum += a
        weight_sum.append(sum)

    t = random.randint(0, sum - 1)
    return data[bisect.bisect_right(weight_sum, t)]


if __name__ == "__main__":
    data = ['A', 'B', 'C', 'D']
    print weight_choice(data, [5, 2, 2, 1])
