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

import os.path
from pathlib import Path

import sys
import re

from PyQt5.Qt import *
from PyQt5.QtCore import (
        QDir,
        QRect
    )

from PyQt5.QtWidgets import (
        QMessageBox,
        QWidget
    )


from .bsmainwindow import BSMainWindow
from .bssystray import BSSysTray
from .bssettings import (
        BSSettings,
        BSSettingsKey
    )

from buliscript.pktk.modules.uitheme import UITheme
from buliscript.pktk.modules.utils import (
        checkKritaVersion,
        Debug
    )
from buliscript.pktk.modules.imgutils import buildIcon
from buliscript.pktk.modules.about import AboutWindow

from buliscript.pktk.pktk import (
        EInvalidType,
        EInvalidValue,
        EInvalidStatus
    )

from buliscript.pktk.modules.ekrita import (
        EKritaNode
    )


# ------------------------------------------------------------------------------
class BSUIController(QObject):
    """The controller provide an access to all BuliScript functions
    """
    __EXTENDED_OPEN_OK = 1
    __EXTENDED_OPEN_KO = -1
    __EXTENDED_OPEN_CANCEL = 0

    bsWindowShown = pyqtSignal()
    bsWindowClosed = pyqtSignal()

    def __init__(self, bsName="Buli Script", bsVersion="testing", kritaIsStarting=False):
        super(BSUIController, self).__init__(None)

        self.__bsStarted = False
        self.__bsStarting = False


        self.__window = None
        self.__bsName = bsName
        self.__bsVersion = bsVersion
        self.__bsTitle = "{0} - {1}".format(bsName, bsVersion)

        self.__settings = BSSettings('buliscript')

        UITheme.load()
        # BC theme must be loaded before systray is initialized
        # #----- uncomment if local resources # UITheme.load(os.path.join(os.path.dirname(__file__), 'resources'))

        self.__systray=BSSysTray(self)
        self.commandSettingsSysTrayMode(self.__settings.option(BSSettingsKey.CONFIG_SYSTRAY_MODE.id()))

        # store a global reference to activeWindow to be able to work with
        # activeWindow signals
        # https://krita-artists.org/t/krita-4-4-new-api/12247?u=grum999
        self.__kraActiveWindow = None

        self.__initialised = False

        if kritaIsStarting and self.__settings.option(BSSettingsKey.CONFIG_OPEN_ATSTARTUP.id()):
            self.start()


    def start(self):
        if self.__bsStarted:
            # user interface is already started, bring to front and exit
            self.commandViewBringToFront()
            return
        elif self.__bsStarting:
            # user interface is already starting, exit
            return

        self.__bsStarting = True

        # Check if windows are opened and then, connect signal if needed
        self.__checkKritaWindows()


        self.__initialised = False
        self.__window = BSMainWindow(self)
        self.__window.dialogShown.connect(self.__initSettings)

        self.__window.setWindowTitle(self.__bsTitle)
        self.__window.show()
        self.__window.activateWindow()


    # region: initialisation methods -------------------------------------------

    def __initSettings(self):
        """There's some visual settings that need to have the window visible
        (ie: the widget size are known) to be applied
        """
        if self.__initialised:
            self.__bsStarted = True
            self.bsWindowShown.emit()
            # already initialised, do nothing
            return

        # Here we know we have an active window
        if self.__kraActiveWindow is None:
            self.__kraActiveWindow=Krita.instance().activeWindow()
        try:
            # should not occurs as uicontroller is initialised only once, but...
            self.__kraActiveWindow.themeChanged.disconnect(self.__themeChanged)
        except:
            pass
        self.__kraActiveWindow.themeChanged.connect(self.__themeChanged)

        self.__window.initMainView()

        self.commandSettingsSaveSessionOnExit(self.__settings.option(BSSettingsKey.CONFIG_SESSION_SAVE.id()))
        self.commandSettingsSysTrayMode(self.__settings.option(BSSettingsKey.CONFIG_SYSTRAY_MODE.id()))
        self.commandSettingsOpenAtStartup(self.__settings.option(BSSettingsKey.CONFIG_OPEN_ATSTARTUP.id()))

        self.commandViewMainWindowGeometry(self.__settings.option(BSSettingsKey.SESSION_MAINWINDOW_WINDOW_GEOMETRY.id()))
        self.commandViewMainWindowMaximized(self.__settings.option(BSSettingsKey.SESSION_MAINWINDOW_WINDOW_MAXIMIZED.id()))
        self.commandViewMainSplitterPosition(self.__settings.option(BSSettingsKey.SESSION_MAINWINDOW_SPLITTER_MAIN_POSITION.id()))
        self.commandViewSecondarySplitterPosition(self.__settings.option(BSSettingsKey.SESSION_MAINWINDOW_SPLITTER_SECONDARY_POSITION.id()))

        self.commandViewShowCanvasVisible(self.__settings.option(BSSettingsKey.SESSION_MAINWINDOW_VIEW_CANVAS_VISIBLE.id()))
        self.commandViewShowCanvasOrigin(self.__settings.option(BSSettingsKey.SESSION_MAINWINDOW_VIEW_CANVAS_ORIGIN.id()))
        self.commandViewShowCanvasGrid(self.__settings.option(BSSettingsKey.SESSION_MAINWINDOW_VIEW_CANVAS_GRID.id()))
        self.commandViewShowCanvasPosition(self.__settings.option(BSSettingsKey.SESSION_MAINWINDOW_VIEW_CANVAS_POSITION.id()))
        self.commandViewShowConsoleVisible(self.__settings.option(BSSettingsKey.SESSION_MAINWINDOW_VIEW_CONSOLE_VISIBLE.id()))

        self.__window.initMenu()

        self.__initialised = True
        self.__bsStarted = True
        self.__bsStarting = False
        self.bsWindowShown.emit()


    def __themeChanged(self):
        """Theme has been changed, reload resources"""
        def buildPixmapList(widget):
            pixmaps=[]
            for propertyName in widget.dynamicPropertyNames():
                pName=bytes(propertyName).decode()
                if re.match('__bsIcon_', pName):
                    # a reference to resource path has been stored,
                    # reload icon from it
                    if pName == '__bsIcon_normalon':
                        pixmaps.append( (QPixmap(widget.property(propertyName)), QIcon.Normal, QIcon.On) )
                    elif pName == '__bsIcon_normaloff':
                        pixmaps.append( (QPixmap(widget.property(propertyName)), QIcon.Normal, QIcon.Off) )
                    elif pName == '__bsIcon_disabledon':
                        pixmaps.append( (QPixmap(widget.property(propertyName)), QIcon.Disabled, QIcon.On) )
                    elif pName == '__bsIcon_disabledoff':
                        pixmaps.append( (QPixmap(widget.property(propertyName)), QIcon.Disabled, QIcon.Off) )
                    elif pName == '__bsIcon_activeon':
                        pixmaps.append( (QPixmap(widget.property(propertyName)), QIcon.Active, QIcon.On) )
                    elif pName == '__bsIcon_activeoff':
                        pixmaps.append( (QPixmap(widget.property(propertyName)), QIcon.Active, QIcon.Off) )
                    elif pName == '__bsIcon_selectedon':
                        pixmaps.append( (QPixmap(widget.property(propertyName)), QIcon.Selected, QIcon.On) )
                    elif pName == '__bsIcon_selectedoff':
                        pixmaps.append( (QPixmap(widget.property(propertyName)), QIcon.Selected, QIcon.Off) )
            return pixmaps

        UITheme.reloadResources()

        # need to apply new palette to widgets
        # otherwise it seems they keep to refer to the old palette...
        palette = QApplication.palette()
        widgetList = self.__window.getWidgets()

        for widget in widgetList:
            if isinstance(widget, BCWPathBar) or isinstance(widget, BreadcrumbsAddressBar):
                widget.updatePalette()
            elif hasattr(widget, 'setPalette'):
                # force palette to be applied to widget
                widget.setPalette(palette)

            if isinstance(widget, QTabWidget):
                # For QTabWidget, it's not possible to set icon directly,
                # need to use setTabIcon()
                for tabIndex in range(widget.count()):
                    tabWidget = widget.widget(tabIndex)

                    if not widget.tabIcon(tabIndex) is None:
                        pixmaps=buildPixmapList(tabWidget)
                        if len(pixmaps) > 0:
                            widget.setTabIcon(tabIndex, buildIcon(pixmaps))

            # need to do something to relad icons...
            elif hasattr(widget, 'icon'):
                pixmaps=buildPixmapList(widget)
                if len(pixmaps) > 0:
                    widget.setIcon(buildIcon(pixmaps))



    def __checkKritaWindows(self):
        """Check if windows signal windowClosed() is already defined and, if not,
        define it
        """
        # applicationClosing signal can't be used, because when while BS is opened,
        # application is still running and then signal is not trigerred..
        #
        # solution is, when a window is closed, to check how many windows are still
        # opened
        #
        for window in Krita.instance().windows():
            # DO NOT SET PROPERTY ON WINDOW
            # but on qwindow() as the qwindow() is always the same
            # and as window is just an instance that wrap the underlied QMainWindow
            # a new object is returned each time windows() list is returned
            if window.qwindow().property('__bsWindowClosed') != True:
                window.windowClosed.connect(self.__windowClosed)
                window.qwindow().setProperty('__bsWindowClosed', True)


    def __windowClosed(self):
        """A krita window has been closed"""
        # check how many windows are still opened
        # if there's no window opened, close BS

        # need to ensure that all windows are connected to close signal
        # (maybe, since BS has been opened, new Krita windows has been created...)
        self.__checkKritaWindows()

        if len( Krita.instance().windows()) == 0:
            self.commandQuit()


    # endregion: initialisation methods ----------------------------------------


    # region: getter/setters ---------------------------------------------------

    def name(self):
        """Return name"""
        return self.__bsName

    def settings(self):
        """return setting manager"""
        return self.__settings

    def theme(self):
        """Return theme object"""
        return self.__theme

    def started(self):
        """Return True if BuliScript interface is started"""
        return self.__bsStarted

    def version(self):
        return self.__bsVersion

    def title(self):
        return self.__bsTitle

    # endregion: getter/setters ------------------------------------------------


    # region: define commands --------------------------------------------------

    def saveSettings(self):
        """Save the current settings"""
        self.__settings.setOption(BSSettingsKey.CONFIG_SESSION_SAVE, self.__window.actionSettingsSaveSessionOnExit.isChecked())

        if self.__settings.option(BSSettingsKey.CONFIG_SESSION_SAVE.id()):
            # save current session properties only if allowed
            if self.__window.actionViewShowCanvas.isChecked():
                # if not checked, hidden panel size is 0 so, do not save it (splitter position is already properly defined)
                self.__settings.setOption(BSSettingsKey.SESSION_MAINWINDOW_SPLITTER_MAIN_POSITION, self.__window.splMain.sizes())

            self.__settings.setOption(BSSettingsKey.SESSION_MAINWINDOW_VIEW_CANVAS_VISIBLE, self.__window.actionViewShowCanvas.isChecked())
            self.__settings.setOption(BSSettingsKey.SESSION_MAINWINDOW_VIEW_CANVAS_ORIGIN, self.__window.actionViewShowCanvasOrigin.isChecked())
            self.__settings.setOption(BSSettingsKey.SESSION_MAINWINDOW_VIEW_CANVAS_GRID, self.__window.actionViewShowCanvasGrid.isChecked())
            self.__settings.setOption(BSSettingsKey.SESSION_MAINWINDOW_VIEW_CANVAS_POSITION, self.__window.actionViewShowCanvasPosition.isChecked())

            if self.__window.actionViewShowConsole.isChecked():
                # if not checked, hidden panel size is 0 so, do not save it (splitter position is already properly defined)
                self.__settings.setOption(BSSettingsKey.SESSION_MAINWINDOW_SPLITTER_SECONDARY_POSITION, self.__window.splSecondary.sizes())

            self.__settings.setOption(BSSettingsKey.SESSION_MAINWINDOW_VIEW_CONSOLE_VISIBLE, self.__window.actionViewShowConsole.isChecked())

            self.__settings.setOption(BSSettingsKey.SESSION_MAINWINDOW_WINDOW_MAXIMIZED, self.__window.isMaximized())
            if not self.__window.isMaximized():
                # when maximized geometry is full screen geomtry, then do it only if no in maximized
                self.__settings.setOption(BSSettingsKey.SESSION_MAINWINDOW_WINDOW_GEOMETRY, [self.__window.geometry().x(), self.__window.geometry().y(), self.__window.geometry().width(), self.__window.geometry().height()])

        return self.__settings.saveConfig()

    def close(self):
        """When window is about to be closed, execute some cleanup/backup/stuff before exiting BuliScript"""
        # save current settings
        self.saveSettings()

        self.__bsStarted = False
        self.bsWindowClosed.emit()

    def optionIsMaximized(self):
        """Return current option value"""
        return self.__window.isMaximized()

    def commandQuit(self):
        """Close Buli Script"""
        self.__window.close()

    def commandFileOpen(self, file=None):
        """Open file"""
        if isinstance(file, str):
            return False

            try:
                # not yet implemented
                pass
            except Exception as e:
                Debug.print('[BSUIController.commandFileOpen] unable to open file {0}: {1}', file, str(e))
                return False
            return True
        else:
            raise EInvalidType('Given `file` is not valid')

    def commandViewBringToFront(self):
        """Bring main window to front"""
        self.__window.setWindowState( (self.__window.windowState() & ~Qt.WindowMinimized) | Qt.WindowActive)
        self.__window.activateWindow()

    def commandViewMainSplitterPosition(self, positions=None):
        """Set the mainwindow main splitter position

        Given `positions` is a list [<panel0 size>,<panel1 size>]
        If value is None, will define a default 50%-50%
        """
        if positions is None:
            positions = [1000, 1000]

        if not isinstance(positions, list) or len(positions) != 2:
            raise EInvalidValue('Given `positions` must be a list [l,r]')

        self.__window.splMain.setSizes(positions)

        return positions

    def commandViewSecondarySplitterPosition(self, positions=None):
        """Set the mainwindow secondary splitter position

        Given `positions` is a list [<panel0 size>,<panel1 size>]
        If value is None, will define a default 50%-50%
        """
        if positions is None:
            positions = [700, 300]

        if not isinstance(positions, list) or len(positions) != 2:
            raise EInvalidValue('Given `positions` must be a list [l,r]')

        self.__window.splSecondary.setSizes(positions)

        return positions

    def commandViewMainWindowMaximized(self, maximized=False):
        """Set the window state"""
        if not isinstance(maximized, bool):
            raise EInvalidValue('Given `maximized` must be a <bool>')

        if maximized:
            # store current geometry now because after window is maximized, it's lost
            self.__settings.setOption(BSSettingsKey.SESSION_MAINWINDOW_WINDOW_GEOMETRY, [self.__window.geometry().x(), self.__window.geometry().y(), self.__window.geometry().width(), self.__window.geometry().height()])
            self.__window.showMaximized()
        else:
            self.__window.showNormal()

        return maximized

    def commandViewMainWindowGeometry(self, geometry=[-1,-1,-1,-1]):
        """Set the window geometry

        Given `geometry` is a list [x,y,width,height] or a QRect()
        """
        if isinstance(geometry, QRect):
            geometry = [geometry.x(), geometry.y(), geometry.width(), geometry.height()]

        if not isinstance(geometry, list) or len(geometry)!=4:
            raise EInvalidValue('Given `geometry` must be a <list[x,y,w,h]>')

        rect = self.__window.geometry()

        if geometry[0] >= 0:
            rect.setX(geometry[0])

        if geometry[1] >= 0:
            rect.setY(geometry[1])

        if geometry[2] >= 0:
            rect.setWidth(geometry[2])

        if geometry[3] >= 0:
            rect.setHeight(geometry[3])

        self.__window.setGeometry(rect)

        return [self.__window.geometry().x(), self.__window.geometry().y(), self.__window.geometry().width(), self.__window.geometry().height()]

    def commandViewShowCanvasVisible(self, visible=None):
        """Display/Hide canvas"""
        if visible is None:
            visible = self.__window.actionViewShowCanvas.isChecked()
        elif isinstance(visible, bool):
            self.__window.actionViewShowCanvas.setChecked(visible)
        else:
            raise EInvalidValue('Given `visible` must be a <bool>')

        if not visible:
            # when hidden, canvas panel width is set to 0, then save current size now
            self.__settings.setOption(BSSettingsKey.SESSION_MAINWINDOW_SPLITTER_MAIN_POSITION, self.__window.splMain.sizes())

        self.__window.wRightArea.setVisible(visible)

    def commandViewShowCanvasOrigin(self, visible=None):
        """Display/Hide canvas origin"""
        if visible is None:
            visible = self.__window.actionViewShowCanvasOrigin.isChecked()
        elif isinstance(visible, bool):
            self.__window.actionViewShowCanvasOrigin.setChecked(visible)
        else:
            raise EInvalidValue('Given `visible` must be a <bool>')

        # updated in saveSettings()
        #self.__settings.setOption(BSSettingsKey.SESSION_MAINWINDOW_VIEW_CANVAS_ORIGIN, visible)
        Debug.print('TODO: update canvas (origin)')

    def commandViewShowCanvasGrid(self, visible=None):
        """Display/Hide canvas grid"""
        if visible is None:
            visible = self.__window.actionViewShowCanvasGrid.isChecked()
        elif isinstance(visible, bool):
            self.__window.actionViewShowCanvasGrid.setChecked(visible)
        else:
            raise EInvalidValue('Given `visible` must be a <bool>')

        # updated in saveSettings()
        #self.__settings.setOption(BSSettingsKey.SESSION_MAINWINDOW_VIEW_CANVAS_GRID, visible)
        Debug.print('TODO: update canvas (grid)')

    def commandViewShowCanvasPosition(self, visible=None):
        """Display/Hide canvas position"""
        if visible is None:
            visible = self.__window.actionViewShowCanvasPosition.isChecked()
        elif isinstance(visible, bool):
            self.__window.actionViewShowCanvasPosition.setChecked(visible)
        else:
            raise EInvalidValue('Given `visible` must be a <bool>')

        # updated in saveSettings()
        #self.__settings.setOption(BSSettingsKey.SESSION_MAINWINDOW_VIEW_CANVAS_POSITION, visible)
        Debug.print('TODO: update canvas (position)')

    def commandViewShowConsoleVisible(self, visible=None):
        """Display/Hide canvas"""
        if visible is None:
            visible = self.__window.actionViewShowConsole.isChecked()
        elif isinstance(visible, bool):
            self.__window.actionViewShowConsole.setChecked(visible)
        else:
            raise EInvalidValue('Given `visible` must be a <bool>')

        if not visible:
            # when hidden, canvas panel width is set to 0, then save current size now
            self.__settings.setOption(BSSettingsKey.SESSION_MAINWINDOW_SPLITTER_SECONDARY_POSITION, self.__window.splSecondary.sizes())

        self.__window.wConsoleArea.setVisible(visible)

    def commandSettingsSaveSessionOnExit(self, saveSession=None):
        """Define if current session properties have to be save or not"""
        if saveSession is None:
            saveSession = self.__window.actionSettingsSaveSessionOnExit.isChecked()
        elif isinstance(saveSession, bool):
            self.__window.actionSettingsSaveSessionOnExit.setChecked(saveSession)
        else:
            raise EInvalidValue('Given `visible` must be a <bool>')

    def commandSettingsSysTrayMode(self, value=BSSysTray.SYSTRAY_MODE_WHENACTIVE):
        """Set mode for systray notifier"""
        self.__settings.setOption(BSSettingsKey.CONFIG_SYSTRAY_MODE, value)
        self.__systray.setVisibleMode(value)

    def commandSettingsOpenAtStartup(self, value=False):
        """Set option to start BS at Krita's startup"""
        self.__settings.setOption(BSSettingsKey.CONFIG_OPEN_ATSTARTUP, value)

    def commandSettingsOpen(self):
        """Open dialog box settings"""
        if BSSettingsDialogBox.open(f'{self.__bsName}::Settings', self):
            self.saveSettings()

    def commandAboutBs(self):
        """Display 'About Buli Script' dialog box"""
        AboutWindow(self.__bsName, self.__bsVersion, os.path.join(os.path.dirname(__file__), 'resources', 'png', 'buli-powered-big.png'), None, ':BuliScript')


    # endregion: define commands -----------------------------------------------
