
__license__   = 'GPL v3'
__copyright__ = '2023, 2026 Steven Dick <kg4ydw@gmail.com>'

# handle search results and bookmarks

from functools import partial

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtGui import QTextCursor, QColor
from PyQt6.QtWidgets import QDockWidget, QTextEdit, QMenu

from lib.searchdock_ui import Ui_searchDock
from lib.datamodels import itemListModel

from lib.colorpicker import ColorPicker

colorpicker = ColorPicker()

class selItem():
    def __init__(self, cursor, context=True):
        # save in case it goes out of context
        self.cursor = cursor
        self.text = cursor.selectedText()
        self.line = cursor.blockNumber()
        # XX get pretext and posttext
        pos = cursor.position()
        anchor = cursor.anchor()
        contextChars = 20 # XXX setting
        if anchor>pos: # swap!!
            (pos,anchor) = (anchor,pos)
            cursor.setPosition(anchor, QTextCursor.MoveMode.MoveAnchor)
            cursor.setPosition(pos, QTextCursor.MoveMode.KeepAnchor)
        if not context or cursor.atBlockStart():
            self.pretext = ''
        else:
            c = QTextCursor(cursor)
            c.setPosition(anchor, QTextCursor.MoveMode.KeepAnchor)
            c.movePosition(QTextCursor.MoveOperation.PreviousCharacter,QTextCursor.MoveMode.KeepAnchor , contextChars)
            if self.line!=c.blockNumber(): # fell off, start over
                #c = QTextCursor(cursor)
                c.setPosition(anchor, QTextCursor.MoveMode.KeepAnchor)
                c.movePosition(QTextCursor.MoveOperation.StartOfBlock, QTextCursor.MoveMode.KeepAnchor, 1)
            self.pretext = c.selectedText()
        if not context or cursor.atBlockEnd():
            self.posttext = ''
        else:
            c = QTextCursor(cursor)
            c.clearSelection()
            c.movePosition(QTextCursor.MoveOperation.NextCharacter, QTextCursor.MoveMode.KeepAnchor, contextChars)
            if self.line!=c.blockNumber(): # fell off, start over
                c.setPosition(pos, QTextCursor.MoveMode.KeepAnchor)
                #c = QTextCursor(cursor)
                c.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor, 1)
            self.posttext = c.selectedText()

class selList(itemListModel):
    def __init__(self):
        super().__init__(['pre','item','post'])
        self.color = None
        self.haspre = self.hasitem = self.haspost = False

    def setSel(self, extraSelections):
        self.removeRows(0, len(self.data),None) # XX always purge?
        # insert rows in batches for better performance
        rows = []
        for sel in extraSelections:
            if sel.cursor.position() or sel.cursor.hasSelection(): # skip stale highlights
                item = selItem(sel.cursor)
                # self.appendItem(item)
                rows.append(item)
                if item.pretext: self.haspre = True
                if item.text: self.hasitem = True
                if item.posttext: self.haspost = True
            #if len(rows)&7==0: # this would make it negligibly faster but more chunky
            QtCore.QCoreApplication.processEvents()
            if len(rows)>=1000: # XXX SETTING
                self.insertRowsAt(1,rows)
                rows=[]
        if rows: # and the leftovers
            self.insertRowsAt(1,rows)

    def headerData(self, col, orientation, role):
        if orientation==Qt.Orientation.Horizontal and col==1 and role==Qt.ItemDataRole.BackgroundRole and self.color:
            return self.color
        if role==Qt.ItemDataRole.DisplayRole and orientation==Qt.Orientation.Vertical and col<len(self.data):
            return str(self.data[col].line+1)
        else:
            return super().headerData(col, orientation, role)

    def setColor(self, c):
        self.color = c
        self.headerDataChanged.emit(Qt.Orientation.Horizontal, 1, 1)

    def data(self, index, role):
        if role==Qt.ItemDataRole.TextAlignmentRole: # too bad can't set elide style too
            col = index.column()
            if col==0: return Qt.AlignRight
            elif col==1: return Qt.AlignCenter
            elif col==2: return Qt.AlignLeft
        item = self.getItem(index)
        if not item or role not in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole): return None
        col = index.column()
        if col==0: return item.pretext
        elif col==1: return item.text
        elif col==2: return item.posttext
        else: return None

class searchDock(QDockWidget):
    showSel = pyqtSignal(list)
    hideSel = pyqtSignal(list)
    gotoSel = pyqtSignal(QTextCursor)

    def __init__(self, parent, title=None, selections=None, searchterm=None, findflags=None):
        super().__init__(parent)
        self.ui = Ui_searchDock()
        self.ui.setupUi(self)
        self.ui.tableView.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self.searchterm = searchterm # XXX use these later
        self.findflags = findflags

        # stuff this in a corner of the parent QMainWindow
        parent.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self)
        # XX alternate: check parent for existing docks, and add this as a tab SETTINGS
        global colorpicker
        color = colorpicker.nextColor()
        self.color = QtGui.QBrush(QColor(color))
        self.model = selList()
        self.ui.tableView.setModel(self.model)
        # set up connections before the data is loaded
        self.ui.showButton.clicked.connect(partial(self.emitExtraSelections, self.showSel))
        self.ui.hideButton.clicked.connect(partial(self.emitExtraSelections, self.hideSel))
        self.ui.tableView.clicked.connect(self.gotoIndex)
        if title:
            self.setWindowTitle(title)
        self.favcol = 1 # item to scroll to (possibly only visible column)
        if selections:
            self.setSel(selections)
            if title and title!='Highlights':
                tv = self.ui.tableView
                # hide empty columns
                if not self.model.haspre: tv.setColumnHidden(0,True)
                if not self.model.hasitem:
                    tv.setColumnHidden(1,True)
                    if self.model.haspre: self.favcol = 0
                    else: self.favcol = 2
                if not self.model.haspost: tv.setColumnHidden(2,True)
        self.model.setColor(self.color)

    def gotoIndex(self, index):
        item = self.model.getItem(index)
        if item:
            self.gotoSel.emit(item.cursor)

    # opposite of gotoIndex
    def findSelection(self, cursor):
        pos = cursor.position()
        for index in self.model:
            ic = self.model.getItem(index).cursor
            c1 = ic.anchor()
            c2 = ic.position()
            if c1>c2:
                (c1,c2) = (c2,c1)
            if c1<=pos and pos<=c2:
                self.ui.tableView.setCurrentIndex(index)
                self.ui.tableView.scrollTo(index.siblingAtColumn(self.favcol))
                return
        # not found

    def setSel(self, extraSelections):
        self.model.setSel(extraSelections)
        self.ui.tableView.resizeColumnsToContents()

    def addSel(self, cursor):
        self.model.appendItem(selItem(cursor))
        self.ui.tableView.resizeColumnsToContents()

    def emitExtraSelections(self, signal):
        es = []
        for i in self.model.data:
            e = QTextEdit.ExtraSelection()
            e.cursor = i.cursor
            e.format.setBackground(self.color)
            es.append(e)
        signal.emit(es)

    def setColor(self, color):
        self.color = QtGui.QBrush(QColor(color))
        self.model.setColor(self.color)
        self.emitExtraSelections(self.showSel)

    def contextMenuEvent(self, event):
        global colorpicker
        color = colorpicker.execColorMenu(event)
        #print(color) # DEBUG
        if color: self.setColor(color)

    def closeEvent(self, event):
        # if a search dock is closed, make visible the menu entry to delete them
        # XXX test if this bug fix is still needed and see if removing it changes functionsality
        p = self.parent()
        if p:
            p.ui.actionDeleteClosedSearches.setVisible(True)
            p.ui.actionDeleteClosedSearches.setEnabled(True)

        # bug workaround for QTBUG-74606 Oct 2021, fixed in Qt 6.11+? buggy in 5.15.3
        if self.isFloating():
            self.setFloating(False)
            self.hide()
            event.ignore()
        else:
            super().closeEvent(event)
