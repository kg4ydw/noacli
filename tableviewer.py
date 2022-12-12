#!/usr/bin/env python3

__license__   = 'GPL v3'
__copyright__ = '2022, Steven Dick <kg4ydw@gmail.com>'

# This could be a stand alone application but integreates into noacli
# Think of this as a graphical version of less, but for tables.
#
# Given a blob of text, guess how to interpret it as a table
# and then allow minor manipulations for easier viewing.
# Designed to handle large tables.

## bugs:
# XX Doesn't have its own icon (yet)
# XX Doesn't parse command line options, but it should have a few.

import sys
import os
import io
from functools import partial
from math import ceil, floor
import csv
import re
from statistics import stdev, mean, median

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtGui import QTextCursor
from PyQt5.QtWidgets import QTextEdit, QSizePolicy, QMenu
from PyQt5.QtCore import QCommandLineParser, QCommandLineOption, QIODevice, QSocketNotifier, QSize, QModelIndex, QItemSelectionModel, QProcess
from PyQt5.Qt import Qt, pyqtSignal

from betterio import betterQProcess, betterTextIOWrapper
from tableviewer_ui import Ui_TableViewer
from datamodels import simpleTable
from typedqsettings import typedQSettings

typedQSettings().registerOptions({
    'TableviewerResizeRows': [ False, 'Resize rows automatically after data is read', bool],
    'TableviewerResizeRatio': [ 1.5, 'Max ratio of current size to larger size for automatic window resize if larger', float],
    'TableviewerPickerCols': [10,'Threshold of columns in table, over which the column picker is displayed by default', int],
    'TableviewerBatchLines': [100, 'How many table rows to read at once', int]

    })


# since python's I/O classes can't do non-blocking I/O and line buffering
# at the same time, and Qt's classes don't support iteration, roll our own
# Functions:
# * read data as available
# * convert data to unicode
# * parse data into lines immediately and buffer for future use
# * preread and collect so heuristics can peek before using the data
# * make sure there is always data available before __next__ is called
# * instead of throwing away lines as we parse, maybe keep them all and reparse and rebuild the table when we've got more
class lineBuffer():
    lineEnds = '\n\r\x1d\x1e\x85\v\f\u2028\u2029'  # XX update this? from splitlines
    def __init__(self, file):
        self.file = file
        self.lines = []
        self.eof = 0
        #  enable non-blocking I/O here?
        ## really only appropriate for stdin, and maybe file, so no
        # os.set_blocking(sys.stdin.fileno(),False)
        
    ## replace strpeek with peeklines as often as possible
    def strpeek(self, size):  # XX not gonna fake size default
        # horribly inefficent but meh, only call this once hopefully
        s =  "".join(self.lines)
        if len(s)<size:
            self.canReadLine(True) # get some more
            return "".join(self.lines)
        else:
            return s

    def handleEOF(self):
        # got an eof, clean up any buffer left over
        if len(self.lines)==1 and self.lines[0][-1] not in self.lineEnds:
            #print('terminate at eof') # DEBUG
            self.lines[0]+='\n'
        return len(self.lines)>0 # use up what is left
    def canReadLine(self, readmore=False):
        if not readmore: # force buffer growth for extended peeking
            if len(self.lines)>1: return True
            if len(self.lines)>0 and self.lines[0][-1] in self.lineEnds: return True
        # read until we get a whole line or run out
        # XX should this abort for insanely long lines? how long is that?
        lines=[]
        buf = ''
        while len(lines)<1 or len(lines[0])<1 or lines[0][-1] not in self.lineEnds:
            buffer = self.file.read(1024)
            if buffer==None or len(buffer)==0: break
            if type(buffer)==str:
                buf += buffer
            else:
                buf += buffer.decode('utf-8', errors='backslashreplace')
            lines = buf.splitlines(keepends=True)
        if len(buf)>0:
            self.eof = 0  # we got some data
        # save what we read before doing something about EOF
        if len(lines)>0 and len(self.lines)>0 and self.lines[-1][-1] not in self.lineEnds:
            # append to end of previous line
            self.lines[-1] += lines.pop(0)
        # save any remaining whole lines
        if len(lines)>0:
            self.lines += lines
        # deal with EOF, including using last partial line
        if buffer==None:
            self.eof = 6
            return self.handleEOF()
        elif len(buffer)==0:
            self.eof +=1
            if self.eof>2:
                return self.handleEOF() # failed 3x, maybe done?
        # if not eof, did we get a whole line
        if len(self.lines)==0: return False
        if len(self.lines)>1 or (len(self.lines[0])>0 and self.lines[0][-1] in self.lineEnds):
                return True
        return False

    def peekLines(self, minimum=1 ):
        if len(self.lines)<minimum:
                self.canReadLine(True) # attempt to read more
        return self.lines  # just let 'em see them all
    def __iter__(self):
        return self
    def __next__(self):
        # XXX should this make sure the next line is whole
        # or assume the calling code already called canReadLine
        if len(self.lines)==0:
            raise StopIteration
        return self.lines.pop(0)

            
## ideas to implement and/or document
# context menu
#  refactor columns
# filter/search rows by column
# sort / reset sort
# resize column on double click header
# copy cell to clipboard on click
# copy cell to both clipboards on double click
# select column as vertical header


# this relies on features from lineBuffer to correctly pace I/O
class FixedWidthParser():
    def __init__(self, f, options={}):
        # optimistically do this without peek for now
        # XX this doesn't handle right justified or centered columns
        # which might be fixable with peek
        lines = f.peekLines(2)  # this will try to get 2 lines, but no promises
        # Alternate algorithms: XXX
        # * after picking boundaries, scan down the column to verify
        # * set a bitmap of columns only containing spaces and scan that
        if len(lines)>1 and lines[1][0] in '=-': # second line looks better
            s=lines[1].expandtabs()
            gapthresh = 1  # OPTION SETTING
            # XXX if this works we should eat the two header lines
        else:
            gapthresh=2
            s = lines[0].expandtabs() # hopefully this is left justified headers
        if 'gap' in options: # override guess
            gapthresh = options['gap']
        if 'columns' in options: # don't need to guess
            col = options['columns']
            if col[0]!=0: col.insert(0,0)
        else:
            col = [0]
            i=0
            while i>=0:
                i=s.find(' '*gapthresh,i)
                if i>=0: # find end of column
                    i+=gapthresh
                    while i<len(s) and s[i]==' ':
                        i+=1
                    if i<len(s):
                        col.append(i-(gapthresh-1)) # back up one, put border in the column
        self.col = col
        self.lines = iter(f)
        # XXX maybe the column seps should go into small output too
        print("col = "+(",".join([str(i) for i in col]))) # DEBUG
    
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
            yield [ s[self.col[i]:self.col[i+1]].strip() for i in range(len(self.col)-1) ] + [  s[self.col[-1]:].strip() ]

        
class TableViewer(QtWidgets.QMainWindow):
    window_close_signal = pyqtSignal()
    want_resize = pyqtSignal()
    want_readmore = pyqtSignal(str)
    have_error = pyqtSignal(str)
    def __init__(self, options=None, parent=None):
        super().__init__()
        self.data = []
        self.hasmore = True
        self.firstread = True
        self.useheader = True
        # command line options
        self.skiplines = 0
        self.delimiters = '|\t,:' # defaults
        self.fixedoptions = {}
        self.headers = None
        self.forcefixed=False
        # XXX icon
        # connect to my own event so I can send myself a delayed signal
        self.want_resize.connect(self.actionAdjust, Qt.QueuedConnection)
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


    def simpleargs(self, args):
        # Process simple "command line" arguments from noacli internal parsing
        # only single word options supported, so --option=value must be used
        # XXXXX implement and document command line options
        # ignore --file and --files (processed by caller)
        # --skip N lines
        # --csv --delimiter(s)
        # --regex (delimiter or split pattern? depends on if groups?)
        # --fixed --gap=2 --columns=n[,n]*
        # --header=word[,word]*
        # --noheader
        for arg in args:
            if arg.startswith('--skip='):
                try:
                    self.skiplines = int(arg[7:])
                except:
                    pass # XX arg parse error
            elif arg.startswith('--delimiters='):
                self.delimiters = arg[13:]
            elif arg.startswith('--delimiter='):
                self.delimiters = arg[12:]
            elif arg.startswith('--gap='):
                try:
                    self.fixedoptions['gap'] = int(arg[6:])
                except:
                    pass # XX arg parse error
            elif arg.startswith('--columns='):
                try:
                    self.fixedoptions['columns'] = [ int(x) for x in arg[10:].split(',') ]
                except:
                    pass # XX arg parse error
            elif arg.startswith('--headers='):
                self.headers = arg[10:].split(',')
            elif arg.startswith('--noheader'):
                self.useheader = False
            elif arg.startswith('--fixed'):
                self.forcefixed = True
            #else: ignore anything else without error XXX

    def start(self):
        # probably should do more here and less in open 
        pass

    ################ GUI stuff

    def actionAdjust(self):
        view = self.ui.tableView
        view.resizeColumnsToContents()
        if typedQSettings().value('TableviewerResizeRows',False):
            self.ui.tableView.resizeRowsToContents()
        self.resizeWindowToTable(True) # for automatic calls

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
        # measure the width of every visible column and set the width to mean+2*stdev
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
        if nwide>0:
            extra = (width-tmin)/nwide # distribute what is left over
        else:
            extra = 0 # nobody to distribute it to
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
        # calculate max size based on header sizes and add other decorations
        size = QtCore.QSize(hh.length(), vh.length())
        size += QtCore.QSize(vh.size().width(), hh.size().height())
        size += frame + QtCore.QSize(30, 100)
        # check V and H separately
        # don't resize if ratio is exceeded
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
        # XX could count selected cells before adding to menu...
        m.addAction('Merge adjacent selected cells', self.collapseSelectedCells)
        col = self.ui.tableView.columnAt(event.pos().x())
        if col>=0:
            m.addAction('Hide column',partial(self.hideColumn, col))
        # XX more tableviewer context items??
        action = m.exec_(event.globalPos())

    # context menu triggered
    def hideColumn(self, col):
        self.ui.tableView.setColumnHidden(col, True)

    # context menu triggered
    def collapseSelectedCells(self):
        sm = self.ui.tableView.selectionModel()
        slist = sorted(sm.selectedIndexes(), reverse=True) #XXX test
        # and clear the selection now that we've got the cell list.
        # This gives feedback in case the user tried to do something wierd.
        sm.clear() # XXX only clear ones we've fixed?
        # XXX This gives no error messages if things go wrong
        while len(slist)>1:
            # find consecutive items in the same row
            row = slist[0].row()
            i = 0;
            while i+1<len(slist) and slist[i+1].row()==row and slist[i].column()-1==slist[i+1].column():
                i+=1
            if i>0:
                #print('merge {}: {} + {}'.format(slist[i].row(), slist[i].column(),i)) # DEBUG
                self.model.mergeCells(slist[i], i)
            del slist[0:i+1]
            #if i==0: user only selected one sequental item -- reselect it?
        
    ################ table parsing stuff

    def openfile(self,filename):
        self.setWindowTitle(filename)
        try:
            self.csvfile = lineBuffer(open(filename, errors='backslashreplace'))
        except OSError as e:
            self.error = e.strerror
            err = 'Open failed on {}: {}'.format(filename,e.strerror)
            print(err) # EXCEPT
            # XXX send error somewhere
            self.have_error.emit(err)
            # clean up
            self.setWindowTitle(err)
            self.close()
            self.setParent(None)  # delete later?
            return err
        self.openfd(self.csvfile)
        self.want_readmore.emit('initial') # extra just in case

    def openProcess(self, title, process):
        self.process = process
        self.csvfile = lineBuffer(process)
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
        self.csvfile = lineBuffer(sys.stdin)
        self.notifier = QSocketNotifier(sys.stdin.fileno(),QSocketNotifier.Read, self)
        # set up notifier for incoming data
        self.notifier.activated.connect(partial(self.readmore,'socket'))
        self.openfd(self.csvfile)
        self.setWindowTitle('table stdin')

    def openfd(self, csvfile):
        DEBUG = typedQSettings().value('DEBUG',False)
        maxx=0
        while self.skiplines>0:
            if csvfile.canReadLine():
                next(csvfile)
                self.skiplines -= 1
            else:
                return # need to skip more
        if not csvfile.canReadLine():  # try again later
            return
        peeklines = csvfile.peekLines(1)
        if not peeklines or not peeklines[0]:  # try again later
            return 
        peek = peeklines[0] # just one line for now otherwise csv gets too clever
        # self.firstread = False  # got something, initialize! but in case anything goes wrong, set this later
        if self.forcefixed or '\t ' in peek or ' \t' in peek:  # maybe 3 spaces too?
            if DEBUG: print("Found tabs and spaces, trying fixed width parser") # DEBUG
            self.parser = FixedWidthParser(csvfile, self.fixedoptions)
            self.csvreader = iter(self.parser)
        else:
            # give csv a try and then we try again
            try:
                dialect = csv.Sniffer().sniff(peek, delimiters=self.delimiters)
                self.csvreader = csv.reader(csvfile, dialect)
                if DEBUG: print('got csv') # DEBUG
            except csv.Error:
                self.parser = FixedWidthParser(csvfile, self.fixedoptions)
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
        #else: print("end: {}, {}".format(lines, self.csvfile.canReadLine())) # DEBUG
        if self.headers:
            headers = self.headers
        elif self.useheader:
            headers = self.data[0].copy() # XXX copy or steal first row as headers
        else:
            headers=[]
            # XXX disable header view?
    
        # fix blank headers
        for i in range(len(headers)):
            if headers[i].strip()=='':
                headers[i] = str(i+1)
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
        #if DEBUG: print('readmore '+fromwhere)  # DEBUG
        row=None
        # don't read too many lines at once (prevent lockup from large data)
        lines = int(typedQSettings().value('TableviewerBatchLines',100))
        while lines>0 and self.csvfile.canReadLine():
            row = next(self.csvreader)
            if row: rows.append(row)
            lines -= 1
        if lines<=0:
            self.want_readmore.emit('more more') # get more on next pass
        if rows:
            #if DEBUG: print("Read {} rows".format(len(rows))) # DEBUG
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
