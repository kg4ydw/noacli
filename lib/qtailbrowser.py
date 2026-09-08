
__license__   = 'GPL v3'
__copyright__ = '2022, 2023, 2026 Steven Dick <kg4ydw@gmail.com>'

# viewer portion of the qtail application

import re
from functools import partial

from PyQt6.QtCore import pyqtSignal, QPoint
from PyQt6 import QtCore
from PyQt6.QtWidgets import QTextBrowser, QFontDialog, QMenu
from PyQt6.QtGui import QTextCursor


class myBrowser(QTextBrowser):
    # context menu actions
    saveHighlight = pyqtSignal()
    clearHighlights = pyqtSignal()
    findPreviousHilights = pyqtSignal(QPoint)
    suggest_command = pyqtSignal(str, bool) # cmd, immediate

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
        # XXX only if there are highlights?
        m.addAction("Clear highlights", self.clearHighlights.emit)
        # XXX only if there are search results visible?
        m.addAction("Find in search results", lambda: self.findPreviousHilights.emit(event.pos()))
        if self.ui.followCheck.isChecked():
            m.addAction("stop following tail",self.contextFollowToggle)
        else:
            m.addAction("Follow tail",self.contextFollowToggle)
        if self.showBars:
            m.addAction("Hide bars",self.toggleBars)
        else:
            m.addAction("Show bars",self.toggleBars)
        # converting html to html is probably not good
        # but reload might make this necsesary so always offer it anyway
        m.addAction("View as html", self.makeHtml)
        m.addAction("View as markdown", self.makeMarkdown)
        ss = self.contextSearches(event.pos(), m)
        if ss:
            m.addMenu(ss)
        m.exec(event.globalPos())

    def contextSearches(self,pos,parent):
        #p = self.parent()
        #if p.receivers(p.suggest_command) <=0 : return None
        context = [None, False, False, False] # fill in as needed
        menu = QMenu("found commands",parent)
        for cs in filter(lambda s: s.ccontext and s.ctemplate, self.savedsearches):
        #self.savedsearches:
            # print(f"testing context {cs.name} {cs.ccontext} {len(cs.ctemplate)}")  # DEBUG
            if context[cs.ccontext] is False:
                match cs.ccontext: # fill in contexts as needed only
                    case 1: # selection
                        context[1] = self.textCursor().selectedText()
                        #print(f"found selection {len(context[1])}") # DEBUG
                        # XXX what if there's none?
                    case 2: # line
                        context[2] = self.cursorForPosition(pos).block().text()
                    case 3: # word
                        cursor = self.cursorForPosition(pos)
                        cursor.movePosition(QTextCursor.MoveOperation.StartOfWord)
                        cursor.movePosition(QTextCursor.MoveOperation.NextWord, QTextCursor.MoveMode.KeepAnchor)
                        context[3] = cursor.selectedText()
                        # print(f"found word {len(context[3])}") DEBUG
            if context[cs.ccontext]:
                regex = re.compile(cs.sexp)
                for rmatch  in regex.finditer(context[cs.ccontext]):
                    try:
                        text = cs.ctemplate.format(rmatch.group(0), *rmatch.groups())
                    except:
                        text = False
                    if text:
                        menu.addAction(text, partial(self.suggest_command.emit, text, cs.runImmediate))
        return None if menu.isEmpty() else menu

    def makeHtml(self):
        self.setHtml(self.document().toRawText())

    def makeMarkdown(self):
        self.setMarkdown(self.document().toRawText())

    def contextFollowToggle(self):
        self.ui.followCheck.setChecked(not self.ui.followCheck.isChecked())
        ## checkbox action calls this anyway
        # self.jumpToEndMaybe(self.ui.followCheck.isChecked())

    def toggleBars(self):
        # this should use self.ui.actionShowToolbar but it didn't work
        t= self.ui.actionShowToolbar
        # XX this doesn't work ## showBars = t.isChecked()
        self.showBars = not self.showBars
        showBars = self.showBars  # proxy for above
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
        width = max(len(x) for x in atable)
        for row in atable:
            if len(row)<width: row +=['']*(width-len(row))
        cursor = self.textCursor()
        t = cursor.insertTable(len(atable), len(atable[0]))
        # note: must let table be built before starting block to fill it
        cursor.beginEditBlock()

        for arow in atable:
            for cell in arow:
                cursor.insertText(cell)
                cursor.movePosition(QTextCursor.MoveOperation.NextCell)
        cursor.endEditBlock()

    @QtCore.pyqtSlot(bool)
    def jumpToEndMaybe(self,checked):
        if not checked: return
        c=self.textCursor()
        c.movePosition(QTextCursor.MoveOperation.End)
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
    #    opts =  ( QFontDialog.FontDialogOption.MonospacedFonts, )
    #    (font, ok)  = QFontDialog.getFont(self.document().defaultFont(), None, "Select editor font", *opts)
    #    if ok:
    #        self.document().setDefaultFont(font)
    #    print(font) # DEBUG
