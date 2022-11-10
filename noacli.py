#!/usr/bin/env python3

import os
import sys
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.Qt import Qt, pyqtSignal
from PyQt5.QtGui import QTextCursor, QKeySequence
from PyQt5.QtWidgets import QTextEdit, QSizePolicy, QPlainTextEdit, QShortcut, QAction
from PyQt5.QtCore import QCommandLineParser, QCommandLineOption, QIODevice, QModelIndex, QSettings
from noacli_ui import Ui_noacli
from settingsdialog_ui import Ui_settingsDialog
from datamodels import simpleTable, History, jobItem, jobTableModel, settingsDataModel
from functools import partial
from qtail import myOptions as qtailSettings


# initialize, load, hold, and save various global settings
class settings():
    # key : [ default, tooltip, type ]
    settingsDirectory = {
            # All uppercase are inherited(?) from bash
          # 'GraphicalTerminal': ['gnome-shell', 'Graphical terminal used to run commands requiring a tty', str],
            'HISTSIZE':     [ 1000, 'Number of history entries kept in memory', int],
            'HISTFILESIZE': [ 1000, 'Number of history entries saved to disk', int ],
            'HistFile':     [ '.noacli_history', 'name of file to save history (full path or relative to home)', str],
          # 'HISTCONTROL':  ['', 'options: ignorespace ignoredups erasedups', str],
            'HistMenuSize': [ 10, 'number of unique recent history entries to show in the history pull down menu', int],
            'HistMenuWidth':[ 30, 'maximum width of commands listed in the history menu', int],
            'JobCleanTime': [120, 'interval in seconds to check for expired jobs', int ], # XX could be float
            'JobMenuWidth': [ 30, 'maximum width of commands listed in the job menu', int],
            'SHELL':       [ 'bash -c', 'external shell wrapper command to run complex shell commands', str],
        # qtail options
            'QTailMaxLines': [ 10000, 'maximum lines remembered in a qtail window', int],
            'QTailEndBytes': [ 1024*1024, 'Number of bytes qtail rewinds a file', int],
            'QTailDefaultTitle': [ 'subprocess', 'Default title for a qtail process window', str ],
           #'QTailFormat': [ 'plaintext', 'plaintext or html', str ],
            # 'QTailFollow': [ False, 'scroll qtail to the end of the file on updates', bool ],
            # 'QTailWrap':  [ True, 'wrap long lines', bool ]
            # 'QTailSearchMode': ['exact', 'exact or regex search mode', str],
            # 'QTailCaseInsensitive': [True, 'Ignore case when searching', bool],
    }

    def __init__(self):
        # create skelectons of settings and read previous or set defaults
        self.history = History()
        self.history.read()
        #
        self.buttons = [ ]
        # XXX
        self.buttonModel = simpleTable(self.buttons, [  'command', 'button', 'immediate' ])
        # XXX populate environment from real environment
        self.environment = []  # [ 'name', 'value']
        ##  XXX [ 'name', 'value', 'propagate', 'save' ])
        self.jobs = jobTableModel()
        # job manager gets its own special class
        
        self.qtail = qtailSettings()
        self.copy2qtail()

        ## settings dialog info
        # name, default, tooltip / description
        # Note: defaults here might not match the real defaults embeeded in code
    def makeDialog(self):
        qs = QSettings()
        # collect list of rows including settings
        # build a list of settings, each source sorted separately
        rows = sorted(self.settingsDirectory.keys())
        # add additional settings from QSettings (missing from dict)
        rows += [i for i in sorted(qs.allKeys()) if i not in self.settingsDirectory]
        # get qtail defauls
        qt = {
            'QTailMaxLines': self.qtail.maxLines,
            'QTailEndBytes': self.qtail.tailFrag,
            'QTailDefaultTitle': 'subprocess',
            'QtailFormat': self.qtail.format,
            }
        # build settings table using rows
        # all qtail settings are already in docdict but values need to be merged
        data = [ [i, qs.value(i, qt.get(i) or None)] for i in rows]
        self.data = data
        # build the types table
        typedata = [ [None, self.settingsDirectory[i][2] ] for i in rows ] 
        # open dialog box
        model = settingsDataModel(self.settingsDirectory, data, typedata)
        self.dialog = settingsDialog('Settings', model, 'noacli settings')
        self.dialog.finished.connect(self.acceptOrReject)

    def copy2qtail(self):
        qs = QSettings()
        # copy qtail settings
        self.qtail.maxLines = int(qs.value('QTailMaxLines', self.qtail.maxLines))
        self.qtail.tailFrag = int(qs.value('QTailEndBytes', self.qtail.tailFrag))
        # QTailDefaultTitle: default title is set somewhere else XXX
        # XXX more qtail settings not implemented yet
        
    def acceptOrReject(self, result):
        print('settings: '+str(result))
        if result:
            qs = QSettings()
            for d in self.data:
                if d[1]!=None:
                    print('save '+str(d[0])+' = '+str(d[1])) # XXX
                    qs.setValue(d[0], d[1])
            self.copy2qtail()
            qs.sync()
        # destroy everything
        self.dialog = None
        self.data = None

class settingsDialog(QtWidgets.QDialog):
    def __init__(self, title, model, doc=None):
        super(settingsDialog,self).__init__()
        ui = Ui_settingsDialog()
        self.model = model
        # XXX proxy model?  search?
        self.ui = ui
        ui.setupUi(self)
        ui.tableView.setModel(model)
        self.setWindowTitle(title)
        if doc:
            ui.label.setText(doc)
        else:
            ui.label = setText(title)  # XX center?
        ui.tableView.resizeColumnsToContents()
        # XX resize top window too?
        self.show()

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

    @QtCore.pyqtSlot()
    def actionGsettings(self):
        self.settings.makeDialog()

    # slot to connect command window runCommand
    def runCommand(self, command, hist):
        if hist and isinstance(hist.model(),QtCore.QSortFilterProxyModel ):
            hist=hist.model().mapToSource(hist)
        self.resetHistorySort()  # XXX this might be annoying
        # XXX command is redundant? but external stuff calls us
        j = jobItem(hist)  # XX construct new job
        self.settings.jobs.newjob(j)
        j.start(self.settings)
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
        qs = QSettings()
        i = int(qs.value('HistMenuSize', 10))
        cmds=set()
        qs = QSettings()
        width = int(qs.value('HistMenuWidth',30))
        while i>0 and h:
            c = str(h.data())
            if c not in cmds:
                act = QAction(h.data()[0:width], self)
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
