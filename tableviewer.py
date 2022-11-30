#!/usr/bin/env python3

import sys
import os
import io
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtGui import QTextCursor
from PyQt5.QtWidgets import QTextEdit, QSizePolicy, QMenu
from PyQt5.QtCore import QCommandLineParser, QCommandLineOption, QIODevice, QSocketNotifier, QSize, QModelIndex, QItemSelectionModel, QProcess
from PyQt5.Qt import Qt, pyqtSignal
from functools import partial
from math import ceil, floor
import csv
import re
from statistics import stdev, mean, median

from tableviewer_ui import Ui_TableViewer

from datamodels import simpleTable

from typedqsettings import typedQSettings

typedQSettings().registerOptions({
    'TableviewerResizeRows': [ False, 'Resize rows automatically after data is read', bool],
    'TableviewerResizeRatio': [ 1.5, 'Max ratio of current size to larger size for automatic window resize if larger', float],
    'TableviewerPickerCols': [10,'Threshold of columns in table, over which the column picker is displayed by default', int],

    })

## ideas to implement and/or document
# context menu
#  refactor columns
# filter/search rows by column
# sort / reset sort
# resize column on double click header
# copy cell to clipboard on click
# copy cell to both clipboards on double click
# select column as vertical header

# I/O here is messy because Qt needs non-blocking I/O but the Qt file types
# don't handle the python I/O interface csv expects and the python I/O libs
# don't handle non-blocking I/O properly.  I wanted to use either input
# stream (so we can use stdin or QProcess).  With use of peek() this code
# doesn't call something that would block waiting for more data.


################
# Both python and Qt file I/O are missing important features.
# Try to cover this up with two classes that merge features.

# Monkeypatching both QProcess and BufferedReader because neither class
# provided a good way to subclass and init with an existing object.

# monkey patch functor into old only if it isn't already there.
# Don't step on the real one if they actually implement it later.
import types

# can't monkeypatch QProcess, so wrapping it instead
class betterQProcess():
    '''This pretends a QIODevice is a BufferedReader by implementing the
        bare minimum needed here.  Note that both types include all
        the same functionality, but with different function names and
        return types.
    '''
    def __init__(self, qio):
        self.qio = qio
    def strpeek(self, size):
        return str(self.qio.peek(size),'utf-8')
    def __iter__(self):
        return self
    def __next__(self):
        return str(self.qio.readLine(), 'utf-8')
    ## try to dynamicaly patch in anything else
    def __getattr__(self, name):
        f=getattr(self.qio,name) # next time get it direct
        setattr(self,name,f)
        return f

        
## missing stuff from TextIOWrapper
class betterTextIOWrapper():
    def __init__(self, tiow):
        self.tiow = tiow
    def strpeek(self, size):  # XX not gonna fake size default
        return self.tiow.buffer.peek(size).decode('utf-8')
    def canReadLine(self):
        return '\n' in self.strpeek(1024)
    
    def __iter__(self): return self.tiow.__iter__()
    def __next__(self): return self.tiow.__next__()
    def __getattr__(self, name):
        f=getattr(self.tiow, name) # next time get it direct
        setattr(self, name, f)
        return f

## and csv could have done this...
class FixedWidthParser():
    def __init__(self, f):
        # optimistically do this without peek for now
        # XX this doesn't handle right justified or centered columns
        # which might be fixable with peek
        
        #self.lines = iter(f)
        #s = next(self.lines)
        #self.s = s = s.expandtabs()

        peek = f.strpeek(1024)
        lines = peek.splitlines()  # XXX should use this better
        s = lines[0]
        
        col = [0]
        i=0
        while i>=0:
            i=s.find('  ',i)
            if i>=0: # find end of column
                i+=2
                while i<len(s) and s[i]==' ':
                    i+=1
                if i<len(s):
                    col.append(i-1) # back up one, put border in the column
        self.col = col
        self.lines = iter(f)
        print("col = "+(" ".join([str(i) for i in col]))) # DEBUG
    
    def __len__(self):
        return len(self.col)
    def __iter__(self):
        while True:
            try:
                s = next(self.lines)
                if s!=None:
                    s=s.expandtabs()
                else:
                    yield None  # not end of file
                    continue
            except StopIteration:
                if typedQSettings().value('Debug',False): print('fixed got stop') # DEBUG
                return
            yield [ s[self.col[i]:self.col[i+1]-1] for i in range(len(self.col)-1) ] + [  s[self.col[-1]:].strip() ]

        
class TableViewer(QtWidgets.QMainWindow):
    window_close_signal = pyqtSignal()
    want_resize = pyqtSignal()
    want_readmore = pyqtSignal(str)
    def __init__(self, options=None, parent=None):
        super().__init__()
        self.data = []
        self.hasmore = True
        self.firstread = True
        self.useheader = True
        # XXX icon
        # connect to my own event so I can send myself a delayed signal
        self.want_resize.connect(self.actionAdjust, Qt.QueuedConnection) # XXX or adjustAll ?? OPTION
        self.ui = Ui_TableViewer()
        self.ui.setupUi(self)
        self.ui.menuView.addAction(self.ui.colPickerDock.toggleViewAction())
        self.ui.colPicker.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.colPicker.customContextMenuRequested.connect(self.colPickerContext)
        hh = self.ui.tableView.horizontalHeader()
        hh.setSectionsMovable(True)
        hh.sectionDoubleClicked.connect(self.resizeHheader)
        self.ui.tableView.verticalHeader().sectionDoubleClicked.connect(self.resizeVheader)
        self.want_readmore.connect(self.readmore, Qt.QueuedConnection)  # for delayed reads
        
        # set model after opening file

    def start(self):
        # probably should do more here and less in open 
        pass

    ################ GUI stuff
    
    def actionAdjustAll(self):
        self.actionAdjust()
        self.resizeWindowToTable(False)  # XX premature?

    def actionAdjust(self):
        view = self.ui.tableView
        view.resizeColumnsToContents()
        if typedQSettings().value('TableviewerResizeRows',False):
            self.ui.tableView.resizeRowsToContents()
        self.resizeWindowToTable(True)
        ##view.adjustSize()  # does stupid stuff
        self.ui.colPicker.adjustSize() # does stupid stuff
        #self.ui.colPickerDock.adjustSize() # ignored
        mysize = self.size()
        viewsize = view.size()
        frame = mysize-viewsize  # XXX probably wrong

    def showRowNumbers(self, checked):
        self.ui.tableView.verticalHeader().setVisible(checked)

    def showHeadings(self, checked):
        self.ui.tableView.horizontalHeader().setVisible(checked)

    def numberHeadings(self, checked):
        if checked:
            self.model.headers = [str(col+1) for col in range(len(self.model.headers))]
        else: # recopy first row
            self.model.headers = self.model.mydata[0]
        self.model.headerDataChanged.emit(Qt.Horizontal, 0, len(self.model.headers))

    def squeezeColumns(self):
        # measure the width of every column and set the width to mean+2*stdev
        # XXX ignore hidden columns head.isSectionHidden head.{logical,visual}Index
        
        head = self.ui.tableView.horizontalHeader()
        shown = list([ i for i in range(len(self.headers)) if not head.isSectionHidden(i) ])
        widths = [ head.sectionSize(i) for i in shown]
        width = self.ui.tableView.width()-50
        m = min(median(widths),mean(widths))
        s = stdev(widths)
        target = ceil(m+s)
        wmin = [ widths[i] for i in range(len(widths)) if widths[i]<target]
        tmin = sum(wmin)
        nwide = len(widths)-len(wmin)
        tavg = tmin + m*nwide
        tmid = tmin + target*nwide
        tmax = sum(widths)
        extra = (width-tmin)/nwide # distribute what is left over
        #print("squeeze: m={} sd={} w={} tmin={} mid={} max={} e={}".format(m,s,width, tmin, tmid, tmax, extra)) # DEBUG
        if tmax<width: return  # doesn't need to be squeezed
        if tmid>width:  # restrict to std
            extra = 0
        else:
            extra=floor(extra)
        # print(" final e={} target={}".format(extra, target)) # DEBUG squeeze
        for i in range(len(widths)):
            if widths[i]> target+extra:
                head.resizeSection(shown[i],target+extra)
            #elif width[i]>target:
            #    head.resizeSection(i,target)

    def resizeWindowToTable(self, useratio=False):
        oldsize = self.size()
        ratio = typedQSettings().value('TableviewerResizeRatio', 2)
        frame = oldsize - self.ui.tableView.size() 
        vh = self.ui.tableView.verticalHeader()
        hh = self.ui.tableView.horizontalHeader()
        size = QtCore.QSize(hh.length(), vh.length())
        size += QtCore.QSize(vh.size().width(), hh.size().height())
        size += frame + QtCore.QSize(30, 100)
        # check V and H separately
        if useratio:
            if oldsize.height()*ratio < size.height():
                size.setHeight(oldsize.height())
            if oldsize.width()*ratio < size.width():
                size.setWidth(oldsize.width())
        self.resize(size)

    def tableSelectFix(self):
        sm = self.ui.tableView.selectionModel()
        if not sm:
            print("No seleciton model") # EXCEPT
            return
        sm.selectionChanged.connect(self.tableSelect)

    def closeEvent(self,event):
        self.window_close_signal.emit()
        super().closeEvent(event)

    def copyClip1(self, index):
        text = index.data(Qt.DisplayRole)
        #print("Copy1 "+text) # DEBUG
        if type(text)!=str:
            text = str(text)
        self.app.clipboard().setText(text)

    def copyClip2(self, index):
        text = index.data(Qt.DisplayRole)
        #print("Copy2 "+text) # DEBUG
        if type(text)!=str:
            text = str(text)
        self.app.clipboard().setText(text)
        self.app.clipboard().setText(text, QtGui.QClipboard.Selection)
            
    def resizeHheader(self, logical):
        self.ui.tableView.resizeColumnToContents(logical)
    def resizeVheader(self, logical):
        self.ui.tableView.resizeRowToContents(logical)

    def contextMenuEvent(self, event):
        m=QMenu()
        m.addAction('Merge two adjacent selected cells', self.collapseSelectedCells)
        # XXX more tableviewer context items??
        action = m.exec_(event.globalPos())

    # context menu triggered
    def collapseSelectedCells(self):
        sm = self.ui.tableView.selectionModel()
        slist = sm.selectedIndexes()
        # and clear the selection now that we've got the cell list.
        # This gives feedback in case the user tried to do something wierd.
        sm.clear()
        # XX this is pretty primitive, only supports merging two cells
        # XXX and it gives no error messages if things go wrong
        if len(slist)!=2: return
        if slist[0].row()!=slist[1].row(): return
        a = slist[0].column()
        b = slist[1].column()
        if a>b: (a,b)=(b,a)
        if a+1!=b: return
        self.model.mergeCells(self.model.index(slist[0].row(),a))
                              
    ################ table parsing stuff

    def openfile(self,filename):
        self.setWindowTitle(filename)
        self.csvfile =  betterTextIOWrapper(open(filename))  # XXX need better exception handling
        self.openfd(self.csvfile)

    def openProcess(self, title, process):
        self.process = process
        self.csvfile = betterQProcess(process)
        if title:
            self.setWindowTitle(title)
        else:
            self.setWindowTitle('tableviewer window') # SETTING
        process.readyRead.connect(partial(self.readmore,'readyread'))
        #XX let this autotrigger ## self.openfd(self.csvfile)
        #XX Note that QProcess might not even be open yet
        # self.rebutton('kill', self.terminateProcess) XXX
        # self.file.finished.connect(self.procFinished) ###
        
    def openstdin(self):
        os.set_blocking(sys.stdin.fileno(),False)
        self.csvfile = betterTextIOWrapper(sys.stdin)
        self.notifier = QSocketNotifier(sys.stdin.fileno(),QSocketNotifier.Read, self)
        # set up notifier for incoming data
        self.notifier.activated.connect(partial(self.readmore,'socket'))
        self.openfd(sys.stdin)
        self.setWindowTitle('table stdin')

    def openfd(self, csvfile):
        DEBUG = typedQSettings().value('DEBUG',False)
        maxx=0
        # handle either a QProcess io.TextIOWrapper as long as they
        # are properly monkeypatched
        if not csvfile.canReadLine():  # try again later
            return
        peek = csvfile.strpeek(1024)
        if not peek:  # must be on a pipe, try again later
            return 
        # self.firstread = False  # got something, initialize! but in case anything goes wrong, set this later
        if '\t ' in peek or ' \t' in peek:  # maybe 3 spaces too?
            if DEBUG: print("Found tabs and spaces, trying fixed width parser") # DEBUG
            self.parser = FixedWidthParser(csvfile)
            self.csvreader = iter(self.parser)
        else:
            # give csv a try and then we try again
            try:
                dialect = csv.Sniffer().sniff(peek, delimiters='\t,|:')
                self.csvreader = csv.reader(csvfile, dialect)
                if DEBUG: print('got csv') # DEBUG
            except csv.Error:
                self.parser = FixedWidthParser(csvfile) # XX could use peek
                # XX so what if it's a one column table?  better than raising.
                #if len(self.parser)<2:
                #    print('No delimiter found, I give up!'+str(len(self.parser))) # EXCEPT
                #    return
                self.csvreader = iter(self.parser)
                if DEBUG: print("csv failed, using FixedWidthParser")
                self.firstread=False
        # just read a few chunks to get us started
        lines = 3
        while self.csvfile.canReadLine() and lines>0:
            # be brave without a try
                row = self.csvreader.__next__()
                # XXX if not row: what??
                self.data.append(row)
                x = len(row)
                if x>maxx: maxx=x
                lines -= 1
        if lines<0 and self.csvfile.canReadLine():
            self.want_readmore.emit('initial') # get more without waiting
        headers = self.data[0] # XXX copy or steal first row as headers
        try:
            # optionally hide column picker for small tables
            if maxx < typedQSettings().value('TableviewerPickerCols', 10):
                self.ui.colPickerDock.setVisible(False)
        except:
            pass
        self.headers = headers  # too many copies of this? confusing.
        self.model = simpleTable(self.data, headers)
        self.model.checkExtendHeaders(maxx)
        self.ui.tableView.setModel(self.model)
        self.headermodel = QtCore.QStringListModel(headers, self)
        self.ui.colPicker.setModel(self.headermodel)
        self.tableSelectFix()
        self.want_resize.emit()
        self.firstread = False

    def readmore(self,fromwhere):
        DEBUG = typedQSettings().value('DEBUG',False)
        if not self.csvfile.canReadLine():
            # why did you bother us, you're not ready yet
            return
        if self.firstread:  # didn't have any data at start, try again now
            #if DEBUG: print('first read') # DEBUG
            self.openfd(self.csvfile)
        rows = []
        if DEBUG: print('readmore '+fromwhere)  # DEBUG
        row=None
        # don't read too many lines at once (prevent lockup from large data)
        lines = int(typedQSettings().value('LogBatchLines',100))
        while lines>0 and self.csvfile.canReadLine():
            row = next(self.csvreader)
            if row: rows.append(row)
            lines -= 1
        if lines<=0:
            self.want_readmore.emit('more more') # get more on next pass
        if rows:
            if DEBUG: print("Read {} rows".format(len(rows))) # DEBUG
            self.model.insertRowsAt(1,rows)
            # update headers if any row is longer XXX


    def hideCols(self):
        indexes = self.ui.colPicker.selectedIndexes()
        for i in indexes:
            self.ui.tableView.setColumnHidden(i.row(),True)
        self.ui.colPicker.selectionModel().clear()
    def showCols(self):
        indexes = self.ui.colPicker.selectedIndexes()
        for i in indexes:
            self.ui.tableView.setColumnHidden(i.row(),False)
        self.ui.colPicker.selectionModel().clear()

    def tableSelect(self, selected, deselected):
        # XXX ignore what is passed to us and reask for selection
        indexes = self.ui.tableView.selectionModel().selectedColumns()
        if not indexes: return
        selection = QtCore.QItemSelection()
        view = self.ui.colPicker.model()
        for i in indexes:
            ii = view.index(i.column(),0)
            selection.select(ii,ii)
        self.ui.colPicker.selectionModel().select(selection, QItemSelectionModel.Select)

    def colPickerContext(self, point):
        m = QMenu()
        pick = self.ui.colPicker
        m.addAction("Clear selection",pick.selectionModel().clear)
        m.addAction("Select shown columns",self.pickShown)
        m.addAction("Select hidden columns",self.pickHidden)
        m.addAction("Set shown columns", self.setShown)
        m.addAction("Export selected to clipboard", partial(self.exportCol,' '))
        m.addAction("Export selected to clipboard (csv)", partial(self.exportCol,','))
        action = m.exec_(self.ui.colPicker.mapToGlobal(point))

    def pickShown(self):
        self.pickShowCol(False)
    def pickHidden(self):
        self.pickShowCol(True)
    def setShown(self):
        view = self.ui.tableView
        pickselmodel = self.ui.colPicker.selectionModel()
        pickmodel = self.ui.colPicker.model()
        for i in range(len(self.headers)):
            view.setColumnHidden(i, not pickselmodel.isSelected(pickmodel.index(i,0)))
    def exportCol(self, delimiter):
        indexes = self.ui.colPicker.selectedIndexes()
        headers = [self.headers[index.row()] for index in indexes]
        text = delimiter.join(headers)
        self.app.clipboard().setText(text)
        self.app.clipboard().setText(text, QtGui.QClipboard.Selection)
                                              
    def pickShowCol(self, wanthid):
        view = self.ui.tableView
        viewmodel = view.model()
        pick = self.ui.colPicker
        pickmodel = pick.model()
        sel = pick.selectionModel()
        sel.clear()
        selection = QtCore.QItemSelection()
        for i in range(len(self.headers)):
            if wanthid==view.isColumnHidden(i):
                ii = pickmodel.index(i,0)
                selection.select(ii,ii)
        self.ui.colPicker.selectionModel().select(selection, QItemSelectionModel.Select)

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    # display
    QtCore.QCoreApplication.setOrganizationName("kg4ydw");
    QtCore.QCoreApplication.setApplicationName("TableViewer");

    #options = myOptions()
    #args = options.process(app)

    mainwin = TableViewer()
    mainwin.app = app
    #if options.title: mainwin.setWindowTitle(options.title)
    
    w = mainwin.ui

    mainwin.show()
    #mainwin.start()

    #if options.isCommand:
    #    # save command for later reuse
    #    # open pipe
    #    # resize window with adjust() if command exits 
    #    pass
    #elif args and args[0]!='-':
    #    # XXX handle multiple files later
    #    mainwin.openfile(args[0])
    #else:
    #    mainwin.openstdin()

    args = sys.argv
    if args and len(args)>1 and args[1]!='-':
        # XXX handle multiple files later
        mainwin.openfile(args[1])
    else:
        mainwin.openstdin()
    
    app.exec_()
