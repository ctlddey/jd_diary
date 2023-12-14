#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
时间：2023/12/5 20:48
作者：南城九叔
"""

from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWidgets import *
from app.main import MainWin


if __name__ == '__main__':
    app = QApplication([])
    win = MainWin()
    win.show()
    app.exec()