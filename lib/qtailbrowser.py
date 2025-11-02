
__license__   = 'GPL v3'
__copyright__ = '2022, 2023 Steven Dick <kg4ydw@gmail.com>'

# viewer portion of the qtail application

import re
from functools import partial

from PyQt5.Qt import pyqtSignal
from PyQt5 import QtCore
from PyQt5.QtWidgets import QTextBrowser, QFontDialog
from PyQt5.QtGui import QTextCursor

class myBrowser(QTextBrowser):
    # context menu actions
    saveHighlight = pyqtSignal()
    clearHighlights = pyqtSignal()
    
    def __init__(self, parent):
        super().__init__(parent)
        self.ui = parent.parent().ui
        self.showBars = True
    
    def contextMenuEvent(self, event):
        m=super().createStandardContextMenu(event.pos())
        if self.textCursor().hasSelection():
            m.addAction("Convert selection to table", self.selToTable)
            m.addAction("Save selection as highlight", self.saveHighlight.emit)
        else:
            m.addAction("Convert to table",self.allToTable)
        m.addAction("Clear highlights", self.clearHighlights.emit)
        if self.ui.followCheck.isChecked():
            m.addAction("stop following tail",self.contextFollowToggle)
        else:
            m.addAction("Follow tail",self.contextFollowToggle)
        if self.showBars:
            m.addAction("Hide bars",self.toggleBars)
        else:
            m.addAction("Show bars",self.toggleBars)
        m.exec(event.globalPos())

    def contextFollowToggle(self):
        self.ui.followCheck.setChecked(not self.ui.followCheck.isChecked())
        ## checkbox action calls this anyway
        # self.jumpToEndMaybe(self.ui.followCheck.isChecked())

    def toggleBars(self):
        # this should use self.ui.actionShowToolbar but it didn't work
        t= self.ui.actionShowToolbar
        # XX this doesn't work ## showBars = t.isChecked()
        self.showBars = not self.showBars
        showBars = self.showBars # proxy for above
        self.ui.toolBar_2.setVisible(showBars)
        self.ui.menubar.setVisible(showBars)
        self.ui.statusbar.setVisible(showBars)
        t.setChecked(showBars)

    def selToTable(self):
        cursor = self.textCursor()
        self.toTable(cursor.selectedText())
        pass

    def allToTable(self):
        self.toTable(self.toPlainText())

    def autoTable(self, text):
        # guess what kind of table this is based on the first line
        # This is (intentionally?) primitive, tableviewer does it better
        # XXX export selection to tableviewer instead?
        ds = {}
        for i in re.findall('[\t,|]', text):
            if i in ds: ds[i]+=1
            else: ds[i]=1
        if not ds: return False
        d = max(ds, key=lambda x: ds[x])
        #print('delimiter={} found={}'.format(d,ds[d])) # DEBUG
        return self.csvTable(text,d)

    def csvTable(self, text, delimiter=','):
        table = []
        for line in text.splitlines():
            table.append(line.split(delimiter))
        #if typedQSettings().value('DEBUG',False):print("table: {},{}".format(len(table),len(table[0]))) # DEBUG
        return table
    
    def toTable(self, text):
        # this doesn't handle quoted delimiters correctly in csv, very primitive
        atable = self.autoTable(text)
        if not atable: return  # fail!
        # normalize the table
        width = max([len(x) for x in atable])
        for row in atable:
            if len(row)<width: row +=['']*(width-len(row))
        cursor = self.textCursor()
        t = cursor.insertTable(len(atable), len(atable[0]))
        # note: must let table be built before starting block to fill it
        cursor.beginEditBlock()

        for arow in atable:
            for cell in arow:
                cursor.insertText(cell)
                cursor.movePosition(QTextCursor.NextCell)
        cursor.endEditBlock()
            
    @QtCore.pyqtSlot(bool)
    def jumpToEndMaybe(self,checked):
        if not checked: return
        c=self.textCursor()
        c.movePosition(QTextCursor.End)
        self.setTextCursor(c)

    def liveFont(self,font):
        if font:
            self.document().setDefaultFont(font)

    def doneFont(self):
        self.fontdialog.deleteLater()
        self.fontdialog = None

    def pickFont(self):
        startfont = self.document().defaultFont()
        fd = QFontDialog(startfont, None)
        fd.currentFontChanged.connect(self.liveFont)
        fd.rejected.connect(partial(self.liveFont,startfont) )
        fd.finished.connect(self.doneFont)
        fd.setWindowTitle("Pick qtail browser font")
        self.fontdialog = fd
        fd.open()
    
    ## this doesn't work any differently than the above
    #def pickFontMono(self):
    #    print('mono') # DEBUG
    #    opts =  ( QFontDialog.MonospacedFonts, )
    #    (font, ok)  = QFontDialog.getFont(self.document().defaultFont(), None, "Select editor font", *opts)
    #    if ok:
    #        self.document().setDefaultFont(font)
    #    print(font) # DEBUG
