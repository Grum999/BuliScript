#-----------------------------------------------------------------------------
# Buli Script
# Copyright (C) 2020 - Grum999
# -----------------------------------------------------------------------------
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.
# If not, see https://www.gnu.org/licenses/
# -----------------------------------------------------------------------------
# A Krita plugin designed to draw programmatically
# -----------------------------------------------------------------------------

from PyQt5.Qt import *
from PyQt5.QtWidgets import QDockWidget
from PyQt5.QtCore import (
        pyqtSignal as Signal
    )


from buliscript.pktk.widgets.wcolorselector import WColorPicker
from buliscript.pktk.widgets.wdockwidget import WDockWidget


class BSDockWidgetColorPicker(WDockWidget):
    """A dock widget to display color selector, to insert/update a color code in script"""
    apply=Signal(QColor, int)       # upsert button cliked, apply color according to mode

    MODE_INSERT = 0x01
    MODE_UPDATE = 0x02

    def __init__(self, parent, name='Color Picker'):
        super(BSDockWidgetColorPicker, self).__init__(name, parent)

        self.__mode=BSDockWidgetColorPicker.MODE_INSERT

        self.__widget=QWidget(self)
        self.__widget.setMinimumWidth(200)

        self.__layout=QVBoxLayout(self.__widget)
        self.__widget.setLayout(self.__layout)

        self.__cColorPicker=WColorPicker(self)
        self.__cColorPicker.setOptionMenu(WColorPicker.OPTION_MENU_RGB|
                                          WColorPicker.OPTION_MENU_CMYK|
                                          WColorPicker.OPTION_MENU_HSV|
                                          WColorPicker.OPTION_MENU_HSL|
                                          WColorPicker.OPTION_MENU_ALPHA|
                                          WColorPicker.OPTION_MENU_CSSRGB|
                                          WColorPicker.OPTION_MENU_COLCOMP|
                                          WColorPicker.OPTION_MENU_COLWHEEL|
                                          WColorPicker.OPTION_MENU_PALETTE|
                                          WColorPicker.OPTION_MENU_UICOMPACT|
                                          WColorPicker.OPTION_MENU_COLPREVIEW)
        self.__cColorPicker.setOptionLayout(['colorRGB', 'colorHSV', 'colorAlpha', 'colorCssRGB', 'colorWheel', 'colorPreview'])

        self.__btnUpsert=QPushButton("xx")
        self.__btnUpsert.clicked.connect(self.__clicked)
        self.setMode(self.__mode)


        self.__layout.addWidget(self.__cColorPicker)
        self.__layout.addWidget(self.__btnUpsert)

        self.updateStatus()
        self.setWidget(self.__widget)

    def __clicked(self):
        """Button has been clicked"""
        self.apply.emit(self.color(), self.__mode)


    def options(self):
        """Return current option value"""
        return self.__cColorPicker.optionLayout()

    def setOptions(self, value):
        """Set option value"""
        if "layoutOrientation:2" in value:
            value.remove('layoutOrientation:2')
        self.__cColorPicker.setOptionLayout(value)

    def colorPicker(self):
        """Return color picker instance"""
        return self.__cColorPicker

    def color(self):
        """Return current color from color picker"""
        return self.__cColorPicker.color()

    def setColor(self, color):
        """Set current color"""
        if isinstance(color, str):
            if r:=re.search(r"^#([A-F0-9]{2})?([A-F0-9]{6})$", color, re.IGNORE):
                color=QColor(color)

        if not isinstance(color, QColor):
            raise EInvalidType("Given `color` must be a <QColor> or a valid <str> color value")

        self.__cColorPicker.setColor(color)

    def mode(self):
        """Return current mode: INSERT or UPDATE"""
        return self.__mode

    def setMode(self, mode):
        """Set button mode INSERT or REPLACE"""
        if mode==BSDockWidgetColorPicker.MODE_INSERT:
            self.__btnUpsert.setText(i18n('Insert color'))
            self.__btnUpsert.setToolTip(i18n('Insert current color in script'))
            self.__mode=mode
        elif mode==BSDockWidgetColorPicker.MODE_UPDATE:
            self.__btnUpsert.setText(i18n('Update color'))
            self.__btnUpsert.setToolTip(i18n('Update current color in script'))
            self.__mode=mode
