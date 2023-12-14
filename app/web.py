#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
时间：2023/12/6 18:54
作者：南城九叔
"""
import random
import sqlite3
import time
from threading import Thread

from PySide6.QtCore import *
from PySide6.QtNetwork import QNetworkCookie
from PySide6.QtWebEngineCore import *
from PySide6.QtWebEngineWidgets import *

from .unit import BASE_DIR, os, S


class JDWeb(QWebEngineView):
    drop_down = Signal()
    auto = False
    cookie = {'pt_pin': '', 'pt_key': ''}

    def __init__(self, user: str = 'default'):
        super().__init__()
        self.user = user
        self._profile = QWebEngineProfile(user)
        s = self._profile.settings()
        s.setAttribute(QWebEngineSettings.PluginsEnabled, True)
        s.setAttribute(QWebEngineSettings.DnsPrefetchEnabled, True)
        s.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
        s.setAttribute(QWebEngineSettings.LocalContentCanAccessFileUrls, True)
        self._profile.setCachePath(os.path.join(BASE_DIR, 'WebData'))
        self.cookiePath = os.path.join(BASE_DIR, f'WebData/{user}')
        self._profile.setPersistentStoragePath(self.cookiePath)
        # self._profile.setHttpCacheType(QWebEngineProfile.DiskHttpCache)
        self._profile.setPersistentCookiesPolicy(QWebEngineProfile.ForcePersistentCookies)
        ua = 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.71 Safari/537.36'
        self._profile.setHttpUserAgent(ua)
        page = QWebEnginePage(self._profile)
        self.setPage(page)

        # 非常奇怪，如果不输出下面的信息就无法正常缓存会话与cookie(PySide6的bug比教多)
        self.page().profile().isOffTheRecord()

        # 业务流程相关
        self.drop_down.connect(self._drop_down)
        S.stop_auto.connect(self._stop_auto)
        S.next_kind.connect(self._next_kind)

    @Slot()
    def _next_kind(self, kind: int):
        """
        切换到下一分类试用
        :param kind: 2-11(共11种)
        :return:
        """
        self.page().runJavaScript("""
                                        var element = document.evaluate(
                                            '/html/body/div[1]/div[3]/div/div/div[3]/div/div/div[2]/div/div[1]/div[2]/div/div/div[%s]/div/span',
                                            document,
                                            null,
                                            XPathResult.FIRST_ORDERED_NODE_TYPE,
                                            null
                                        ).singleNodeValue;
                                        if (element) {
                                            element.click();  // 或者使用 element.dispatchEvent(new Event('touchstart'));
                                        }
                                    """ % kind)

    def get_applies(self):
        """
        获取所有免费试用商品信息
        :return:
        """
        self.loadFinished.connect(self._get_free_applies)
        S.get_applies = True
        self.auto = True
        self.load(QUrl('https://try.m.jd.com'))

    def get_applying(self):
        """
        获取正在申请的商品信息
        :return:
        """
        self.loadFinished.connect(self._get_applyings)
        S.get_applying = True
        self.auto = True
        self.load(QUrl('https://try.m.jd.com'))

    def auto_drop_down(self):
        """
        随机2~5秒 下拉到页面底部
        :return:
        """
        while self.auto:
            time.sleep(random.randint(2, 3))
            self.drop_down.emit()

    @Slot()
    def _drop_down(self):
        """
        操作JS将下拉进度条滑动到底部
        :return:
        """
        self.page().runJavaScript("window.scrollTo(0, document.body.scrollHeight);")
        # print(self.page().runJavaScript("document.body.scrollHeight"))

    @Slot()
    def _stop_auto(self):
        """
        将循环标志设置为否，停止循环下拉
        :return:
        """
        self.auto = False

    @Slot()
    def _get_free_applies(self):
        """
        操作JS从主页跳转到免费试用界面
        :return:
        """

        def load_finish():
            """
            一定要将自动下拉放到加载试用结束后，否则可能会出现未加载出时就下拉，导致无法正常进入免费试用页面，一直在当前页面下拉
            :return:
            """
            print('加载试用页结束')
            self.loadFinished.disconnect(load_finish)
            server = Thread(target=self.auto_drop_down, daemon=True)
            server.start()

        print('点击试用')
        self.loadFinished.disconnect(self._get_free_applies)
        js = """
        var selectors = [
                '.lottery-two-container',
                '.lotter-two-container',
                '.lottery-try-item',
                '.lotter-try-item'
            ];

            var itemClicked = false;
            for (var i = 0; i < selectors.length && !itemClicked; i++) {
                var items = document.querySelectorAll(selectors[i]);
                if(items.length > 0) {
                    items[0].click(); // 点击找到的第一个元素
                    itemClicked = true; // 标记已进行点击，避免点击多个元素
                }
            }
        """
        self.page().runJavaScript(js)
        self.loadFinished.connect(load_finish)

    @Slot()
    def _get_applyings(self):
        """
        跳转到各人试用信息
        :return:
        """
        def load_finish():
            """
            一定要将自动下拉放到加载试用结束后，否则可能会出现未加载出时就下拉，导致无法正常进入免费试用页面，一直在当前页面下拉
            :return:
            """
            print('加载申请页结束')
            self.loadFinished.disconnect(load_finish)
            server = Thread(target=self.auto_drop_down, daemon=True)
            server.start()

        self.loadFinished.disconnect(self._get_applyings)
        js = """
        var element = document.evaluate(
            '/html/body/div[1]/div[3]/div/div/div[4]/div/div/img',
            document,
            null,
            XPathResult.FIRST_ORDERED_NODE_TYPE,
            null
        ).singleNodeValue;
        if (element) {
            element.click();  // 或者使用 element.dispatchEvent(new Event('touchstart'));
        }
        """
        self.page().runJavaScript(js)
        self.loadFinished.connect(load_finish)

    def contextMenuEvent(self, event):
        menu = self.createStandardContextMenu()
        actions = menu.actions()
        inspect_action = self.page().action(QWebEnginePage.InspectElement)
        if inspect_action in actions:
            inspect_action.setText("Inspect element")
        else:
            vs = self.page().action(QWebEnginePage.ViewSource)
            if vs not in actions:
                menu.addSeparator()

            action = menu.addAction("Open inspector in new window")
            action.triggered.connect(self._emit_devtools_requested)

        menu.popup(event.globalPos())

    def _emit_devtools_requested(self):
        S.CS.emit(self.page())

    def apply_product(self, url: str):
        """
        试用申请
        :param url:
        :return:
        """

        def run_js(ok):
            self.loadFinished.disconnect(run_js)
            if ok:
                if ok:  # 检查页面是否成功加载
                    # 注入 JavaScript 来查询特定 div 并根据其内容点击
                    js_code = """
                            var divs = document.querySelectorAll('.apply-try_btn');
                            var result = 0;
                            divs.forEach(function(div) {
                                if(div.textContent.trim() === '立即申请') {
                                    div.click();
                                    result = 1;
                                } else if (div.textContent.trim() === '已申请，进店逛逛') {
                                    result = 0;
                                };
                            });                            
                            result;  // 将结果返回给 PySide
                            """

                    # 执行 JavaScript 并从页面接收返回值
                    self.page().runJavaScript(js_code, 0, js_callback)

        def js_callback(result):
            print('1次点击结果', result)
            js_code = """
            var divs = document.querySelectorAll('.apply-try_btn');
            var result = 0;
            divs.forEach(function(div) {
                if(div.textContent.trim() === '申请试用') {
                    div.click();
                    result = 2;
                } else  {
                    result = 0;
                };
            });                            
            result;  // 将结果返回给 PySide
                                        """
            if result == 1:
                # 执行 JavaScript 并从页面接收返回值
                self.page().runJavaScript(js_code, 1, js_callback2)
            else:
                if not S.stop_apply:
                    S.next_apply.emit()

        def js_callback2(result):
            js_code = """
            var divs = document.querySelectorAll('.open-brand-vip_btn tip-margin');
            var result = 0;
            if (element) {
                element.click();
                result = 3;
                } else {
                result = 0;
                };
            result;  // 将结果返回给 PySide
                                        """
            self.page().runJavaScript(js_code)
            if not S.stop_apply:
                S.next_apply.emit()

        self.loadFinished.connect(run_js)
        self.load(QUrl(url))

    def get_cookie(self):
        conn = sqlite3.connect(os.path.join(self.cookiePath, 'Cookies'), check_same_thread=False, timeout=1)
        cur = conn.cursor()
        cur.execute('select name,value from cookies;')
        cookies = cur.fetchall()
        cookie = ''
        for key, value in cookies:
            if key in ['pt_key', 'pt_in']:
                self.cookie[key] = value
                cookie += f'{key}={value}; '
        S.tip.emit(f'提取到cookie: {cookie}')

    def re_login(self):
        self.page().profile().cookieStore().deleteAllCookies()

