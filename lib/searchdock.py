
__license__   = 'GPL v3'
__copyright__ = '2023, Steven Dick <kg4ydw@gmail.com>'

# handle search results and bookmarks

from functools import partial

from PyQt5.Qt import Qt, pyqtSignal
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtGui import QTextCursor, QColor
from PyQt5.QtWidgets import QDockWidget, QTextEdit, QMenu

from lib.searchdock_ui import Ui_searchDock
from lib.datamodels import itemListModel
        
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
            cursor.setPosition(anchor, QTextCursor.MoveAnchor)
            cursor.setPosition(pos, QTextCursor.KeepAnchor)
        if not context or cursor.atBlockStart():
            self.pretext = ''
        else:
            c = QTextCursor(cursor)
            c.setPosition(anchor, QTextCursor.KeepAnchor)
            c.movePosition(QTextCursor.PreviousCharacter,QTextCursor.KeepAnchor , contextChars)
            if self.line!=c.blockNumber(): # fell off, start over
                #c = QTextCursor(cursor)
                c.setPosition(anchor, QTextCursor.KeepAnchor)
                c.movePosition(QTextCursor.StartOfBlock, QTextCursor.KeepAnchor, 1)
            self.pretext = c.selectedText()
        if not context or cursor.atBlockEnd():
            self.posttext = ''
        else:
            c = QTextCursor(cursor)
            c.clearSelection()
            c.movePosition(QTextCursor.NextCharacter, QTextCursor.KeepAnchor, contextChars)
            if self.line!=c.blockNumber(): # fell off, start over
                c.setPosition(pos, QTextCursor.KeepAnchor)
                #c = QTextCursor(cursor)
                c.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor, 1)
            self.posttext = c.selectedText()

class selList(itemListModel):
    def __init__(self):
        super().__init__(['pre','item','post'])

    def setSel(self, extraSelections):
        self.removeRows(0, len(self.data),None) # XX always purge?
        for sel in extraSelections:
            self.appendItem(selItem(sel.cursor))

    def headerData(self, col, orientation, role):
        if role==Qt.DisplayRole and orientation==Qt.Vertical and col<len(self.data):
            return str(self.data[col].line+1)
        else:
            return super().headerData(col, orientation, role)

    def data(self, index, role):
        if role==Qt.TextAlignmentRole: # too bad can't set elide style too
            col = index.column()
            if col==0: return Qt.AlignRight
            elif col==1: return Qt.AlignCenter
            elif col==2: return Qt.AlignLeft
        item = self.getItem(index)
        if not item or role not in (Qt.DisplayRole, Qt.EditRole): return None
        col = index.column()
        if col==0: return item.pretext
        elif col==1: return item.text
        elif col==2: return item.posttext
        else: return None
    
class searchDock(QDockWidget):
    showSel = pyqtSignal(list)
    hideSel = pyqtSignal(list)
    gotoSel = pyqtSignal(QTextCursor)
    
    def __init__(self, parent):
        super().__init__(parent)
        self.ui = Ui_searchDock()
        self.ui.setupUi(self)
        self.ui.tableView.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)

        # XX (later) check parent for existing docks, and add this as a tab
        parent.addDockWidget(Qt.LeftDockWidgetArea, self)
        
        self.color = QtGui.QBrush(Qt.cyan) # XXX
        self.model = selList()
        self.ui.tableView.setModel(self.model)

        self.ui.showButton.clicked.connect(partial(self.emitExtraSelections, self.showSel))
        self.ui.hideButton.clicked.connect(partial(self.emitExtraSelections, self.hideSel))
        self.ui.tableView.clicked.connect(self.gotoIndex)

    def gotoIndex(self, index):
        item = self.model.getItem(index)
        if item:
            self.gotoSel.emit(item.cursor)

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
        self.emitExtraSelections(self.showSel)
        
    def contextMenuEvent(self, event):
        m = QMenu()
        # XX make this a submenu instead?
        # XX colorNames gives too many colors.
        # Filter by dark/light mode? with a more option??
        for c in QtGui.QColor.colorNames():
            m.addAction(c, partial(self.setColor, c))
        m.exec(event.globalPos())
        
    
