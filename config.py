#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
时间：2023/12/9 09:11
作者：南城九叔
"""

filterKeywords = ['外壳', '手机壳', '手机膜', '钢化膜', '电信', '移动', '联通', '博朗', '窗户', '西瓜', '课程', '网课',
                  '培训', '教程', '无实物', '测评', '服务', '跟团', '旅游', '北海', '看房', '辅导', '在线', '体验课',
                  '训练营', '门票', '公园', '活动', '拿证']

# 端口好
PORT = 3969

USERS = {
    '南城九叔': {
        # 是否是Plus会员：True/False
        'isVip': True,

        # 是否是种草管：True/False
        'isTrier': True,

        # 过滤掉包含关键词的商品：filterKeywords中的全部以及自定义的['面包', '牛奶’]
        'filterKeywords': filterKeywords + [],
    },
    '陈二狗': {
        'isVip': True,
        'isTrier': True,
        'filterKeywords': filterKeywords + [],
    },
    '李唯恩': {
        'isVip': True,
        'isTrier': True,
        'filterKeywords': filterKeywords + [],
    }
}
GET_FROM_GITEE = True
