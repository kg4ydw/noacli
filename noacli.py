#!/usr/bin/env python3

import os
import sys
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.Qt import Qt
from PyQt5.QtGui import QTextCursor, QKeySequence
from PyQt5.QtWidgets import QTextEdit, QSizePolicy, QPlainTextEdit, QShortcut
from PyQt5.QtCore import QCommandLineParser, QCommandLineOption, QIODevice
from noacli_ui import Ui_noacli
from datamodels import simpleTable, History

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
        self.jobs = []
        # job manager needs a special class
        ## [ pid? , type, command, status // kill raise info rerun

class noacli(QtWidgets.QMainWindow):
    def __init__(self, settings):
        super(noacli,self).__init__()
        self.ui = Ui_noacli()
        self.ui.setupUi(self)
        self.settings = settings
        self.historypos = 1;
       
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
        # special tweaks XXX this could be subclassed instead
        ui.historyView.resizeColumnsToContents()

        # connect the command editor to the history data model
        # XX this should be a connect historySave->saveItem
        ui.plainTextEdit.setHistory(self.settings.history)
        
        # ui.jobTableView.setModel(settings.jobManagerModel)

    def start(self):
        # XXX nothign to initialize yet
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

class commandEditor(QPlainTextEdit):
    def __init__(self, parent):
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
            # XXX run it here
            # RunProcess(h)
            super(commandEditor,self).clear()  # bypass internal clear
            self.histindex = None
            
    def clear(self):
        # XXX save previous contents in history if modified
        if self.document().isModified():
            # XX this should be done with a signal instead
            self.history.saveItem(self.toPlainText(), self.histindex, None)
        self.histindex = None
        super(commandEditor,self).clear()

    #is this right? @QtCore.pyqtSlot(QModelIndex)
    def acceptHistory(self, idx):
        self.clear()
        self.histindex = idx;
        str = idx.siblingAtColumn(1).data(Qt.EditRole)
        self.setPlainText(str)
        #unnecssary?# self.document().setModified( idx.siblingAtColumn(0).data(Qt.DisplayRole)==None)

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    app.setWindowIcon(QtGui.QIcon("noacli.png"))
    #XXX QtCore.QCoreApplication.setOrganizationName("ssdApps");
    QtCore.QCoreApplication.setApplicationName("noacli");

    # XXX process command line args

    settings = settings()
    mainwin = noacli(settings)
    w = mainwin.ui

    mainwin.show()
    mainwin.start()

    app.exec_()

