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
# A Krita plugin designed to manage documents
# -----------------------------------------------------------------------------

from PyQt5.Qt import *
from PyQt5.QtWidgets import (
        QAction,
        QMenu,
        QSystemTrayIcon
    )
from PyQt5.QtGui import (
        QIcon,
        QPixmap
    )
from PyQt5.QtCore import (
        pyqtSignal as Signal,
        QEventLoop,
        QTimer
    )
from buliscript.pktk.modules.utils import Debug
from buliscript.pktk.modules.imgutils import buildIcon

class BSSysTray(object):
    """Manage system tray"""

    SYSTRAY_MODE_NEVER = 0
    SYSTRAY_MODE_FORNOTIFICATION = 1
    SYSTRAY_MODE_WHENACTIVE = 2
    SYSTRAY_MODE_ALWAYS = 3

    # whhhooo that's ugly ^_^'
    __selfInstance = None


    def __init__(self, uiController):
        """Initialise SysTray manager"""
        def actionAbout(action):
            self.__uiController.commandAboutBs()

        def actionDisplayBs(action):
            self.__displayBuliScript()

        def actionQuitBs(action):
            self.__uiController.commandQuit()


        # Note: theme must be loaded before BSSysTray is instancied (otherwise no icon will be set)
        self.__buliIcon = buildIcon([(QPixmap(':/buli/buli-rounded-border'), QIcon.Normal)])
        self.__tray = QSystemTrayIcon(self.__buliIcon, Krita.instance())
        self.__visibleMode = 1 # when active
        self.__uiController = uiController

        self.__uiController.bsWindowShown.connect(self.__displaySysTrayIcon)
        self.__uiController.bsWindowClosed.connect(self.__hideSysTrayIcon)
        self.__tray.activated.connect(self.__activated)

        BSSysTray.__selfInstance = self

        self.__actionAbout=QAction(i18n('About Buli Script...'))
        self.__actionAbout.triggered.connect(actionAbout)
        self.__actionOpenBs=QAction(i18n('Open Buli Script...'))
        self.__actionOpenBs.triggered.connect(actionDisplayBs)
        self.__actionCloseBs=QAction(i18n('Quit Buli Script'))
        self.__actionCloseBs.triggered.connect(actionQuitBs)

        self.__menu = QMenu()
        self.__menu.addAction(self.__actionAbout)
        self.__menu.addSeparator()
        self.__menu.addAction(self.__actionOpenBs)
        self.__menu.addSeparator()
        self.__menu.addAction(self.__actionCloseBs)

        self.__tray.setContextMenu(self.__menu)


    def __displayContextMenu(self):
        """Display context menu on systray icon"""
        # menu

        # About BS
        # --------
        # Open BS  | Show BS            ==> Open is not yet opened, otherwise show
        # Quit BS

        #print("__displayContextMenu()")
        pass


    def __displayBuliScript(self):
        """Display buli script"""
        if self.__uiController.started():
            self.__uiController.commandViewBringToFront()
        else:
            self.__uiController.start()


    def __activated(self, activationReason):
        """System tray icon has been activated"""
        if activationReason == QSystemTrayIcon.Context:
            # in fact, does nothing if context menu is set...?
            self.__displayContextMenu()
        elif QSystemTrayIcon.DoubleClick:
            self.__displayBuliScript()
        else:
            Debug.print('[BSSysTray] Unknown')


    def __displaySysTrayIcon(self):
        """Display systray if allowed by mode"""
        self.__actionOpenBs.setVisible(not self.__uiController.started())
        self.__actionCloseBs.setVisible(self.__uiController.started())

        if self.__visibleMode==BSSysTray.SYSTRAY_MODE_ALWAYS:
            self.__tray.show()
        elif self.__visibleMode==BSSysTray.SYSTRAY_MODE_WHENACTIVE:
            if not self.__uiController is None:
                if self.__uiController.started():
                    self.__tray.show()
                elif self.__uiController.started():
                    self.__tray.hide()
        else:
            # SYSTRAY_MODE_NEVER
            # SYSTRAY_MODE_FORNOTIFICATION
            self.__tray.hide()


    def __hideSysTrayIcon(self):
        """Hide systray if allowed by mode"""
        self.__actionOpenBs.setVisible(not self.__uiController.started())
        self.__actionCloseBs.setVisible(self.__uiController.started())

        if self.__visibleMode!=BSSysTray.SYSTRAY_MODE_ALWAYS:
            self.__tray.hide()


    def visible(self):
        """Return if icon is currently visible in system tray"""
        return self.__tray.isVisible()


    def visibleMode(self):
        """Return current Systray visible mode"""
        return self.__tray.isVisible()


    def setVisibleMode(self, mode):
        """Set current Systray visible mode"""
        if not mode in [BSSysTray.SYSTRAY_MODE_NEVER,
                        BSSysTray.SYSTRAY_MODE_FORNOTIFICATION,
                        BSSysTray.SYSTRAY_MODE_WHENACTIVE,
                        BSSysTray.SYSTRAY_MODE_ALWAYS]:
            raise EInvalidValue("Given `mode` is not valid")

        self.__visibleMode=mode
        self.__displaySysTrayIcon()


    def __popMessage(self, title, message, icon):
        """Display an information message"""
        def hide():
            # hide icon in tray
            loop.quit()
            self.__hideSysTrayIcon()

        if self.__visibleMode in [BSSysTray.SYSTRAY_MODE_ALWAYS, BSSysTray.SYSTRAY_MODE_WHENACTIVE]:
            self.__tray.showMessage(title, message, icon)
        elif self.__visibleMode == BSSysTray.SYSTRAY_MODE_FORNOTIFICATION:
            self.__tray.show()
            self.__tray.showMessage(title, message, icon)

            # wait 5s before hiding icon in tray
            loop = QEventLoop()
            QTimer.singleShot(5000, hide)
        elif self.__visibleMode == BSSysTray.SYSTRAY_MODE_NEVER:
            tmpTray = QSystemTrayIcon(Krita.instance())
            tmpTray.show()
            tmpTray.showMessage(title, message, icon)
            tmpTray.hide()


    @staticmethod
    def messageInformation(title, message):
        """Display an information message"""
        BSSysTray.__selfInstance.__popMessage(title, message, QSystemTrayIcon.Information)

    @staticmethod
    def messageWarning(title, message):
        """Display a warning message"""
        BSSysTray.__selfInstance.__popMessage(title, message, QSystemTrayIcon.Warning)

    @staticmethod
    def messageCritical(title, message):
        """Display a critical message"""
        BSSysTray.__selfInstance.__popMessage(title, message, QSystemTrayIcon.Critical)
