#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
时间：2023/12/5 20:42
作者：南城九叔
"""
import asyncio
import json
import os.path
import sqlite3
from threading import Thread
import requests
from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtNetwork import QNetworkProxy, QNetworkReply
from PySide6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage, QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import *
from mitmproxy.options import Options
from mitmproxy.tools.dump import DumpMaster

from config import *
from .sever import TryAddon
from .ui_main import Ui_MainWindow
from .unit import *
from .web import *


class MainWin(QMainWindow, Ui_MainWindow):
    item = Signal(list)
    getGD = Signal()
    resizeTable = Signal()
    path = os.path.join(BASE_DIR, 'WebData', 'UserData')
    if not os.path.exists(path):
        os.makedirs(path)
    con = sqlite3.connect(os.path.join(path, 'users.db'), check_same_thread=False)
    cur = con.cursor()
    products = {}

    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.setWindowIcon(BytesIcon(appIcon))
        self.setWindowTitle('狗狗日记')
        self.init_settings()
        proxy = QNetworkProxy()
        proxy.setType(QNetworkProxy.HttpProxy)
        proxy.setHostName("127.0.0.1")
        proxy.setPort(PORT)
        QNetworkProxy.setApplicationProxy(proxy)
        S.tip.connect(self.textBrowser.append)
        S.products.connect(self._add_products)
        S.apply_result.connect(self._apply_result)
        S.next_apply.connect(self._next_apply)

        # self.setMinimumSize(1600, 850)
        self.setFixedSize(1600, 850)
        # self.w.setFixedSize(400, 800)
        self.jd = QStackedWidget()
        self.jd.setFixedSize(400, 800)
        # self.jd.addWidget(self.w)
        self.dock = QDockWidget()
        self.dock.setWindowTitle('模拟器')
        self.dock.setWidget(self.jd)
        self.dock.setAllowedAreas(Qt.LeftDockWidgetArea)
        self.dock.setFeatures(self.dock.features() & ~QDockWidget.DockWidgetClosable)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.dock)
        self.server = Thread(target=self.on_sever, daemon=True)
        self.server.start()
        self.pic_manager = QNetworkAccessManager(self)
        self.pic_manager.finished.connect(self._set_label_pic)
        self.load_user()
        self.comboBox.currentIndexChanged.connect(self.user_changed)
        # 测试
        S.CS.connect(self.cs)

    def cs(self, page):
        w = self.jd.widget(1)
        page.setDevToolsPage(w.page())

    def user_changed(self, index: int):
        """
        切换网页
        :param index: 用户序号
        :return:
        """
        self.jd.setCurrentIndex(index)
        S.user = self.comboBox.currentText()
        S.stop_apply = False

    def load_user(self):
        """
        加载用户
        :return:
        """

        for i, user in enumerate(USERS.keys()):
            web = JDWeb(user)
            if i == 0:
                S.user = user
            web.load(QUrl('https://home.m.jd.com/myJd/newhome.action'))
            self.jd.addWidget(web)
            self.comboBox.addItem(user, userData=web)
            self.cur.execute(f"CREATE TABLE IF NOT EXISTS {user} (商品ID integer primary key)")

    def init_settings(self):
        """
        初始化相关设置
        :return:
        """
        self.pushButton.clicked.connect(self._get_toady_infos)
        self.pushButton_2.clicked.connect(self._check_apply)
        self.pushButton_3.clicked.connect(self._get_cookie)
        self.pushButton_4.clicked.connect(self._apply_products)
        self.pushButton_5.clicked.connect(self._del_user_data)
        self.pushButton_6.clicked.connect(self._re_login)
        self.pushButton_7.clicked.connect(self._creat_user_db)
        self.pushButton_8.clicked.connect(self._creat_applies)
        self.tableWidget.setSelectionBehavior(QTableWidget.SelectRows)
        self.tableWidget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.tableWidget.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tableWidget.itemSelectionChanged.connect(self._show_pic)
        self.tableWidget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tableWidget.customContextMenuRequested.connect(self._creat_menu)
        self.tableWidget.setSortingEnabled(True)
        self.item.connect(self._add_product_to_table)
        self.getGD.connect(self._get_jd)
        self.resizeTable.connect(self._resize_table)

    def on_sever(self):
        mitmproxy_options = Options()
        mitmproxy_options.add_option("ssl_insecure", bool, True, "Ignore SSL certificate verification")
        mitmproxy_options.listen_host = "127.0.0.1"  # 监听主机
        mitmproxy_options.listen_port = PORT  # 监听端口
        loop = asyncio.new_event_loop()
        master = DumpMaster(options=mitmproxy_options, with_termlog=False, with_dumper=False, loop=loop)

        # 添加自定义 addons 规则
        master.addons.add(TryAddon())
        # 使用协程运行mitmproxy
        asyncio.run(master.run())

    @Slot()
    def _get_jd(self):
        """
        打开京东试用界面获取商品信息
        :return:
        """
        web: JDWeb = self.jd.currentWidget()

        QTimer.singleShot(1000, web.get_applies)

    @Slot()
    def _get_toady_infos(self):
        """
        获取今日试用商品列表信息
        :return:
        """

        self.tableWidget.setSortingEnabled(False)
        self.tableWidget.setRowCount(0)

        def get_from_jd():
            """
            从京东获取数据
            :return:
            """
            self.getGD.emit()

        def get_from_gitee():
            """
            从Gitee读取数据，避免频繁从京东访问数据
            :return:
            """
            if GET_FROM_GITEE:
                url = 'https://gitee.com/ctlddey/updata/raw/master/products.json'
                r = requests.get(url, verify=False)
                data = r.json()
                if data['day'] == time.strftime("%Y-%m-%d"):
                    items = data['data']
                    file = os.path.join(BASE_DIR, 'WebData', 'products.json')
                    with open(file, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False)
                    self.products = data
                    self._send_items(items)
                else:
                    get_from_jd()
            else:
                get_from_jd()

        def get_from_local():
            """
            检查本地缓存信息
            :return:
            """

            file = os.path.join(BASE_DIR, 'WebData', 'products.json')
            if os.path.exists(file):
                with open(file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if data['day'] == time.strftime("%Y-%m-%d"):
                        items = data['data']
                        self.products = data
                        self._send_items(items)
                    else:
                        get_from_gitee()
            else:
                get_from_gitee()

        work = Thread(target=get_from_local, daemon=True)
        work.start()

    @Slot()
    def _add_products(self, data: dict):
        """
        所有商品信息
        :param data:
        :return:
        """
        self.products = data
        items = data['data']
        self._send_items(items)

    def _send_items(self, items: dict):
        """
        将商品信息展示在表格中
        :param items: 商品项目字典
        :return:
        """
        for kind, item in items.items():
            for product in item:
                self.item.emit(product)
        self.resizeTable.emit()

    @Slot()
    def _add_product_to_table(self, item: list):
        """
        将商品信息展示到表格中
        :param item: 商品信息列表
        :return:
        """

        def _add(col, value):
            item = QTableWidgetItem()
            item.setData(Qt.DisplayRole, value)
            self.tableWidget.setItem(row, col, item)

        # row = self.tableWidget.rowCount()
        row = 0
        self.tableWidget.insertRow(row)
        [_add(m, value) for m, value in enumerate(item)]
        self.tableWidget.setItem(row, 9, QTableWidgetItem('未申请'))

    @Slot()
    def _show_pic(self):
        """
        发起图像请求
        :return:
        """
        row = self.tableWidget.currentRow()
        item = self.tableWidget.item(row, 6)
        if item:
            url = item.text()
            request = QNetworkRequest(QUrl(url))
            self.pic_manager.get(request)

    @Slot()
    def _set_label_pic(self, reply: QNetworkReply):
        """
        将收到的二进制图像呫在label上
        :param reply: 网络回应
        :return:
        """
        img_data = reply.readAll()
        pixmap = QPixmap()
        pixmap.loadFromData(img_data)
        # 将图像缩放与label一致大小
        pixmap = pixmap.scaled(self.label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        # 在标签中设置图像
        self.label.setPixmap(pixmap)

    @Slot()
    def _creat_user_db(self):
        """
        建立用户数据库存储申请中的信息
        :return:
        """
        web: JDWeb = self.jd.currentWidget()
        S.user = self.comboBox.currentText()
        QTimer.singleShot(1000, web.get_applying)

    @Slot()
    def _resize_table(self):
        QTimer.singleShot(100, self.resize_table)

    def resize_table(self):
        """
        调整表格显示
        :return:
        """

        def table_length():
            """
            计算表格尺寸
            :return:
            """
            table = self.tableWidget
            w1 = table.verticalHeader().width() if table.verticalHeader().isVisible() else 0
            w2 = table.verticalScrollBar().width() if table.verticalScrollBar().isVisible() else 0
            return table.width() - w1 - w2

        jd1_b = [8, 1, 1, 1, 1, 1.3, 0, 0, 0, 2]
        c = [table_length() * (j / sum(jd1_b)) for j in jd1_b]
        [self.tableWidget.setColumnWidth(i, c[i]) for i in range(self.tableWidget.columnCount())]

    def resizeEvent(self, a0: QResizeEvent) -> None:
        QTimer.singleShot(50, self.resize_table)

    @Slot()
    def _creat_menu(self, pos):

        def open_url():
            self.web().load(QUrl(url))

        def apply_this():
            info = self.tableWidget.item(item.row(), 9).text()
            if info != '已申请':
                self.web().apply_product(url)

        def _print():
            def a():
                print("当前行号", S.item.row())

            QTimer.singleShot(5000, a)

        menu = QMenu(self)
        ac1 = QAction('查看详情', self, triggered=open_url)
        ac2 = QAction('申请此项', self, triggered=apply_this)
        ac3 = QAction('打印行号', self, triggered=_print)
        menu.addActions([ac1, ac2, ac3])
        item = self.tableWidget.itemAt(pos)
        if item:
            S.item = item
            productId = self.tableWidget.item(item.row(), 7).text()
            url = f'https://try.jd.com/{productId}.html'
            menu.exec_(self.tableWidget.mapToGlobal(pos))
            # print(url)

    @Slot()
    def _apply_result(self, item, msg):
        row = item.row()
        self.tableWidget.setItem(row, 9, QTableWidgetItem(msg))
        item = self.tableWidget.item(row, 9)
        self.tableWidget.scrollToItem(item, QAbstractItemView.PositionAtTop)
        self.tableWidget.clearSelection()
        Range = QTableWidgetSelectionRange(row, 0, row, self.tableWidget.columnCount() - 1)
        self.tableWidget.setRangeSelected(Range, True)
        # self.tableWidget.verticalScrollBar().setSliderPosition(row)

    def web(self) -> JDWeb:
        return self.jd.currentWidget()

    @Slot()
    def _creat_applies(self):
        def keyword_filter():
            # print(products)
            keywords = USERS[self.comboBox.currentText()]['filterKeywords']

            # 清洗重复的数据
            seen = set()
            cleaned_list = list(filter(lambda x: len(x) > 6 and x[6] not in seen and not seen.add(x[6]), products))

            # 清洗关键词
            cleaned_list = list(filter(lambda x: not any(keyword in x[0] for keyword in keywords), cleaned_list))

            self.cur.execute(f"SELECT 商品ID FROM {self.comboBox.currentText()}")
            product_ids = self.cur.fetchall()
            product_ids = [p[0] for p in product_ids]
            # print(product_ids)
            for p in cleaned_list:
                productId = p[7]
                if productId not in product_ids:
                    # 此操作如果中断需要重新加载数据
                    self._add_product_to_table(p)
            self.tableWidget.setSortingEnabled(True)

            # 设置价格由大到小排序
            self.tableWidget.sortItems(1, Qt.DescendingOrder)

        if not self.products:
            self.textBrowser.append('请先获取今日试用商品信息')
        else:
            if self.products['day'] != time.strftime("%Y-%m-%d"):
                self.textBrowser.append('商品信息已失效，请重新获取')
            else:
                products = []
                self.tableWidget.setRowCount(0)
                self.tableWidget.setSortingEnabled(False)
                data: dict = self.products['data']
                for _, items in data.items():
                    for item in items:
                        products.append(item)
                keyword_filter()
                # print(len(products))

    @Slot()
    def _apply_products(self):
        if self.pushButton_4.text() == '批量申请':
            self.pushButton_4.setText('终止申请')
            S.stop_apply = False
            self.apply_products()

        else:
            self.pushButton_4.setText('批量申请')
            S.stop_apply = True

    def apply_products(self):
        for row in range(self.tableWidget.rowCount()):
            item = self.tableWidget.item(row, 9)
            if item and item.text() == '未申请':
                S.item = item
                productId = self.tableWidget.item(row, 7).text()
                url = f'https://try.jd.com/{productId}.html'
                self.web().apply_product(url)
                return
        S.stop_apply = True

    @Slot()
    def _next_apply(self):

        def apply():
            if not S.stop_apply:
                self.apply_products()

        if not S.stop_apply:
            QTimer.singleShot(5000, apply)

    @Slot()
    def _check_apply(self):
        self.web().load(QUrl('https://try.m.jd.com'))

    @Slot()
    def _get_cookie(self):
        self.web().get_cookie()

    @Slot()
    def _re_login(self):
        self.web().re_login()

    @Slot()
    def _del_user_data(self):
        self.con.execute(f"DELETE FROM {self.comboBox.currentText()}")
        self.con.commit()
        self.textBrowser.append('当前用户已申请商品ID数据库缓存已清空，请从新初始化获取...')