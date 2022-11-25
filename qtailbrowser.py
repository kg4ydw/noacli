from PyQt5 import QtCore
from PyQt5.QtWidgets import QTextBrowser
from PyQt5.QtGui import QTextCursor

import re

class myBrowser(QTextBrowser):
    def __init__(self, parent):
        super().__init__(parent)
    
    def contextMenuEvent(self, event):
        m=super().createStandardContextMenu(event.pos())
        if self.textCursor().hasSelection():
            m.addAction("Convert selection to table", self.selToTable)
        else:
            m.addAction("Convert to table",self.allToTable)
        m.exec_(event.globalPos())

    def selToTable(self):
        cursor = self.textCursor()
        self.toTable(cursor.selectedText())
        pass

    def allToTable(self):
        self.toTable(self.toPlainText())

    def autoTable(self, text):
        # XXX guess for fixed format spaced columns too
        # guess what kind of table this is based on the first line
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
        print("table: {},{}".format(len(table),len(table[0]))) # DEBUG
        return table
    
    def toTable(self, text):
        # XXX this doesn't handle quoted delimiters correctly in csv
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

