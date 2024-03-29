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

from os.path import join, getsize
import os


from buliscript.pktk.modules.hlist import HList

from buliscript.pktk.pktk import (
        EInvalidType,
        EInvalidValue
    )

# -----------------------------------------------------------------------------

class BSHistory(HList):

    def removeMissingFiles(self):
        """Remove missing directories from history"""
        modified=False
        tmpList=[]
        for path in self.list():
            if isinstance(path, str) and os.path.isfile(path):
                tmpList.append(path)
            else:
                modified=True
        if modified:
            self.setItems(tmpList)
