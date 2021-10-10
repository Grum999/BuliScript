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

import html
import re

from PyQt5.Qt import *
from PyQt5.QtWidgets import QDockWidget
from PyQt5.QtCore import (
        pyqtSignal as Signal
    )


from buliscript.pktk.modules.imgutils import buildIcon
from buliscript.pktk.widgets.wdockwidget import WDockWidget


class BSDockWidgetLangageQuickHelp(WDockWidget):
    """A dock widget to display quick help about language

    Docker is made of:
    - A QLabel: used to display title
    - A QTextBrowser: used to display formatted text help
    """

    def __init__(self, parent, name='Language Quick Help'):
        super(BSDockWidgetLangageQuickHelp, self).__init__(name, parent)

        self.__syntax=None
        self.__description=None
        self.__example=None

        self.__widget=QWidget(self)
        self.__widget.setMinimumWidth(200)

        self.__layout=QVBoxLayout(self.__widget)
        self.__widget.setLayout(self.__layout)

        self.__title=QLabel(self)
        self.__title.setSizePolicy(QSizePolicy(QSizePolicy.Preferred,QSizePolicy.Maximum))
        self.__title.setText(i18n("Language Quick Help"))
        #self.__title.setStyleSheet("QLabel { background-color: palette(light); padding: 6; font-weight: bold; }")
        self.__title.setStyleSheet("QLabel { font-weight: bold; }")

        self.__documentation=QTextBrowser(self)
        self.__documentation.setOpenExternalLinks(True)
        self.__documentation.setSizePolicy(QSizePolicy(QSizePolicy.Preferred,QSizePolicy.MinimumExpanding))
        self.__documentation.setHtml(i18n("""<html><body><p>Quick help is displayed from:</p>
            <ul>
                <li>From script source<br><i>&gt; place cursor on an instruction to get quick help</i></li>
                <li>From <i>Language Reference</i> docker<br><i>&gt;select a language instruction to get quick help</i></li>
                <li>From <i>Language</i> menu<br><i>&gt;move mouse hover a language menu item to get quick help</i></li>
            </ul>
            </body>
        </html>
        """))

        self.__layout.addWidget(self.__title)
        self.__layout.addWidget(self.__documentation)

        self.setWidget(self.__widget)

    def __reformattedSyntaxText(self, text):
        """Reformat given text, assuming it's a completion text command"""
        returned=[]
        texts=text.split('\x01')
        for index, textItem in enumerate(texts):
            if index%2==1:
                # odd text ("optionnal" information) are written smaller, with darker color
                returned.append(f"<i>{textItem}</i>")
            else:
                # normal font
                returned.append(textItem)

        return ''.join(returned)


    def title(self):
        """Return current title"""
        return self.__title.text()

    def setTitle(self, value):
        """Set current title"""
        self.__title.setText(value)

    def syntax(self):
        """Return current syntax"""
        return self.__syntax

    def description(self):
        """Return current description"""
        return self.__description

    def example(self):
        """Return current example"""
        return self.__example

    def set(self, title, syntax, description, example):
        """Convenience method to set all docker quick help content"""
        self.setTitle(title)

        self.__syntax=syntax
        self.__description=description
        self.__example=example

        if example!='':
            example=f'<h1>Example</h1><p>{example}</p>'

        # define HTML content
        htmlContent=f'''
        <html>
            <body>
                <h1>Syntax</h1>
                <p>
                    <span style="font-family:monospace">{self.__reformattedSyntaxText(html.escape(syntax))}</span>
                </p>

                <h1>Description</h1>
                <p>
                    {description}
                </p>

                {example}
            </body>
        </html>
        '''

        self.__documentation.setHtml(htmlContent)



class BSDockWidgetLangageReference(WDockWidget):
    """A dock widget to display reference language

    Docker is made of:
    - A QLineEdit: used as search filter
    - QButton: used for exand/collapse everything in treeview | switch between tree/flat view
    - A QTreeView: used to provide all language reference items in a structured format (like language menu)
    """
    languageReferenceSelected=Signal(str)
    languageReferenceDblClicked=Signal(str)

    def __init__(self, parent, languageDef, name='Language Reference'):
        super(BSDockWidgetLangageReference, self).__init__(name, parent)

        self.__widget=QWidget(self)
        self.__widget.setMinimumWidth(200)

        self.__layout=QVBoxLayout(self.__widget)
        self.__widget.setLayout(self.__layout)

        self.__tvLanguageRef=BSLangageReferenceView(self)
        self.__tbFilter=BSLangageReferenceTBar(self)
        self.__tbFilter.setLanguageReferenceView(self.__tvLanguageRef)

        self.__tvLanguageRef.selectionModel().currentChanged.connect(self.__selectedItemChanged)
        self.__tvLanguageRef.doubleClicked.connect(self.__itemDblClicked)
        self.__tvLanguageRef.setAllColumnsShowFocus(True)

        self.__layout.addWidget(self.__tbFilter)
        self.__layout.addWidget(self.__tvLanguageRef)

        self.setWidget(self.__widget)

        self.__initialiseReference(languageDef)


    def __initialiseReference(self, languageDef):
        """Initialise language reference model"""
        dataList=[]
        for rule in languageDef.tokenizer().rules():
            for autoCompletion in rule.autoCompletion():
                description=rule.description()
                if not description is None:
                    for treePath in description.split('|'):
                        dataList.append((treePath, autoCompletion[0], languageDef.style(rule), rule.autoCompletionChar()))

        self.__tvLanguageRef.setData(dataList, False)


    def __selectedItemChanged(self, current, previous):
        """Item has changed"""
        data=current.data(BSLangageReferenceModel.VALUE)
        if not data is None:
            self.languageReferenceSelected.emit(data.split('\x01')[0])

    def __itemDblClicked(self, index):
        """Item has been double clicked"""
        data=index.data(BSLangageReferenceModel.VALUE)
        if not data is None:
            self.languageReferenceDblClicked.emit(data)



class BSLangageReferenceTBar(QWidget):
    """Interface to manage filter + buttons"""

    def __init__(self, parent=None):
        super(BSLangageReferenceTBar, self).__init__(parent)
        self.__languageReferenceView=None
        self.__filter=''

        self.__layout=QHBoxLayout(self)
        self.__proxyModel=None

        self.__btExpandAll=QToolButton(self)
        self.__btCollapseAll=QToolButton(self)
        self.__leFilter=QLineEdit(self)

        self.__layout.addWidget(self.__btExpandAll)
        self.__layout.addWidget(self.__btCollapseAll)
        self.__layout.addWidget(self.__leFilter)

        self.__buildUi()

    def __buildUi(self):
        """Build toolbat ui"""
        self.__btExpandAll.setAutoRaise(True)
        self.__btCollapseAll.setAutoRaise(True)
        self.__leFilter.setClearButtonEnabled(True)

        self.__btExpandAll.setIcon(buildIcon('pktk:list_tree_expand'))
        self.__btCollapseAll.setIcon(buildIcon('pktk:list_tree_collapse'))

        self.__leFilter.textEdited.connect(self.__setFilter)
        self.__btExpandAll.clicked.connect(self.expandAll)
        self.__btCollapseAll.clicked.connect(self.collapseAll)

        self.__btExpandAll.setToolTip(i18n('Expand all'))
        self.__btCollapseAll.setToolTip(i18n('Collapse all'))
        self.__leFilter.setToolTip(i18n('Filter language reference\nStart filter with "re:"" or "re/i:"" for regular expression filter'))

        self.__layout.setContentsMargins(0,0,0,0)

        self.__leFilter.findChild(QToolButton).setIcon(QIcon(":/pktk/images/normal/edit_text_clear"))
        self.setLayout(self.__layout)

    def __setFilter(self, filter=''):
        """Set current filter to apply"""
        if filter == self.__filter:
            # filter unchanged, do nothing
            return

        if not isinstance(filter, str):
            raise EInvalidType('Given `filter` must be a <str>')

        self.__filter = filter

        if reFilter:=re.search('^re:(.*)', self.__filter):
            self.__proxyModel.setFilterCaseSensitivity(Qt.CaseSensitive)
            self.__proxyModel.setFilterRegExp(reFilter.groups()[0])
        elif reFilter:=re.search('^re\/i:(.*)', self.__filter):
            self.__proxyModel.setFilterCaseSensitivity(Qt.CaseInsensitive)
            self.__proxyModel.setFilterRegExp(reFilter.groups()[0])
        else:
            self.__proxyModel.setFilterCaseSensitivity(Qt.CaseInsensitive)
            self.__proxyModel.setFilterWildcard(self.__filter)
        # expand automatically results
        self.expandAll()

    def expandAll(self):
        """Expand all nodes"""
        if self.__languageReferenceView:
            self.__languageReferenceView.expandAll()

    def collapseAll(self):
        """Expand all nodes"""
        if self.__languageReferenceView:
            self.__languageReferenceView.collapseAll()

    def setFilter(self, filter=''):
        """Set current filter to apply"""
        if filter == self.__filter:
            # filter unchanged, do nothing
            return

        if not isinstance(filter, str):
            raise EInvalidType('Given `filter` must be a <str>')

        self.__leFilter.setText(filter)
        self.__setFilter(filter)

    def filter(self):
        """Return current applied filter"""
        return self.__filter

    def setLanguageReferenceView(self, languageReferenceView):
        """Set node view to be linked with tool bar"""
        if languageReferenceView is None:
            if not self.__languageReferenceView is None:
                # unlink

                # restore model
                self.__languageReferenceView.setModel(self.__proxyModel.sourceModel())
                self.__languageReferenceView=None
                self.__proxyModel=None
        elif isinstance(languageReferenceView, BSLangageReferenceView):
            # link
            self.setLanguageReferenceView(None)
            self.__languageReferenceView=languageReferenceView

            self.__proxyModel = QSortFilterProxyModel(self)
            self.__proxyModel.setSourceModel(self.__languageReferenceView.model())
            self.__proxyModel.setFilterKeyColumn(0)
            self.__proxyModel.setRecursiveFilteringEnabled(True)

            self.__languageReferenceView.setModel(self.__proxyModel)

    def languageReferenceView(self):
        """Return current linked node view"""
        return self.__languageReferenceView



class BSLangageReferenceNode:
    """A node for BSLangageReferenceModel

    Built from a given dictionary data
    """
    PATH = 0
    VALUE = 1
    STYLE = 2
    CHAR = 3

    def __init__(self, data=None, parent=None):
        """Initialise nodes

        Given `data`can be:
        - a BSLangageReferenceNode
        - a list of tuple (treePath, value)
        - a tuple

        Given `parent` can be None (root) or a BSLangageReferenceNode

        """
        # parent is a BSLangageReferenceNode
        if not parent is None and not isinstance(parent, BSLangageReferenceNode):
            raise EInvalidType("Given `parent` must be a <BSLangageReferenceNode>")

        self.__parent=parent

        # initialise default values
        self.__data=(None, None, None, None)

        # Initialise node childs
        self.__childs=[]

        if isinstance(data, list):
            # list of tuple (treePath, value)
            for dataNfo in data:
                self.__addKeyValue(dataNfo[BSLangageReferenceNode.PATH],
                                   dataNfo[BSLangageReferenceNode.VALUE],
                                   dataNfo[BSLangageReferenceNode.STYLE],
                                   dataNfo[BSLangageReferenceNode.CHAR]
                                )
        elif isinstance(data, tuple):
            self.__data=data

    def __repr__(self):
        return f"<BSLangageReferenceNode({self.__data[0]}, {self.__data[1]})>"

    def __addKeyValue(self, keyPath, value, style, char):
        """Add a key/value pair

        Build tree if needed, or to add as child of path in tree
        """
        if keyPath:
            # need to build path tree
            directory=self.__childFromPath(keyPath)
            directory.addChild(BSLangageReferenceNode((None, value, style, char), directory))
        else:
            self.addChild(BSLangageReferenceNode((None, value, style, char), self))

    def __childFromPath(self, fullPath):
        """Return node from given path

        If path doesn't exist, build it
        """

        # testA/testB/tesC

        if "/" in fullPath:
            path, key=fullPath.split("/", 1)

            foundNode=self.__childFromPath(path)
            if foundNode:
                # exists, continue to search
                return foundNode.__childFromPath(key)
        else:
            for item in self.__childs:
                if item.data(BSLangageReferenceNode.PATH)==fullPath:
                    return item

            item=BSLangageReferenceNode((fullPath, None, None, None), self)
            self.addChild(item)
            return item

        return None

    def childs(self):
        """Return list of children"""
        # need to return a clone?
        return self.__childs

    def child(self, row):
        """Return child at given position"""
        if row<0 or row>=len(self.__childs):
            return None
        return self.__childs[row]

    def addChild(self, childNode):
        """Add a new child"""
        if not isinstance(childNode, BSLangageReferenceNode):
            raise EInvalidType("Given `childNode` must be a <BSLangageReferenceNode>")

        self.__childs.append(childNode)

    def childCount(self):
        """Return number of children the current node have"""
        return len(self.__childs)

    def row(self):
        """Return position is parent's children list"""
        returned=0
        if self.__parent:
            returned=self.__parent.childRow(self)
            if returned<0:
                # need to check if -1 can be used
                returned=0
        return returned

    def childRow(self, node):
        """Return row number for given node

        If node is not found, return -1
        """
        try:
            return self.__childs.index(node)
        except:
            return -1

    def columnCount(self):
        """Return number of column for item"""
        return 1

    def data(self, key=None):
        """Return data for node

        Content is managed from model
        """
        if not key is None:
            if key in (BSLangageReferenceNode.PATH,
                       BSLangageReferenceNode.VALUE,
                       BSLangageReferenceNode.CHAR,
                       BSLangageReferenceNode.STYLE
                    ):
                return self.__data[key]
            else:
                return None
        else:
            return self.__data

    def parent(self):
        """Return current parent"""
        return self.__parent

    def setData(self, value):
        """Set node data

        Warning: there's not control about data!!
        """
        self.__data=(self.__data[0], value)



class BSLangageReferenceModel(QAbstractItemModel):
    """A model to display key/value with tree"""

    DEFAULT_RENDER = Qt.UserRole + 1
    VALUE = Qt.UserRole + 2
    STYLE = Qt.UserRole + 3
    CHAR = Qt.UserRole + 4

    def __init__(self, parent=None):
        """Initialise data model"""
        super(BSLangageReferenceModel, self).__init__(parent)

        self.__rootItem=BSLangageReferenceNode()

    def columnCount(self, parent=QModelIndex()):
        """Return total number of column for index"""
        return 1

    def rowCount(self, parent=QModelIndex()):
        """Return total number of rows for index"""
        if parent.column()>0:
            return 0

        if not parent.isValid():
            parentItem=self.__rootItem
        else:
            parentItem=parent.internalPointer()

        return parentItem.childCount()

    def data(self, index, role=Qt.DisplayRole):
        """Return data for index+role"""
        if not index.isValid():
            return None

        item=index.internalPointer()

        if role in (Qt.DisplayRole, BSLangageReferenceModel.VALUE):
            value=item.data(BSLangageReferenceNode.VALUE)
            if value is None:
                value=item.data(BSLangageReferenceNode.PATH)
            return value
        elif role==BSLangageReferenceModel.CHAR:
            return item.data(BSLangageReferenceNode.CHAR)
        elif role==BSLangageReferenceModel.STYLE:
            return item.data(BSLangageReferenceNode.STYLE)
        elif role==BSLangageReferenceModel.DEFAULT_RENDER:
            return item.data(BSLangageReferenceNode.VALUE) is None

        return None

    def index(self, row, column, parent=None):
        """Provide indexes for views and delegates to use when accessing data

        If an invalid model index is specified as the parent, it is up to the model to return an index that corresponds to a top-level item in the model.
        """
        if not isinstance(parent, QModelIndex) or not self.hasIndex(row, column, parent):
            return QModelIndex()

        child=None
        if not parent.isValid():
            parentNode = self.__rootItem
        else:
            parentNode = parent.internalPointer()

        child = parentNode.child(row)

        if child:
            return self.createIndex(row, column, child)
        else:
            return QModelIndex()

    def parent(self, index):
        """return parent (QModelIndex) for given index"""
        if not index or not index.isValid():
            return QModelIndex()

        childItem=index.internalPointer()
        childParent=childItem.parent()

        if childParent is None or childParent==self.__rootItem:
            return QModelIndex()

        return self.createIndex(childParent.row(), 0, childParent)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        """Return label for given data section"""
        return None

    def setData(self, dataList):
        """Add data to model

        If `treePath` contains "/", then a tree is built
            {"a/b/c": 'value'}
            => a
               +- b
                  +- c
                     +- value
        """
        if len(dataList)>0:
            self.__rootItem=BSLangageReferenceNode(dataList)
        else:
            self.__rootItem=BSLangageReferenceNode()
        self.modelReset.emit()



class BSLangageReferenceView(QTreeView):
    """A treeview to visualize language reference"""


    def __init__(self, parent=None):
        super(BSLangageReferenceView, self).__init__(parent)

        self.__model=BSLangageReferenceModel(self)

        self.setModel(self.__model)

        header = self.header()
        header.setStretchLastSection(True)
        self.setHeaderHidden(True)
        self.setItemDelegate(BSLangageReferenceStyle(self))

    def setData(self, data, expandAll=True):
        """Set data for treeview"""

        self.__model.setData(data)
        if expandAll:
            self.expandAll()

    def selectionChanged(self, selected, deselected):
        """ """



class BSLangageReferenceStyle(QStyledItemDelegate):
    """Extend QStyledItemDelegate class to build improved view for which language
    syntax use theme colors
    """
    def __init__(self, parent=None):
        """Constructor, nothingspecial"""
        super(BSLangageReferenceStyle, self).__init__(parent)

    def paint(self, painter, option, index):
        """Paint list item:
        - type ('F'=flow, 'a'=action, 'v'=variable...)
        - value, using editor's style

        ==> globaly same code than WCECompleterView from wcodeeditor
        """
        self.initStyleOption(option, index)

        if index.data(BSLangageReferenceModel.DEFAULT_RENDER):
            # in this case let default rendering
            super(BSLangageReferenceStyle, self).paint(painter, option, index)
            return

        # retrieve style from token
        style = index.data(BSLangageReferenceModel.STYLE)

        # memorize curent state
        painter.save()
        currentFontName="DejaVu Sans Mono [Qt Embedded]"
        currentFontSize=painter.font().pointSizeF()
        color = style.foreground().color()

        if (option.state & QStyle.State_Selected) == QStyle.State_Selected:
            selectRect=QRect(option.rect)
            selectRect.setX(0)
            #rect = QRect(option.rect.left() + 2 * option.rect.height(), option.rect.top(), option.rect.width(), option.rect.height())
            painter.fillRect(selectRect, option.palette.color(QPalette.AlternateBase))

        # -- completion type
        rect = QRect(option.rect.left(), option.rect.top(), 2 * option.rect.height(), option.rect.height())
        if (option.state & QStyle.State_Selected) == QStyle.State_Selected:
            painter.fillRect(rect, QBrush(color.darker(200)))
        else:
            painter.fillRect(rect, QBrush(color.darker(300)))
        font = style.font()
        font.setFamily("DejaVu Sans [Qt Embedded]")
        font.setBold(True)
        font.setPointSizeF(currentFontSize * 0.65)

        painter.setFont(font)
        painter.setPen(QPen(color.lighter(300)))

        painter.drawText(rect, Qt.AlignHCenter|Qt.AlignVCenter, index.data(BSLangageReferenceModel.CHAR))

        # -- completion value
        font = style.font()
        font.setFamily(currentFontName)
        font.setPointSizeF(currentFontSize)


        painter.setFont(font)
        painter.setPen(QPen(color))

        lPosition=option.rect.left() + 2 *  option.rect.height() + 5

        texts=index.data(BSLangageReferenceModel.VALUE).split('\x01')
        for index, text in enumerate(texts):
            if index%2==1:
                # odd text ("optionnal" information) are written smaller, with darker color
                drawingFont=QFont(font)
                drawingFont.setBold(False)
                drawingFont.setItalic(True)
                drawingFont.setPointSizeF(font.pointSizeF()*0.85)
                painter.setOpacity(0.7)
            else:
                drawingFont=font
                painter.setOpacity(1)

            painter.setFont(drawingFont)
            fontMetrics=QFontMetrics(drawingFont)

            rect = QRect(lPosition, option.rect.top(), option.rect.width(), option.rect.height())
            painter.drawText(rect, Qt.AlignLeft|Qt.AlignVCenter, text)

            if text[-1]==' ':
                lPosition+=fontMetrics.boundingRect(text[0:-1]+'_').width()
            else:
                lPosition+=fontMetrics.boundingRect(text).width()

        painter.restore()

    def sizeHint(self, option, index):
        """Caclulate size for rendered completion item"""
        size = super(BSLangageReferenceStyle, self).sizeHint(option, index)
        size.setWidth(size.width() + 2 * size.height() + 5)
        return size
