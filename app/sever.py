#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
时间：2023/12/5 20:50
作者：南城九叔
"""
import json
import os.path
import sqlite3
import time
from urllib.parse import parse_qs

from PySide6.QtCore import QObject
from mitmproxy.http import HTTPFlow

from .unit import S, BASE_DIR


class TryAddon(QObject):
    page = 1
    tabIds = {'212': '精选', '221': '手机', '222': '电脑数码', '229': '家电', '223': '母婴',
              '224': '食品饮料', '225': '美妆', '226': '清洁', '227': '个护', '228': '更多活动', '234': '时尚'}
    products = {'day': time.strftime("%Y-%m-%d"), 'data': {}}
    path = os.path.join(BASE_DIR, 'WebData', 'UserData')
    if not os.path.exists(path):
        os.makedirs(path)
    con = sqlite3.connect(os.path.join(path, 'users.db'), check_same_thread=False)
    cur = con.cursor()

    # user = '南城九叔'

    # TODO: 测试后删除
    # cur.execute(f"CREATE TABLE IF NOT EXISTS {user} (商品ID integer primary key)")

    def __init__(self):
        super().__init__()

    def response(self, flow: HTTPFlow):
        """
        网络响应情况
        :param flow: HTTPFlow
        :return:
        """

        # 获取京东api请求
        if 'api.m.jd.com/client.action' in flow.request.url:
            content: str = flow.request.get_text()
            result: dict = flow.response.json()
            params: dict = parse_qs(content)

            # 获取试用申请的返回结果
            if 'functionId=try_apply' in content and 'appid=newtry' in content:
                if 'message' in result:
                    msg = result['message']
                    S.apply_result.emit(S.item, msg)
                    if '明天' in msg or '登陆' in msg:
                        S.stop_apply = True
                        return
                    actId = eval(params['body'][0])['activityId']
                    # print(actId)
                    try:
                        self.con.execute(f'INSERT INTO {S.user} (商品ID) VALUES (?)', (actId,))
                        self.con.commit()
                    except Exception as e:
                        print('已申请商品ID存入数据库出错', e)

            if S.get_applies:
                if 'functionId=try_SpecFeedList' in content and 'appid=newtry' in content:
                    try:
                        info = json.loads(params['body'][0])
                        # print(result)
                        kind = info['tabId']
                        page = info['page']
                        S.tip.emit(f'获取 {self.tabIds[kind]}，第{page}页...')
                        next_page = result['data']['hasNext']
                        try:
                            self._get_product_info(self.tabIds[kind], result['data']['feedList'])
                        except Exception as e:
                            print('解析商品信息时发生错误', e)
                        if not next_page:
                            self.page += 1
                            S.next_kind.emit(self.page)
                            if self.page == 12:
                                print(f'获得_{self.tabIds[kind]}，第{page}页...')
                                file = os.path.join(BASE_DIR, 'WebData', 'products.json')
                                with open(file, 'w', encoding='utf-8') as f:
                                    json.dump(self.products, f, ensure_ascii=False)
                                S.products.emit(self.products)
                                S.stop_auto.emit()
                                S.get_applies = False
                                return
                    except Exception as e:
                        print('错误信息', e)

            # 获取已试用的商品信息
            if S.get_applying:
                if 'functionId=try_MyTrials' in content and 'appid=newtry' in content:
                    # print('获取已申请信息结果', result)
                    info = json.loads(params['body'][0])
                    try:
                        if result['message'] and '请先登陆' in result['message']:
                            S.tip.emit('请先登陆后再操作.')
                            S.get_applying = False
                            S.stop_auto.emit()
                            return
                        selected = info['selected']
                        if selected == 1:
                            page = info['page']
                            data = result['data']['list']
                            print('页数', page)
                            if data:
                                self._save_user_applies(data)
                            else:
                                if page > 1:
                                    S.tip.emit('所有已申请的商品信息已获取完毕')
                                else:
                                    S.tip.emit('暂未申请过商品')
                                S.get_applying = False
                                S.stop_auto.emit()
                                return
                    except Exception as e:
                        print(e)

    def _get_product_info(self, kind: str, result: list):
        """
        提取出需要的试用商品信息字段
        :param kind: 分类
        :param result: 每一页的列表数据
        :return:
        """
        if kind not in self.products['data']:
            self.products['data'][kind] = []
        for data in result:
            skuTitle = data['skuTitle']
            jdPrice = float(data['jdPrice'])
            trialPrice = float(data['trialPrice'])
            supplyNum = data['supplyNum'] if data['applyNum'] else 0
            applyNum = data['applyNum'] if data['applyNum'] else 1
            winRate = round(supplyNum / applyNum * 1000, 2) if applyNum else 1000
            skuImg = f'https:{data["skuImg"]}' if data["skuImg"].startswith('//') else data["skuImg"]
            trialActivityId = data['trialActivityId']
            tagList = data['tagList']
            item = [skuTitle, jdPrice, trialPrice, supplyNum, applyNum, winRate, skuImg, trialActivityId, tagList]
            self.products['data'][kind].append(item)

    def _save_user_applies(self, data: list):
        """
        储存用户已试用过的商品ID
        :param data: 列表数据
        :return:
        """
        for item in data:
            actId = item['actId']
            # print(actId)
            S.userData[S.user].append(actId)
            try:
                self.con.execute(f'INSERT INTO {S.user} (商品ID) VALUES (?)', (actId,))
            except Exception as e:
                print('已申请商品ID存入数据库出错', e)

        self.con.commit()
