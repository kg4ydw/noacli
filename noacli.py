#!/usr/bin/env python3

import os
import sys
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.Qt import Qt, pyqtSignal
from PyQt5.QtGui import QTextCursor, QKeySequence
from PyQt5.QtWidgets import QTextEdit, QSizePolicy, QPlainTextEdit, QShortcut, QAction
from PyQt5.QtCore import QCommandLineParser, QCommandLineOption, QIODevice, QModelIndex
from noacli_ui import Ui_noacli
from datamodels import simpleTable, History, jobItem, jobTableModel
from functools import partial

# initialize, load, hold, and save various global settings
class settings():
    def __init__(self):
        # XXX initalize QSettings first
        
        # create skelectons of settings and read previous or set defaults
        self.history = History()
        self.history.read()
        # 
        self.buttons = [ ]
        self.buttonModel = simpleTable(self.buttons, [  'command', 'button', 'immediate' ])
        # XXX populate environment from real environment
        self.environment = []  # [ 'name', 'value']
        ##  [ 'name', 'value', 'propagate', 'save' ])
        self.jobs = jobTableModel()
        # job manager needs a special class
        
        ## [ pid? , type, command, status // kill raise info rerun

class noacli(QtWidgets.QMainWindow):
    def __init__(self, settings):
        super(noacli,self).__init__()
        self.ui = Ui_noacli()
        self.ui.setupUi(self)
        self.settings = settings
        self.historypos = 1;
        dir = os.path.dirname(os.path.realpath(__file__))
        self.setWindowIcon(QtGui.QIcon(dir+'/noacli.png'))
       
        # hide all the docks by default XXX unless set in settings?
        ui=self.ui
        self.hideAllDocks()
        # XXX show buttons by default?

        # populate the view menu (is there a more automatic way?)
        ui.menuViews.addAction(ui.history.toggleViewAction())
        ui.menuViews.addAction(ui.jobManager.toggleViewAction())
        ui.menuViews.addAction(ui.buttons.toggleViewAction())

        # convert all the docs to tabs XXX preferences?
        self.tabifyDockWidget( ui.buttons,ui.jobManager)
        self.tabifyDockWidget( ui.jobManager, ui.history)

        # attach the data models to the views
        ui.historyProxy = QtCore.QSortFilterProxyModel()
        ui.historyProxy.setSourceModel(self.settings.history)
        ui.historyProxy.setFilterKeyColumn(1)
        ui.historyView.setModel(ui.historyProxy)
        ui.historySearch.textChanged['QString'].connect(ui.historyProxy.setFilterFixedString)

        # make all the tables fit
        ui.historyView.resizeColumnsToContents()
        ui.jobTableView.resizeColumnsToContents()

        # connect the command editor to the history data model
        # XX this should be a connect historySave->saveItem
        ui.plainTextEdit.setHistory(self.settings.history)
        
        ui.jobTableView.setModel(self.settings.jobs)

        # mess with the history corner button
        cb = ui.historyView.findChild(QtWidgets.QAbstractButton)
        if cb:
            cb.disconnect()
            cb.clicked.connect(self.resetHistorySort)
        # mess with job manager corner button (is this even visible?)
        cb = ui.jobTableView.findChild(QtWidgets.QAbstractButton)
        if cb:
            cb.disconnect()
            cb.clicked.connect(self.settings.jobs.cleanup)

        # XXXX build history context menu
        self.ui.historyMenu.aboutToShow.connect(self.buildHistoryMenu)
        self.ui.menuJobs.aboutToShow.connect(self.buildJobMenu)

        self.ui.historyView.scrollToBottom()


    @QtCore.pyqtSlot(QModelIndex)
    def jobDoubleClicked(self, index):
        if not index.isValid(): return
        col = index.column()
        if col==0:
            text = str(index.model().getItem(index).process.processId())
            self.app.clipboard().setText(text)
        elif col==1: index.model().cleanupJob(index)  # job status
        elif col==2: self.windowShowRaise(index)
        elif col==3: self.ui.plainTextEdit.acceptCommand(index.model().getItem(index).command())

    def windowShowRaise(self,index):
        if isinstance(index, QAction): index = index.data() # unwrap
        job = index.model().getItem(index)
        job.windowOpen = True
        job.window.show()
        job.window.raise_()
            
    def resetHistorySort(self):
        self.ui.historyProxy.sort(-1)
        self.ui.historyView.horizontalHeader().setSortIndicator(-1,0)
        #self.historyProxy.invalidate()
        
    def start(self):
        # nothing else to initialize yet
        pass

    @QtCore.pyqtSlot()
    def showAllDocks(self):
        ui = self.ui
        ui.history.setVisible(True)
        ui.buttons.setVisible(True)
        ui.jobManager.setVisible(True)

    @QtCore.pyqtSlot()
    def hideAllDocks(self):
        ui = self.ui
        ui.history.setVisible(False)
        ui.buttons.setVisible(False)
        ui.jobManager.setVisible(False)

    # push button signal
    @QtCore.pyqtSlot()
    def runLastCommand(self):
        last = self.settings.history.last()
        self.runCommand(None,last)

    # slot to connect command window runCommand
    def runCommand(self, command, hist):
        if hist and isinstance(hist.model(),QtCore.QSortFilterProxyModel ):
            hist=hist.model().mapToSource(hist)
        self.resetHistorySort()  # XXX this might be annoying
        # XXX command is redundant? but external stuff calls us
        j = jobItem(hist)  # XX construct new job
        self.settings.jobs.newjob(j)
        j.start()
        # XX try to fix job table size every time?
        self.ui.jobTableView.resizeColumnsToContents()

    # slots for history dock context menu
    def deleteSelected(self):
        # XX reuse this somehow?
        indexes = ui.historyView.selectionModel().selectedRows()
        while indexes:  # XX delete ranges for higher efficency?
            i = indexes.pop()
            i.model().removeRow(self, i.row(), QModelIndex())

    # menu action
    def actionSaveHistory(self):
        self.settings.history.write()

    def closeEvent(self, event):
        self.actionSaveHistory()

    # dynamic portion of history menu
    @QtCore.pyqtSlot()
    def buildHistoryMenu(self):
        hm = self.ui.historyMenu
        # first destroy old entries
        # XXXX does this work?
        for a in hm.actions():
            if a.data(): hm.removeAction(a)
        # add new entries
        h = self.settings.history.last()
        i = 5  # XXX setting: history menu size
        cmds=set()
        while i>0 and h:
            c = str(h.data())
            if c not in cmds:
                act = QAction(h.data(), self)
                act.setData(h)
                hm.addAction(act)
                act.triggered.connect(partial(self.acceptHistoryAction,act))
                cmds.add(c)
                i -= 1
            h = h.model().prevNoWrap(h)

    def acceptHistoryAction(self, act):
        self.ui.plainTextEdit.acceptHistory(act.data())

    @QtCore.pyqtSlot()
    def buildJobMenu(self):
        jm = self.ui.menuJobs
        jm.clear()
        if self.settings.jobs.isEmpty():
            jm.addAction('No jobs left')
            return
        # XXX threshold for too many jobs in this menu
        # XX if there's too many, how do we filter?
        # XX active jobs or all jobs?
        jobs = self.settings.jobs
        for j in jobs:
            s = str(j.model().getItem(j))
            act = QAction(s,  self)
            act.setData(j)
            jm.addAction(act)
            act.triggered.connect(partial(self.windowShowRaise,act))
        
class commandEditor(QPlainTextEdit):
    command_to_run = pyqtSignal(str, QModelIndex)

    def __init__(self, parent):
        super(commandEditor,self).__init__(parent)
        self.ui = parent.parent().ui
        self.histindex = None
        self.history = None
        self.histUp = QShortcut(QKeySequence('ctrl+up'),self)
        self.histUp.activated.connect(self.historyUp)
        self.histDown = QShortcut(QKeySequence('ctrl+down'), self)
        self.histDown.activated.connect(self.historyDown)
        self.runCmd2 = QShortcut(QKeySequence(QKeySequence.InsertLineSeparator), self)
        self.runCmd2.activated.connect(self.runCommand)
        self.runCmd3 = QShortcut(QKeySequence('Ctrl+Return'), self)
        self.runCmd3.activated.connect(self.runCommand)
        # shift return does not work!?  override keyPressEvent instead?
        self.runCmd4 = QShortcut(QKeySequence('Shift+Return'), self)
        self.runCmd4.activated.connect(self.runCommand)

    def setHistory(self, hist):
        self.history = hist

    @QtCore.pyqtSlot()
    def historyUp(self):
        if not self.history: return
        self.acceptHistory(self.history.prev(self.histindex))
    @QtCore.pyqtSlot()
    def historyDown(self):
        self.acceptHistory(self.history.next(self.histindex))

    @QtCore.pyqtSlot()
    def runCommand(self):
        text = self.toPlainText()
        if text:
            h = self.history.saveItem(text, self.histindex, None)
            self.command_to_run.emit(text, h)
            
            super(commandEditor,self).clear()  # bypass internal clear
            self.histindex = None
            
    def clear(self):
        # save previous contents in history if modified
        if self.document().isModified():
            # XX this should be done with a signal instead
            i = self.history.saveItem(self.toPlainText(), self.histindex, None)
            if i: self.ui.historyView.scrollTo(i)
        self.histindex = None
        super(commandEditor,self).clear()

    def acceptCommand(self, str):
        self.clear()
        self.histindex = None
        self.setPlainText(str)
        
    #is this right? @QtCore.pyqtSlot(QModelIndex)
    def acceptHistory(self, idx):
        self.clear()
        self.histindex = idx;
        str = idx.siblingAtColumn(1).data(Qt.EditRole)
        self.setPlainText(str)
        #unnecssary?# self.document().setModified( idx.siblingAtColumn(0).data(Qt.DisplayRole)==None)
        # scroll history window to this entry XX optional?
        self.ui.historyView.scrollTo(idx)

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    QtCore.QCoreApplication.setOrganizationName("kg4ydw");
    QtCore.QCoreApplication.setApplicationName("noacli");

    # XXX process command line args

    settings = settings()
    mainwin = noacli(settings)
    mainwin.app = app
    w = mainwin.ui

    mainwin.show()
    mainwin.start()

    app.exec_()

