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

# context menu
#  refactor columns
# filter/search rows by column
# sort / reset sort
# resize column on double click header
# copy cell to clipboard on click
# copy cell to both clipboards on double click
# select column as vertical header

# signals
#  header.sectionClicked(logical)
#  header.sectionDoubleClocked(logical)
#  

class WaitRead(Exception):
   pass

class fakeBufferedReader():
    ''' This pretends a QIODevice is a BufferedReader
        by implementing the bare minimum needed here.
        Note that both types include all the same functionality, but
        with different return types and names.
    '''
    def __init__(self, qio):
        self.qio = qio
    def peek(self, size):
        return str(self.qio.peek(size),'utf-8')
    def __iter__(self):
        return self
    def __next__(self):
        # maybe this should have used TextStream ?
        if self.qio.canReadLine():
            s= str(self.qio.readLine(), 'utf-8')
            #print('read: '+s) # DEBUG
            return s
        else:
            raise WaitRead
            if self.qio.atEnd() and not self.qio.isOpen() and self.qio.state()==QProcess.NotRunning:
                    if typedQSettings().value('DEBUG',False): print('stop') # DEBUG
                    return None
                    #raise StopIteration
            # print('raise waitread') DEBUG
            raise WaitRead
            return ''
            return None  # can't detect eof here


class FixedWidthParser():
    def __init__(self, f):
        # optimistically do this without peek for now
        # XX this doesn't handle right justified or centered columns
        # which might be fixable with peek
        self.lines = f.__iter__()
        s = next(self.lines)
        self.s = s = s.expandtabs()
        
        col = [0]
        i=0
        while i>=0:
            i=s.find('  ',i)
            if i>=0: # find end of column
                i+=2
                while s[i]==' ':
                    i+=1
                col.append(i-1) # back up one, put border in the column
        self.col = col
        #print("col = "+(" ".join([str(i) for i in col]))) # DEBUG
    
    def __len__(self):
        return len(self.col)
    def __iter__(self):
        while True:
            if self.s and len(self.s): # XXXXXXX
                s = self.s
                self.s = None
            else:
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
        # self.ui.tableView.resizeRowsToContents()  # XXX optional?
        self.resizeWindowToTable()  # XX premature?

    def actionAdjust(self):
        view = self.ui.tableView
        view.resizeColumnsToContents()
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

    def resizeWindowToTable(self):
        oldsize = self.size()
        frame = oldsize - self.ui.tableView.size() 
        vh = self.ui.tableView.verticalHeader()
        hh = self.ui.tableView.horizontalHeader()
        size = QtCore.QSize(hh.length(), vh.length())
        size += QtCore.QSize(vh.size().width(), hh.size().height())
        size += frame + QtCore.QSize(30, 100)
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
        
    ################ table parsing stuff

    def openfile(self,filename):
        self.setWindowTitle(filename)
        with open(filename) as csvfile:
            self.openfd(csvfile)

    def openProcess(self, title, process):
        self.process = process
        if title:
            self.setWindowTitle(title)
        else:
            self.setWindowTitle('tableviewer window') # SETTING
        self.csvfile = fakeBufferedReader(process)
        # QProcess has a peek but not under buffer, so loop this
        #self.csvfile.buffer = self.csvfile
        process.readyRead.connect(partial(self.readmore,'readyread'))
        #XX let this autotrigger ## self.openfd(self.csvfile)
        # self.rebutton('kill', self.terminateProcess) XXX
        # self.file.finished.connect(self.procFinished) ###
        
        
    def openstdin(self):
        # hopefully we at least get the first line with blocking off
        os.set_blocking(sys.stdin.fileno(),False)
        self.csvfile = sys.stdin
        self.notifier = QSocketNotifier(0,QSocketNotifier.Read, self) # XXX 0
        self.notifier.activated.connect(partial(self.readmore,'socket'))
        self.openfd(sys.stdin)
        self.setWindowTitle('table stdin')
        # set up notifier for incoming data

    def openfd(self, csvfile):
        DEBUG = typedQSettings().value('DEBUG',False)
        maxx=0
        # handle either a QProcess.peek or a io.TextIOWrapper.buffer.peek
        # which return different types
        if issubclass(type(csvfile),fakeBufferedReader):
            peek = csvfile.peek(1024)
        else: # python BufferedReader
            peek = csvfile.buffer.peek(1024).decode('utf-8') # XX unportable?
        if not peek:  # must be on a pipe
            # print("No data on first read") # DEBUG
            return
        self.firstread = False
        # print("peek = "+str(len(peek))) # DEBUG
        if '\t ' in peek:
            if DEBUG: print("Found tabs and spaces, trying fixed width parser") # DEBUG
            self.parser = FixedWidthParser(csvfile)
            self.csvreader = iter(self.parser)
        else:
            self.firstread = False
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
        # just read one chunk
        lines = 3
        try:
            for row in self.csvreader:
                if not row or lines<0:
                    print('break')
                    break
                self.data.append(row)
                x = len(row)
                if x>maxx: maxx=x
                lines -= 1
        except WaitRead:
            self.hasmore=False
        if lines<0 and self.hasmore:
            self.want_readmore.emit('initial')  # assume there's more
        # XXX except?
        if not self.data: return # XXX error
        headers = self.data[0] # XXX copy or steal first row as headers
        if len(headers)<maxx: # extend as necessary
            headers += []*(maxx-len(headers))
        # go ahead and normalize all the rows in the data too (might be moot)
        for row in self.data:
            if len(row)<maxx: # extend as necessary
                row += []*(maxx-len(row))
        try:
            if maxx < typedQSettings().value('TableviewerPickerCols', 10):
                self.ui.colPickerDock.setVisible(False)
        except:
            pass
        self.headers = headers  # too many copies of this? confusing.
        self.model = simpleTable(self.data, headers)
        self.ui.tableView.setModel(self.model)
        self.headermodel = QtCore.QStringListModel(headers, self)
        self.ui.colPicker.setModel(self.headermodel)
        self.tableSelectFix()
        self.want_resize.emit()
        self.firstread = False

    def readmore(self,fromwhere):
        DEBUG = typedQSettings().value('DEBUG',False)
        if self.firstread:  # didn't have any data at start, try again now
            if DEBUG: print('first read') # DEBUG
            self.openfd(self.csvfile)
        # just one line for now
        self.hasmore = True
        #try:
        #if True:
        rows = []
        if DEBUG: print('readmore '+fromwhere)  # DEBUG
        lines = typedQSettings().value('LogBatchLines',100)
        # don't read too many lines at once (prevent lockup)
        row=None
        try:
            row = next(self.csvreader)
            while lines>0 and row:
                rows.append(row)
                try:
                    row = next(self.csvreader)
                except csv.Error:
                    self.hasmore=False
                    break
                lines -= 1
            if row:
                rows.append(row)
        except WaitRead:
            if DEBUG: print(' got waitread')
            self.hasmore = False
            if DEBUG:print('  rows={}'.format(len(rows)))
        except StopIteration:
            if DEBUG:print(' got stop')
            self.hasmore = False
            if DEBUG:print('  rows={}'.format(len(rows)))
        if row and self.hasmore:
            if DEBUG:print('emit readmore') # DEBUG
            self.want_readmore.emit('readmore')
        else:
            self.hasmore = False
        if rows:
            if DEBUG: print("Read {} rows".format(len(rows))) # DEBUG
            self.model.insertRowsAt(1,rows)
            # XXX update headers if row is longer?
        #except StopIteration:
        #    self.hasmore=False
        #    print("Stopping") # EXCEPT this doesn't happen?
        #    # why is the stocket still bothering us
        #    #self.notifier.activated.disconnect()
        #    # maybe close file too? meh.
        #except Exception as e:
        #    print("readmore: "+str(e)) # EXCEPT
        #   # exit(1)
        
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
