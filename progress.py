__license__   = 'GPL v3'
__copyright__ = '2026 Steven Dick <kg4ydw@gmail.com>'

# show a progress indicator for a process that outputs

# initial version just uses a QprogressBar but we wanna do a pie chart,
# maybe a concentric pie chart eventually

import argparse, time
from functools import partial

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QRect, QSize, QProcess
from PyQt6.QtCore import QRegularExpression as re
from PyQt6.QtGui import QPainter, QPen, QBrush, QTextOption, QColor, QAction
from PyQt6.QtWidgets import QDockWidget, QMenu, QWidget, QSizePolicy

from lib.progress_ui import Ui_progressDock
from lib.colorpicker import ColorPicker
from lib.typedqsettings import typedQSettings
from lib.saved_searches import saved_searches, searchModel

# replacement progress widgets:
# * stacked progress bar
# * concentric pie graph

# not implmeented yet:
# * stdin
# * flies (!?)
# * resize hint (keep pie square)
# * switch between progress bar and pie graph
# * command line option parsing
# lots of XXXX

class ProgressDock(QDockWidget):
    want_read_more = pyqtSignal(str)
    window_close_signal = pyqtSignal()

    # XXX make this configurable SETTINGS
    pro_regex_list = [ 'per', 'lp', 'lvt' ] # NOTE: 0 based! fix that below
    pro_regex = {
        # shortname: description, regex
        'per' : [ 'Percentage' , r"(\d+)%"],
        'lp'  : [ "Label and percentage", r"(\w+) (\d+)"],
        'lvt' : [ "Label value/total", r"(\w+) (\d+)/(\d+)"]
        }
    
    def __init__(self, title, jobitem):
        super().__init__(title)
        self.started = False
        self.jobitem = jobitem # XX do we need this?
        self.ui = Ui_progressDock()
        self.ui.setupUi(self)
        ## stuff designer can't set or is messy to set properly
        refreshAction = QAction(self)
        icon = QtGui.QIcon.fromTheme("media-playback-start")
        refreshAction.setIcon(icon)
        refreshAction.triggered.connect(self.refresh)
        self.ui.toolButton.setDefaultAction(refreshAction)
        #self.ui.toolButton.triggered.connect(self.refresh)
        self.ui.toolButton.setMenu(self.mymenu(self.ui.toolButton))
        self.ui.progressBar.setValue(0) # non-zero looks better in designer
        # replace progress bar with pie or progress bar stack
        # for now, just do the pi XXX
        #self.pwidget = StackedProgressBar()
        self.pwidget = concentricPieGraph(self, '')
        self.ui.splitter.replaceWidget(0, self.pwidget)
        self.ui.splitter.setCollapsible(0, False) # don't collapse status
        self.ui.splitter.setSizes([1,0])
        self.ui.splitter.setStretchFactor(0, 10)
        self.ui.splitter.setStretchFactor(1, 0)
        self.ui.textBrowser.setWordWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        self.setMinimumSize(10,10)  # designer won't set it small enough
        self.ui.regex.editingFinished.connect(self.patternEdited)
        self.ui.regex.returnPressed.connect(self.readmore) # retrigger search
        self.ui.regex.textEdited.connect(lambda t: self.ui.regex.setToolTip(''))
        self.setDelay(0)
        self.ui.delay.editingFinished.connect(self.delayEdited)
        self.ui.regex.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.ui.regex.customContextMenuRequested.connect(self.regexContextMenu)
        # XX maybe instead of splitter, use a dialog box
        ## stuff noacli looks for -- should this be put in jobitem ?
        self.runcount = 0 
        self.timestart = time.monotonic()  # in case we miss the real start
        self.runtime = None
        self.setDelay(0) # disable
        # XXX add dock to noacli main window?
        ## bind keys
        self.closekey = QtGui.QShortcut(QtGui.QKeySequence.StandardKey.Close,self, self.close) # MacOS because we don't have a close menu item
        self.refreshkey = QtGui.QShortcut(QtGui.QKeySequence.StandardKey.Refresh,self, self.refresh)
        ## misc internal stuff
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.buffer = ''
        self.setPattern(r"(\d+)%")
        self.patternre = re(self.pattern)
        self.file = None
        self.want_read_more.connect(self.readmore, Qt.ConnectionType.QueuedConnection)  # read more after everything else is updated
        
    ## widget helpers

    def regexContextMenu(self, point):
        m = QMenu(self)
        for regex in self.pro_regex_list:
            m.addAction(f"{regex}: {self.pro_regex[regex][0]}",
                        partial(self.setPattern, self.pro_regex[regex][1]))
        # XXX ? m.addSeparator()
        dsm = searchModel.getDefaultSearchModel()
        # XXX sort before adding to menu?
        for item in dsm:
            ii = dsm.getItem(item)
            if ii.useInProgress:
                m.addAction(ii.name, partial(self.setPattern, ii.sexp))
        text = self.ui.regex.text()
        if text:
            m.addSeparator()
            m.addAction("Save as new", self.savedSearchesDialog)
        m.exec(self.ui.regex.mapToGlobal(point))

    def savedSearchesDialog(self):
        text = self.ui.regex.text()
        self.ssd = saved_searches(None, inputText=text)

    def setPattern(self, pattern):
        self.pattern = pattern
        self.patternre = re(pattern, re.PatternOption.MultilineOption|re.PatternOption.UseUnicodePropertiesOption)
        if self.patternre.isValid():
            self.ui.regex.setToolTip("OK")
        else:
            self.ui.regex.setToolTip(self.patternre.errorString())
        self.ui.regex.setText(pattern)

    def patternEdited(self):
        self.setPattern(self.ui.regex.text())

    def setDelay(self, delay):
        self.refreshdelay = delay
        if hasattr(self, 'timer') and not delay:
            self.timer.stop()
        self.ui.delay.setText(str(self.refreshdelay))
        if self.started: self.refresh()

    def delayEdited(self):
        try:
            i = int(self.ui.delay.text())
            if i>=0: self.setDelay(i)
        except Exception as e:
            #print(f"fail set delay: {repr(e)}") # DEBUG
            pass # nowhere to send error?
                              
    ### common with OutWin for files

    def simpleargs(self, args):
        # XXXXX parse options
        # regex
        # stock regex index
        # if ss: split
        #  if integer, pull from table
        #  if name, try table then saved searches
        # direct regex on cli?
        # delay
        pass

    def start(self):
        self.started = True
        # XXXX called after show()
        pass

    #def openfile(self, file): XX
    # openProcess below

    #### gui pieces
    
    def collapseSettings(self):
        self.ui.splitter.setSizes([1,0])
        # XXX shrink window?
        
    def uncollapseSettings(self):
        self.ui.splitter.setSizes([1,1])

    def mymenu(self, parent):
        # used for both tool button and context menus
        m = QMenu(parent)
        m.aboutToShow.connect(partial(self.aboutToShowMenu, m))
        return m

    def contextMenuEvent(self, event):
        m = self.mymenu(self)
        m.exec(self.mapToGlobal(event.pos()))

    def aboutToShowMenu(self, m, action=None):
        m.clear()
        if self.ui.splitter.sizes()[1]:
            m.addAction("Collapse settings", self.collapseSettings)
        else:
            m.addAction("Edit settings", self.uncollapseSettings)
            # XXX
            # progress bar / pie graph
            # start / stop / refresh / kill / close
            # edit command !?
        #if self.isFloating():  # XXX find parent to dock to
        #    m.addAction("Dock", partial( self.setFloating,False))
        if self.ui.progressSettings.isHidden():
            m.addAction("Show settings", self.showsettings)
        else:
            m.addAction("Hide settings", self.ui.progressSettings.hide )
        m.addAction("Refresh", self.refresh )
        m.addAction("Dismiss finished", self.pwidget.cleanFinished)
        m.addAction("Reset graph", self.pwidget.resetGraph)
        return m

    def showsettings(self):
        self.ui.progressSettings.show()
        self.ui.splitter.setSizes([1,1])

    def setInterval(self, value=None):  # XXX interval changed box
        pass

    def visibilityChanged_x(self): # gui event
        # if not visible, cancel timer
        # if visible, refresh
        pass

    #### noacli and QProcess pieces
    # possible entrypoints: openfile openstdin openProcess openPretext start?
    # only openProcess implemented for now
    # XXX parse args??

    def openProcess(self, title, process):
        self.file = process
        # XXXX opt?
        if not hasattr(self, 'opt') or not self.opt.title:
            self.setWindowTitle(title or 'progress')
        # setupProc
        self.file.readyRead.connect(self.readmore)
        self.file.started.connect(self.procStarted)
        self.file.finished.connect(self.procFinished)

    def procStarted(self):
        self.timestart = time.monotonic()
 
    def procFinished(self, exitcode, estatus):
        self.exitcode = exitcode
        self.timestop = time.monotonic()
        # calculate running average
        t = self.timestop-self.timestart
        if self.runtime is None: self.runtime=t
        self.runtime = self.runtime * 0.6 + t*0.4
        if self.refreshdelay and  self.runtime > self.refreshdelay*3:
            self.refreshdelay = int(self.runtime) # not too fast!
        if self.refreshdelay:
            self.timer.start(self.refreshdelay*1000)
        
    def closeEvent(self, event):
        self.timer.stop()
        # XXX more? does a dock need to close?
        self.window_close_signal.emit()
        super().closeEvent(event)

    def show(self):
        super().show()
        self.refresh()  # reset timers if necessary

    #### action pieces

    def refresh(self): # XXXX timer or key
        # if isinstance(self.file, QProcess): XXX file or process
        if not self.file:
            return
        if self.file.state() == QProcess.ProcessState.Running:
            return # ignore until it's done
        if self.isHidden():
            return # do nothing while hidden
        self.buffer = ''
        # XXXX guard to prevent rerunning process too fast
        # XXXX rerun process immeidately
        self.file.start()
        # (maybe) restart timer in process finish event handler?

    def readmore(self): # ready read event or want_read_more internal signal
        b = str(self.file.readAll(), 'utf-8')
        # if peek, readmore and keep buffer
        if self.buffer:
            b = self.buffer + b
        self.ui.textBrowser.setPlainText(b)
        if not b: return  # XXX EOF detection goes here!
        # self.file.atEnd()
        # XXXX
        # XXX use compiled regex?

        # find the last two matches
        prev = None
        last = None
        if not self.pattern or len(self.pattern)==0:
            self.buffer = b
            return
        reiter = self.patternre.globalMatch(b)
        if not reiter.hasNext():
            # if not found, save everything for next time
            self.buffer = b
            return
        while reiter.hasNext():
            match= reiter.next()
            label = None
            valstr = None
            # XX also support labeled groups?
            #print(f"match {match.lastCapturedIndex()} = {match.captured(1)} / {match.captured(2)} / {match.captured(3)}") # DEBUG
            match match.lastCapturedIndex():
                case 0:  # whole string, hope it's a integer percentage
                    valstr = match.captured(0)
                case 1:  # 1: integer percentage
                    valstr = match.captured(1)
                case 2:  # 2: label, percentage
                    label = match.captured(1)
                    valstr = match.captured(2)
                case g if g>=3:  # 3: label, current, max, or WTF (ranged?)
                    label = match.captured(1)
                    try: # lots of things can go wrong here
                        val = int(float(match.captured(2)) / float(match.captured(3)))
                    except: # parse error, division by zero
                        pass
            if label:  # save each labeled value
                try:
                    self.pwidget.setValue(int(valstr), label)
                except Exception as e:
                    if typedQSettings().value('DEBUG',False): print(repr(e))
                    pass
        if not label:  # only keep the last naked value
            try:
                self.pwidget.setValue(int(valstr), '')
            except:
                if typedQSettings().value('DEBUG',False): print(repr(e))
                pass
        # only keep stuff after the last match
        self.buffer = b[match.capturedEnd():]
        # XXXX
        # if more to read, emit want_read_more
        # if process is finished and restartable (and not 100%), start timer


class stackedProgressBar(QWidget):
    # init default name
    # set tooltips
    # change format?
    pass

class concentricPieGraph(QWidget):
    # init default name
    # set tooltips
    # paint widget
    def __init__(self, parent, name):
        super().__init__(parent)
        # widget stuff
        self.setMinimumSize(QSize(20,20))
        # this doesn't work without adding a layout and stretch
        # just leave it squished for now
        #p = QSizePolicy()
        #p.setHorizontalStretch(10)
        #p.setVerticalStretch(10)
        #p.setVerticalPolicy(QSizePolicy.Policy.Expanding)
        #p.setHorizontalPolicy(QSizePolicy.Policy.Expanding)
        #p.setHeightForWidth(True)
        #p.setWidthForHeight(True)
        #self.setSizePolicy(p)
        # set up first value
        self.colorpicker = ColorPicker()
        self.colors = {name: self.colorpicker.nextColor()} # XX
        #print(f"concentric '{name}' : [{self.colors[name]}]") # DEBUG
        self.names = [name]
        self.values = {name: 0}
        self.offsets = { name: 0}

    def sizeHint(self):
        return QSize(100,100)

    def resetGraph(self):
        self.names = ['']  # delete 'em all, keep colors just in case
        self.offsets = { '': 0}
        self.values = {'': 0}
        self.update()

    def setValue(self, val, name=''):
        if name not in self.names:
            # new value!
            prev = self.names[-1]
            self.names.append(name) # keep the names in order
            if name not in self.colors: # keep old color
                self.colors[name] = self.colorpicker.nextColor()
            # start where the prev was when we started, just for fun
            self.offsets[name] = (self.values[prev]+self.offsets[prev])%100
            # if there was an empty default value, delete it
            if self.names[0]=='':
                self.names = self.names[1:]
        #print(f"concentric '{name}'={val} : ") # DEBUG
        self.values[name] = val
        self.update()

    def cleanFinished(self):
        finished = set([name for name in self.names if self.values[name]==100])
        self.names = [name for name in self.names if name not in finished]
        self.update()

    # XXX resize ratio override to keep widget square
    def heightForWidth(w):
        return w
    def widthForHeight(w):
        return w
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setPen(QPen(Qt.GlobalColor.black,2))
        rect = self.geometry()
        dx = rect.width() / len(self.values)/2
        dy = rect.height() / len(self.values)/2 # really should be square...
        tooltip = ''
        for i, n in enumerate(self.names):
            # print(f"{n} = {self.colors[n]} {self.offsets[n]} {self.values[n]}") # DEBUG
            tooltip += f"{n} = {self.values[n]}\n"
            nr = QRect(int(dx*i), int(dy*i), int(rect.width()-dx*i*2), int(rect.height()-dy*i*2))
            # painter.setBrush(QColor(self.colors[n]), Qt.BrushStyle.SolidPattern)
            painter.setBrush(QColor(self.colors[n]))
            painter.drawPie(nr, int(self.offsets[n]*360/100*16), int(self.values[n]*360/100*16))
        painter.end()
        self.setToolTip(tooltip)
        # XX what about multi-value progress? is that a thing?
