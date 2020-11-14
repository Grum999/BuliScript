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
from .bsutils import (
        checkKritaVersion,
        Debug
    )

from ..pktk.pktk import (
        EInvalidType,
        EInvalidValue
    )

# -----------------------------------------------------------------------------

class BSSettingsFmt(object):

    def __init__(self, settingType, values=None):
        if not isinstance(settingType, type):
            raise EInvalidType('Given `settingType` must be a type')

        self.__type = settingType
        self.__values = values

    def check(self, value, checkType=None):
        """Check if given value match setting format"""
        if checkType is None:
            checkType = self.__type

        if not isinstance(value, checkType):
            raise EInvalidType(f'Given `value` ({value}) is not from expected type ({checkType})')

        if not self.__values is None:
            if isinstance(value, list) or isinstance(value, tuple):
                # need to check all items
                if isinstance(self.__values, type):
                    # check if all items are of given type
                    for item in value:
                        self.check(item, self.__values)
                else:
                    # check items values
                    for item in value:
                        self.check(item)
            elif isinstance(self.__values, list) or isinstance(self.__values, tuple):
                if not value in self.__values:
                    raise EInvalidValue('Given `value` ({0}) is not in authorized perimeter ({1})'.format(value, self.__values))
            elif isinstance(self.__values, re.Pattern):
                if self.__values.match(value) is None:
                    raise EInvalidValue('Given `value` ({0}) is not in authorized perimeter'.format(value))


class BSSettingsKey(Enum):
    CONFIG_OPEN_ATSTARTUP =                                  'config.open.atStartup'
    CONFIG_SYSTRAY_MODE =                                    'config.systray.mode'
    CONFIG_SESSION_SAVE =                                    'config.session.save'

    SESSION_MAINWINDOW_SPLITTER_MAIN_POSITION =              'session.mainwindow.splitter.main.position'
    SESSION_MAINWINDOW_SPLITTER_SECONDARY_POSITION =         'session.mainwindow.splitter.secondary.position'
    SESSION_MAINWINDOW_WINDOW_GEOMETRY =                     'session.mainwindow.window.geometry'
    SESSION_MAINWINDOW_WINDOW_MAXIMIZED =                    'session.mainwindow.window.maximized'

    SESSION_MAINWINDOW_VIEW_CANVAS_VISIBLE =                 'session.mainwindow.view.canvas.visible'
    SESSION_MAINWINDOW_VIEW_CANVAS_ORIGIN =                  'session.mainwindow.view.canvas.origin'
    SESSION_MAINWINDOW_VIEW_CANVAS_GRID =                    'session.mainwindow.view.canvas.grid'
    SESSION_MAINWINDOW_VIEW_CANVAS_POSITION =                'session.mainwindow.view.canvas.position'

    SESSION_MAINWINDOW_VIEW_CONSOLE_VISIBLE =                'session.mainwindow.view.console.visible'


    def id(self, **param):
        if isinstance(param, dict):
            return self.value.format(**param)
        else:
            return self.value


class BSSettings(object):
    """Manage all BuliScript settings with open&save options

    Configuration is saved as JSON file
    """

    def __init__(self, pluginId=None, panelIds=[0, 1]):
        """Initialise settings"""
        if pluginId is None or pluginId == '':
            pluginId = 'buliscript'

        self.__pluginCfgFile = os.path.join(QStandardPaths.writableLocation(QStandardPaths.GenericConfigLocation), f'krita-plugin-{pluginId}rc.json')
        self.__config = {}

        # define current rules for options
        self.__rules = {
            # values are tuples:
            # [0]       = default value
            # [1..n]    = values types & accepted values
            BSSettingsKey.CONFIG_SYSTRAY_MODE.id():                             (2,                        BSSettingsFmt(int, [0,1,2,3])),
            BSSettingsKey.CONFIG_OPEN_ATSTARTUP.id():                           (False,                    BSSettingsFmt(bool)),
            BSSettingsKey.CONFIG_SESSION_SAVE.id():                             (True,                     BSSettingsFmt(bool)),

            BSSettingsKey.SESSION_MAINWINDOW_SPLITTER_MAIN_POSITION.id():       ([1000, 1000],             BSSettingsFmt(int), BSSettingsFmt(int)),
            BSSettingsKey.SESSION_MAINWINDOW_SPLITTER_SECONDARY_POSITION.id():  ([700, 300],               BSSettingsFmt(int), BSSettingsFmt(int)),
            BSSettingsKey.SESSION_MAINWINDOW_WINDOW_GEOMETRY.id():              ([-1,-1,-1,-1],            BSSettingsFmt(int), BSSettingsFmt(int), BSSettingsFmt(int), BSSettingsFmt(int)),
            BSSettingsKey.SESSION_MAINWINDOW_WINDOW_MAXIMIZED.id():             (False,                    BSSettingsFmt(bool)),

            BSSettingsKey.SESSION_MAINWINDOW_VIEW_CANVAS_VISIBLE.id():          (True,                     BSSettingsFmt(bool)),
            BSSettingsKey.SESSION_MAINWINDOW_VIEW_CANVAS_ORIGIN.id():           (True,                     BSSettingsFmt(bool)),
            BSSettingsKey.SESSION_MAINWINDOW_VIEW_CANVAS_GRID.id():             (False,                    BSSettingsFmt(bool)),
            BSSettingsKey.SESSION_MAINWINDOW_VIEW_CANVAS_POSITION.id():         (True,                     BSSettingsFmt(bool)),

            BSSettingsKey.SESSION_MAINWINDOW_VIEW_CONSOLE_VISIBLE.id():         (True,                     BSSettingsFmt(bool))
        }

        self.setDefaultConfig()
        self.loadConfig()

    def __setValue(self, target, id, value):
        """From an id like 'a.b.c', set value in target dictionary"""
        keys = id.split('.', 1)

        if len(keys) == 1:
            target[keys[0]] = value
        else:
            if not keys[0] in target:
                target[keys[0]] = {}

            self.__setValue(target[keys[0]], keys[1], value)

    def __getValue(self, target, id):
        """From an id like 'a.b.c', get value in target dictionary"""
        keys = id.split('.', 1)

        if len(keys) == 1:
            return target[keys[0]]
        else:
            return self.__getValue(target[keys[0]], keys[1])

    def configurationFile(self):
        """Return the configuration file name"""
        return self.__pluginCfgFile

    def setDefaultConfig(self):
        """Reset default configuration"""
        self.__config = {}

        for rule in self.__rules:
            self.__setValue(self.__config, rule, self.__rules[rule][0])

    def loadConfig(self):
        """Load configuration from file

        If file doesn't exist return False
        Otherwise True
        """
        def setKeyValue(sourceKey, value):
            if isinstance(value, dict):
                for key in value:
                    setKeyValue(f'{sourceKey}.{key}', value[key])
            else:
                self.setOption(sourceKey, value)

        jsonAsDict = None

        if os.path.isfile(self.__pluginCfgFile):
            with open(self.__pluginCfgFile, 'r') as file:
                try:
                    jsonAsStr = file.read()
                except Exception as e:
                    Debug.print('[BSSettings.loadConfig] Unable to load file {0}: {1}', self.__pluginCfgFile, str(e))
                    return False

                try:
                    jsonAsDict = json.loads(jsonAsStr)
                except Exception as e:
                    Debug.print('[BSSettings.loadConfig] Unable to parse file {0}: {1}', self.__pluginCfgFile, str(e))
                    return False
        else:
            return False

        # parse all items, and set current config
        for key in jsonAsDict:
            setKeyValue(key, jsonAsDict[key])

        return True

    def saveConfig(self):
        """Save configuration to file

        If file can't be saved, return False
        Otherwise True
        """
        with open(self.__pluginCfgFile, 'w') as file:
            try:
                file.write(json.dumps(self.__config, indent=4, sort_keys=True))
            except Exception as e:
                Debug.print('[BSSettings.saveConfig] Unable to save file {0}: {1}', self.__pluginCfgFile, str(e))
                return False

        return True

    def setOption(self, id, value):
        """Set value for given option

        Given `id` must be valid (a BSSettingsKey)
        Given `value` format must be valid (accordiing to id, a control is made)
        """
        # check if id is valid
        if isinstance(id, BSSettingsKey):
            id = id.id()

        if not isinstance(id, str) or not id in self.__rules:
            #raise EInvalidValue(f'Given `id` is not valid: {id}')
            Debug.print('[BSSettings.setOption] Given id `{0}` is not valid', id)
            return

        # check if value is valid
        rules = self.__rules[id][1:]
        if len(rules) > 1:
            # value must be a list
            if not isinstance(value, list):
                #raise EInvalidType(f'Given `value` must be a list: {value}')
                Debug.print('[BSSettings.setOption] Given value for id `{1}` must be a list: `{0}`', value, id)
                return

            # number of item must match number of rules
            if len(rules) != len(value):
                Debug.print('[BSSettings.setOption] Given value for id `{1}` is not a valid list: `{0}`', value, id)
                return

            # check if each item match corresponding rule
            for index in range(len(value)):
                rules[index].check(value[index])
        else:
            rules[0].check(value)

        # value is valid, set it
        self.__setValue(self.__config, id, value)

    def option(self, id):
        """Return value for option"""
        # check if id is valid
        if isinstance(id, BSSettingsKey):
            id = id.id()

        if not isinstance(id, str) or not id in self.__rules:
            raise EInvalidValue(f'Given `id` is not valid: {id}')


        return self.__getValue(self.__config, id)

    def options(self):
        return self.__config


