#!/usr/bin/env python3

import sys
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtGui import QTextCursor
from PyQt5.QtWidgets import QTextEdit, QSizePolicy
from PyQt5.QtCore import QCommandLineParser, QCommandLineOption, QIODevice
from noacli_ui import Ui_noacli
from simpleTable import simpleTable

# initialize, load, hold, and save various global settings
class settings():
    def __init__(self):
        # create skelectons of settings
        self.history = []
        self.buttons = [ ]
        self.buttonModel = simpleTable(self.buttons, [  'command', 'button', 'immediate' ])
        # XXX populate environment from real environment
        self.environment = []  # [ 'name', 'value']
        self.environmentModel = simpleTable(self.environment,[ 'name', 'value', 'propagate', 'save' ])
        self.jobs = []
        # job manager needs a special class
        ## [ pid? , type, command, status // kill raise info rerun

class noacli(QtWidgets.QMainWindow):
    def __init__(self, settings):
        super(noacli,self).__init__()
        self.ui = Ui_noacli()
        self.ui.setupUi(self)
        self.settings = settings
        
        # hide all the docks by default XXX unless set in settings?
        ui=self.ui
        self.hideAllDocs()
        # XXX show buttons by default?

        # create the view menu
        ## doesn't work
        #ui.viewMenu = QtWidgets.QMenu(self.menubar)
        #ui.viewMenu = self.createPopupMenu()
        #ui.viewMenu.setObjectName("viewMenu")
        # XXX doesn't work
        #ui.menubar.addAction(ui.viewMenu.menuAction())

        # populate the view menu (is there a more automatic way?)
        ui.menuViews.addAction(ui.history.toggleViewAction())
        ui.menuViews.addAction(ui.jobManager.toggleViewAction())
        ui.menuViews.addAction(ui.buttons.toggleViewAction())
        ui.menuViews.addAction(ui.buttoneditor.toggleViewAction())
        ui.menuViews.addAction(ui.environment.toggleViewAction())

        # attach the data models to the views
        # XXX ui.historyListView.setModel(historyModel)
        ui.buttonTableView.setModel(settings.buttonModel)
        ui.environmentTableView.setModel(settings.environmentModel)
        # ui.jobTableView.setModel(settings.jobManagerModel)

    def start(self):
        # XXX nothign to initialize yet
        pass

    @QtCore.pyqtSlot()
    def showAllDocs(self):
        ui = self.ui
        ui.history.setVisible(True)
        ui.buttons.setVisible(True)
        ui.buttoneditor.setVisible(True)
        ui.environment.setVisible(True)
        ui.jobManager.setVisible(True)

    @QtCore.pyqtSlot()
    def hideAllDocs(self):
        ui = self.ui
        ui.history.setVisible(False)
        ui.buttons.setVisible(False)
        ui.buttoneditor.setVisible(False)
        ui.environment.setVisible(False)
        ui.jobManager.setVisible(False)

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
