#!/usr/bin/env python3

import sys
import os
import io
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtGui import QTextCursor
from PyQt5.QtWidgets import QTextEdit, QSizePolicy, QMenu
from PyQt5.QtCore import QCommandLineParser, QCommandLineOption, QIODevice, QSocketNotifier, QSize, QModelIndex, QItemSelectionModel
from PyQt5.Qt import Qt, pyqtSignal
from functools import partial
from math import ceil, floor
import csv
import re
from statistics import stdev, mean, median

from tableviewer_ui import Ui_TableViewer

from datamodels import simpleTable

# newData(x1,y1,x2,y2) -> emtChanged.emit([])


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
            return str(self.qio.readLine(), 'utf-8')
        else:
            raise StopIteration # not sure file is done
        # XXX stop iter?

class TableViewer(QtWidgets.QMainWindow):
    window_close_signal = pyqtSignal()
    want_resize = pyqtSignal()
    def __init__(self, options=None, parent=None):
        super().__init__()
        self.data = []
        self.hasmore = True
        self.firstread = True
        self.useheader = True
        # XXX icon
        # connect to my own event so I can send myself a delayed signal
        self.want_resize.connect(self.actionAdjust, Qt.QueuedConnection) # delay this
        self.ui = Ui_TableViewer()
        self.ui.setupUi(self)
        self.ui.menuView.addAction(self.ui.colPickerDock.toggleViewAction())
        self.ui.colPicker.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.colPicker.customContextMenuRequested.connect(self.colPickerContext)
        self.ui.tableView.horizontalHeader().setSectionsMovable(True)
        # XXX hide colPickerDock by default?
        # set model after opening file

    def start(self):
        pass

    def actionAdjust(self):
        view = self.ui.tableView
        view.resizeColumnsToContents()
        ##view.adjustSize()  # does stupid stuff
        self.ui.colPicker.adjustSize() # does stupid stuff
        #self.ui.colPickerDock.adjustSize() # ignored
        mysize = self.size()
        viewsize = view.size()
        frame = mysize-viewsize  # XXX probably wrong
        # ### need to get screen size and max out
        #self.resize(ceil(width), ceil(height))

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
        print("squeeze: m={} sd={} w={} tmin={} mid={} max={} e={}".format(m,s,width, tmin, tmid, tmax, extra))
        if tmax<width: return  # doesn't need to be squeezed
        if tmid>width:  # restrict to std
            extra = 0
        else:
            extra=floor(extra)
        print(" final e={} target={}".format(extra, target))
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
            print("No seleciton model")
            return
        sm.selectionChanged.connect(self.tableSelect)

    def closeEvent(self,event):
        self.window_close_signal.emit()
        super().closeEvent(event)

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
        process.readyRead.connect(self.readmore)
        self.openfd(self.csvfile)
        # self.rebutton('kill', self.terminateProcess) XXX
        # self.file.finished.connect(self.procFinished) ###
        
        
    def openstdin(self):
        # hopefully we at least get the first line with blocking off
        os.set_blocking(sys.stdin.fileno(),False)
        self.csvfile = sys.stdin
        self.notifier = QSocketNotifier(0,QSocketNotifier.Read, self) # XXX 0
        self.notifier.activated.connect(self.readmore)
        self.openfd(sys.stdin)
        self.setWindowTitle('table stdin')
        # set up notifier for incoming data

    def openfd(self, csvfile):
        maxx=0
        # handle either a QProcess.peek or a io.TextIOWrapper.buffer.peek
        # which return different types
        if issubclass(type(csvfile),fakeBufferedReader):
            peek = csvfile.peek(1024)
        else: # python BufferedReader
            peek = csvfile.buffer.peek(1024).decode('utf-8') # XX unportable?
        if not peek:  # must be on a pipe
            print("No data on first read")
            return
        # print("peek = "+str(len(peek))) #XXX
        self.firstread = False
        try:
            dialect = csv.Sniffer().sniff(peek, delimiters='\t,|:')
        except csv.Error:
            print('csv failed to detect dialoect, trying again')
            # well, try my dumb heuristic instead
            ds = {}
            for i in re.findall('[\t,|:]', peek):
                if i in ds: ds[i]+=1
                else: ds[i]=1
            delimiter = max(ds, key=lambda x: ds[x])
            if delimiter=='\t':
                dialect = csv.excel_tab()
            elif delimiter:
                csv.register_dialect('mine', delimiter=delimiter, quoting=csv.QUOTE_NONE)
                dialect = 'mine'
            else:
                print('No delimiter found, I give up')
                raise
        # csvfile.seek(0) # peek makes seek unnecessary
        reader = csv.reader(csvfile, dialect)
        self.csvreader = reader
        for row in reader:
            self.data.append(row)
            x = len(row)
            if x>maxx: maxx=x
        # XXX except?
        if not self.data: return # XXX error
        headers = self.data[0] # XXX copy or steal first row as headers
        if len(headers)<maxx: # extend as necessary
            headers += []*(maxx-len(headers))
        # go ahead and normalize all the rows in the data too
        for row in self.data:
            if len(row)<maxx: # extend as necessary
                row += []*(maxx-len(row))
        self.headers = headers
        self.model = simpleTable(self.data, headers)
        self.ui.tableView.setModel(self.model)
        self.headermodel = QtCore.QStringListModel(headers, self)
        self.ui.colPicker.setModel(self.headermodel)
        self.tableSelectFix()
        self.want_resize.emit()
        self.firstread = False

    def readmore(self):
        if self.firstread:  # didn't have any data at start, try again now
            self.openfd(self.csvfile)
        # just one line for now
        self.hasmore = True
        try:
            # XXXXX this would be faster if it grabbed multiple rows
            row = self.csvreader.__next__()
            if row:
                self.model.appendRow(row)
                # XXXX update headers if row is longer
            else:
                self.hasmore = False
        except StopIteration:
            self.hasmore=False
            # why is the stocket still bothering us
            #self.notifier.activated.disconnect()
            # maybe close file too? meh.
        except Exception as e:
            print(e)
            exit(1)
        
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
