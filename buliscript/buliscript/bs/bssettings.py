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

from enum import Enum


import PyQt5.uic
from PyQt5.Qt import *
from PyQt5.QtCore import (
        pyqtSignal,
        QSettings,
        QStandardPaths
    )
from PyQt5.QtWidgets import (
        QDialog,
        QMessageBox
    )

from os.path import join, getsize
import json
import os
import re
import sys
import shutil

from .bssystray import BSSysTray

from buliscript.pktk.modules.utils import (
        checkKritaVersion,
        Debug
    )
from buliscript.pktk.modules.settings import (
                        Settings,
                        SettingsFmt,
                        SettingsKey,
                        SettingsRule
                    )
from buliscript.pktk.pktk import (
        EInvalidType,
        EInvalidValue
    )

# -----------------------------------------------------------------------------

class BSSettingsKey(SettingsKey):
    CONFIG_OPEN_ATSTARTUP =                                  'config.open.atStartup'
    CONFIG_SYSTRAY_MODE =                                    'config.systray.mode'

    CONFIG_SESSION_SAVE =                                    'config.session.save'
    CONFIG_SESSION_DOCUMENTS_RECENTS_COUNT =                 'config.session.documents.recents.count'

    CONFIG_EDITOR_FONT_NAME =                                'config.editor.font.name'
    CONFIG_EDITOR_FONT_SIZE =                                'config.editor.font.size'
    CONFIG_EDITOR_INDENT_WIDTH =                             'config.editor.indent.width'
    CONFIG_EDITOR_INDENT_VISIBLE =                           'config.editor.indent.visible'
    CONFIG_EDITOR_SPACES_VISIBLE =                           'config.editor.spaces.visible'
    CONFIG_EDITOR_RIGHTLIMIT_WIDTH =                         'config.editor.rightLimit.width'
    CONFIG_EDITOR_RIGHTLIMIT_VISIBLE =                       'config.editor.rightLimit.visible'
    CONFIG_EDITOR_AUTOCOMPLETION_ACTIVE =                    'config.editor.autoCompletion.active'

    SESSION_MAINWINDOW_SPLITTER_MAIN_POSITION =              'session.mainwindow.splitter.main.position'
    SESSION_MAINWINDOW_SPLITTER_SECONDARY_POSITION =         'session.mainwindow.splitter.secondary.position'
    SESSION_MAINWINDOW_WINDOW_GEOMETRY =                     'session.mainwindow.window.geometry'
    SESSION_MAINWINDOW_WINDOW_MAXIMIZED =                    'session.mainwindow.window.maximized'

    SESSION_MAINWINDOW_VIEW_CANVAS_VISIBLE =                 'session.mainwindow.view.canvas.visible'
    SESSION_MAINWINDOW_VIEW_CANVAS_ORIGIN =                  'session.mainwindow.view.canvas.origin'
    SESSION_MAINWINDOW_VIEW_CANVAS_GRID =                    'session.mainwindow.view.canvas.grid'
    SESSION_MAINWINDOW_VIEW_CANVAS_POSITION =                'session.mainwindow.view.canvas.position'

    SESSION_MAINWINDOW_VIEW_CONSOLE_VISIBLE =                'session.mainwindow.view.console.visible'

    SESSION_DOCUMENTS_OPENED =                               'session.documents.opened'
    SESSION_DOCUMENTS_RECENTS =                              'session.documents.recents'

    # keep in memory last path used in open/save dialog box
    SESSION_PATH_LASTOPENED =                                'session.paths.last.opened'
    SESSION_PATH_LASTSAVED =                                 'session.paths.last.saved'



class BSSettings(Settings):
    """Manage all BuliScript settings with open&save options

    Configuration is saved as JSON file
    """

    def __init__(self, pluginId=None):
        """Initialise settings"""
        if pluginId is None or pluginId == '':
            pluginId = 'buliscript'

        # define current rules for options
        rules = [
            # values are tuples:
            # [0]       = default value
            # [1..n]    = values types & accepted values
            SettingsRule(BSSettingsKey.CONFIG_SYSTRAY_MODE,                             2,                        SettingsFmt(int, [0,1,2,3])),
            SettingsRule(BSSettingsKey.CONFIG_OPEN_ATSTARTUP,                           False,                    SettingsFmt(bool)),

            SettingsRule(BSSettingsKey.CONFIG_SESSION_SAVE,                             True,                     SettingsFmt(bool)),
            SettingsRule(BSSettingsKey.CONFIG_SESSION_DOCUMENTS_RECENTS_COUNT,          25,                       SettingsFmt(int, (1, 100))),

            SettingsRule(BSSettingsKey.CONFIG_EDITOR_FONT_NAME,                         "DejaVu Sans Mono",       SettingsFmt(str)),
            SettingsRule(BSSettingsKey.CONFIG_EDITOR_FONT_SIZE,                         9,                        SettingsFmt(int, (5, 96))),

            SettingsRule(BSSettingsKey.CONFIG_EDITOR_INDENT_WIDTH,                      4,                        SettingsFmt(int, (1,8))),
            SettingsRule(BSSettingsKey.CONFIG_EDITOR_INDENT_VISIBLE,                    True,                     SettingsFmt(bool)),
            SettingsRule(BSSettingsKey.CONFIG_EDITOR_SPACES_VISIBLE,                    True,                     SettingsFmt(bool)),

            SettingsRule(BSSettingsKey.CONFIG_EDITOR_RIGHTLIMIT_WIDTH,                  120,                      SettingsFmt(int, (40, 240))),
            SettingsRule(BSSettingsKey.CONFIG_EDITOR_RIGHTLIMIT_VISIBLE,                True,                     SettingsFmt(bool)),

            SettingsRule(BSSettingsKey.CONFIG_EDITOR_AUTOCOMPLETION_ACTIVE,             True,                     SettingsFmt(bool)),


            SettingsRule(BSSettingsKey.SESSION_MAINWINDOW_SPLITTER_MAIN_POSITION,       [1000, 1000],             SettingsFmt(int), SettingsFmt(int)),
            SettingsRule(BSSettingsKey.SESSION_MAINWINDOW_SPLITTER_SECONDARY_POSITION,  [700, 300],               SettingsFmt(int), SettingsFmt(int)),
            SettingsRule(BSSettingsKey.SESSION_MAINWINDOW_WINDOW_GEOMETRY,              [-1,-1,-1,-1],            SettingsFmt(int), SettingsFmt(int), SettingsFmt(int), SettingsFmt(int)),
            SettingsRule(BSSettingsKey.SESSION_MAINWINDOW_WINDOW_MAXIMIZED,             False,                    SettingsFmt(bool)),

            SettingsRule(BSSettingsKey.SESSION_MAINWINDOW_VIEW_CANVAS_VISIBLE,          True,                     SettingsFmt(bool)),
            SettingsRule(BSSettingsKey.SESSION_MAINWINDOW_VIEW_CANVAS_ORIGIN,           True,                     SettingsFmt(bool)),
            SettingsRule(BSSettingsKey.SESSION_MAINWINDOW_VIEW_CANVAS_GRID,             False,                    SettingsFmt(bool)),
            SettingsRule(BSSettingsKey.SESSION_MAINWINDOW_VIEW_CANVAS_POSITION,         True,                     SettingsFmt(bool)),

            SettingsRule(BSSettingsKey.SESSION_MAINWINDOW_VIEW_CONSOLE_VISIBLE,         True,                     SettingsFmt(bool)),

            SettingsRule(BSSettingsKey.SESSION_DOCUMENTS_OPENED,                        [],                       SettingsFmt(list)),
            SettingsRule(BSSettingsKey.SESSION_DOCUMENTS_RECENTS,                       [],                       SettingsFmt(list)),

            SettingsRule(BSSettingsKey.SESSION_PATH_LASTOPENED,                         "",                       SettingsFmt(str)),
            SettingsRule(BSSettingsKey.SESSION_PATH_LASTSAVED,                          "",                       SettingsFmt(str))

        ]

        super(BSSettings, self).__init__(pluginId, rules)
