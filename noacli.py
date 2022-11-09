#!/usr/bin/env python3

import os
import sys
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.Qt import Qt, pyqtSignal
from PyQt5.QtGui import QTextCursor, QKeySequence
from PyQt5.QtWidgets import QTextEdit, QSizePolicy, QPlainTextEdit, QShortcut
from PyQt5.QtCore import QCommandLineParser, QCommandLineOption, QIODevice, QModelIndex
from noacli_ui import Ui_noacli
from datamodels import simpleTable, History, jobItem, jobTableModel

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

    @QtCore.pyqtSlot(QModelIndex)
    def jobDoubleClicked(self, index):
        if not index.isValid(): return
        col = index.column()
        if col==0:
            text = str(index.model().jobItem(index).process.processId())
            self.app.clipboard().setText(text)
        elif col==1: index.model().cleanupJob(index)  # job status
        elif col==2: self.windowShowRaise(index)
        elif col==3: self.ui.plainTextEdit.acceptCommand(index.model().jobItem(index).command())

    def windowShowRaise(self,index):
        job = index.model().jobItem(index)
        job.windowOpen = True
        job.window.show()
        job.window.raise_()
            
    def resetHistorySort(self):
        # this is probably dumb, but there's not currently a UI to do this
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
        print("run last")
        last = self.settings.history.last()
        self.runCommand(None,last)

    # slot to connect command window runCommand
    def runCommand(self, command, hist):
        self.resetHistorySort()
        # XXX command is redundant?
        j = jobItem(hist)
        self.settings.jobs.newjob(j)
        j.start()
        # XX try to fix job table size every time?
        self.ui.jobTableView.resizeColumnsToContents()

class commandEditor(QPlainTextEdit):
    command_to_run = pyqtSignal(str, QModelIndex)

    def __init__(self, parent):
        print
        super(commandEditor,self).__init__(parent)
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
            ## broken
            #j = jobItem(h)
            #self.ui
            #j.start()
            
            super(commandEditor,self).clear()  # bypass internal clear
            self.histindex = None
            
    def clear(self):
        # save previous contents in history if modified
        if self.document().isModified():
            # XX this should be done with a signal instead
            self.history.saveItem(self.toPlainText(), self.histindex, None)
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

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    #XXX QtCore.QCoreApplication.setOrganizationName("ssdApps");
    QtCore.QCoreApplication.setApplicationName("noacli");

    # XXX process command line args

    settings = settings()
    mainwin = noacli(settings)
    mainwin.app = app
    w = mainwin.ui

    mainwin.show()
    mainwin.start()

    app.exec_()

