#!/usr/bin/env python3

__license__   = 'GPL v3'
__copyright__ = '2022, 2023, Steven Dick <kg4ydw@gmail.com>'

# The No Ampersand CLI shell
#
# Do most things regular CLI shells do (except full parsing and turing
# complete programming), but in a graphical interface.  Take full
# advantage of having a GUI as much as possible, including common
# trivial data visualization stuff.
#
# See Readme.md for more documentation.

import os, sys, time
from pathlib import Path
from functools import partial
import signal

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.Qt import Qt, pyqtSignal
from PyQt5.QtGui import QTextCursor, QKeySequence,QTextOption, QClipboard, QFont
from PyQt5.QtWidgets import *
from PyQt5.QtCore import QIODevice, QModelIndex,QPersistentModelIndex, QSettings, QProcessEnvironment, QProcess

from lib.noacli_ui import Ui_noacli
from lib.typedqsettings import typedQSettings

from lib.datamodels import simpleTable, settingsDataModel, settingsDialog
from lib.noajobs import jobItem, jobTableModel, History
from lib.smalloutput import smallOutput
from qtail import myOptions as qtailSettings
from lib.commandparser import OutWin, commandParser
from lib.envdatamodel import envSettings
from lib.buttondock import ButtonDock, EditButtonDocks
from lib.favorites import Favorites

__version__ = '1.10.4'

# Some settings have been moved to relevant modules
class settingsDict():
    # key : [ default, tooltip, type ]
    settingsDirectory = {
    'DEBUG': [False, 'Enable debug prints', bool],
    # All uppercase are inherited(?) from bash
    'DefWinProfile':[True, 'Load the Default window profile at start', bool],
    'EditorFont':   [None, 'Font used for the editor and log windows', QFont],
    'FavFrequent':  [10, 'Number of frequently used commands automatically imported into favorites', int],
    'FavRecent':    [10, 'Number of recent history commands automaticaly imported into favorites', int],
    'FileDialogFilter': ['All files (*);; Python (*.py *.ui *.qrc);; Images (*.png *.xpm *.jpg *.pbm);;Text files (*.txt *.md);;Archives (*.zip *z)',
                    "Default File browser dialog (Ctrl-F) search groups if you don't supply a filter by selecting it", str],
  # 'GraphicalTerminal': ['gnome-shell', 'Graphical terminal used to run commands requiring a tty', str],
    'HISTSIZE':     [ 1000, 'Number of history entries kept in memory', int],
    'HISTFILESIZE': [ 1000, 'Number of history entries saved to disk', int ],
    'HistFile':     [ '.noacli_history', 'name of file to save history (full path or relative to home)', str],
  # 'HISTCONTROL':  ['', 'options: ignorespace ignoredups erasedups', str],
    'HistMenuSize': [ 10, 'number of unique recent history entries to show in the history pull down menu', int],
    'HistMenuWidth':[ 30, 'maximum width of commands listed in the history menu', int],
    'JobCleanTime': [120, 'interval in seconds to check for expired jobs', int ], # XX could be float
    'JobMenuWidth': [ 30, 'maximum width of commands listed in the job menu', int],
    'LogMaxLines':    [10000, 'maximum lines remembered in the log window', int],
    'LogBatchLines': [100, 'number of lines read in a batch for the log window.  Increasing this decreases shell responsiveness but makes logs read faster.', int],
    'MessageDelay':[10, 'Timeout (seconds) for transient message bar messages', float],
    'SettingsAutoSave':[300, 'Automatically save history and settings (seconds)',int],
    'SHELL':       [ 'bash -c', 'external shell wrapper command to run complex shell commands', str],
    'TemplateMark':['{}', 'Move cursor to this string after loading a command into the edit window', str],
    'SmallMultiplier': [2, 'Number of lines to keep in the small output window, <10 is screen multiples, >=10 is paragraphs, <1 for infinite', int],
    }

    def __init__(self):
        typedQSettings().registerOptions(self.settingsDirectory)

# initialize, load, hold, and save various global settings
class settings():
    def __init__(self):
        qs = typedQSettings()
        self.settingsDirectory = qs.setdict
        # create skelectons of settings and read previous or set defaults
        self.history = History()
        self.history.read()
        self.favorites = Favorites(self)
        self.commandParser = commandParser() # XXX load settings
        # don't call this before setting buttonbox, so call it in caller
        #self.favorites.loadSettings()

        self.environment = envSettings()

        self.jobs = jobTableModel()
        # job manager gets its own special class
        
        self.qtail = qtailSettings()
        self.copy2qtail()

    def generalSettingsContextMenu(self, point):
        t = self.dialog.ui.tableView
        index = t.indexAt(point)
        # XX and index is not default value
        if index.isValid():
            m = QMenu(self.dialog)
            # XXX value? already default?
            m.addAction("Reset to default", partial(self.resetGenSetting, index))
            action = m.exec(t.mapToGlobal(point))  # event.globalPos())

    def resetGenSetting(self, index):
        m = index.model()
        if index.row()!=1:
            index = m.index(index.row(),1)
        m.setData(index, index.data(Qt.ToolTipRole), Qt.EditRole)

    ## settings dialog info
    # name, default, tooltip / description
    # Note: defaults here might not match the real defaults embeeded in code
    # ETAGS: generalSettingsDialog
    def makeDialog(self, parent):
        # XX makeDialog should be generalSettingsDialog or something
        # collect list of rows including settings
        # build a list of settings, each source sorted separately
        rows = sorted(self.settingsDirectory.keys())
        # add additional settings from QSettings (missing from dict)
        qs = typedQSettings()
        qs.warnmissing = False  # don't warn on obsolete settings and mac noise
        rows += [i for i in sorted(qs.childKeys()) if i not in self.settingsDirectory]
        # get qtail defaults
        qt = {
            'QTailMaxLines': self.qtail.maxLines,
            'QTailEndBytes': self.qtail.tailFrag,
            'QTailDefaultTitle': 'subprocess',
            'QtailFormat': self.qtail.format,
            }
        # build settings table using rows
        # all qtail settings are already in docdict but values need to be merged
        data = []
        for name in rows: # this was just too messy to do in a comprehension
            val = qs.value(name,None)
            # get qtail current setting which might be default anyway
            if val==None and name in qt: val=qt.get(name)
            # fix types
            if name in self.settingsDirectory and val!=None:
                if self.settingsDirectory[name][2]==bool and type(val)==str:
                    val = val.lower() in ['true','yes']
                else:
                    try:
                        val = self.settingsDirectory[name][2](val)
                    except: # XX debug msg?
                        val = None
            # reset if default value
            if  val!=None and val==self.settingsDirectory[name][0]:
                val = None
            data.append([name, val ])
        self.data = data
        # build the types table
        typedata = [ [None, self.settingsDirectory[i][2] ] for i in rows ] 
        # open dialog box
        model = settingsDataModel(self.settingsDirectory, data, typedata)
        self.dialog = settingsDialog(parent, 'Settings', model, 'noacli settings')
        self.dialog.finished.connect(self.acceptOrReject)
        tv =  self.dialog.ui.tableView
        tv.setContextMenuPolicy(Qt.CustomContextMenu)
        tv.customContextMenuRequested.connect(self.generalSettingsContextMenu)

    def copy2qtail(self):
        qs = typedQSettings()
        # copy qtail settings
        self.qtail.maxLines = int(qs.value('QTailMaxLines', self.qtail.maxLines))
        self.qtail.tailFrag = int(qs.value('QTailEndBytes', self.qtail.tailFrag))
        # QTailDefaultTitle: default title is set somewhere else XX
        # XX more qtail settings not implemented yet
        
    def acceptchanges(self):
        #if typedQSettings().value('DEBUG',False):print('accept') # DEBUG
        qs = typedQSettings()
        for d in self.data:
            if d[1]!=None:
                #print('save '+str(d[0])+' = '+str(d[1])) # DEBUG
                qs.setValue(d[0], d[1])
        self.copy2qtail()
        # copy settings that have immediate effect to their widgets
        # most settings are retrieved dynamically, but a few are set in widgets
        # could convert the rest of these to connections
        self.logOutputView.applySettings()
        self.smallOutputView.applySettings()
        self.apply_settings.emit()
        # history size is reset when history is added? XX
        qs.sync()
        
    def acceptOrReject(self, result):
        if result: self.acceptchanges()
        #print('finished') # DEBUG
        # destroy everything
        self.dialog.setParent(None)
        self.dialog = None
        self.data = None

class  fontDelegate(QStyledItemDelegate):
    # All tested versions of Qt call setModelData when they think
    # editing is done, not when the font dialog is done.  This happens
    # even when the editing is rejected.  Some versions of Qt (5.12.8?)
    # call setModelData then fontSelected where later versions do the
    # reverse.  selectedFont is not valid before fontSelected is
    # called. So we set a flag at editor creation indicating if a
    # font is selected.  When setModelData is called, save state
    # variables, and set the font only if one has been selected.  When
    # one is selected, check if the state variables were set and use
    # them after the fact.  This fixes older qt never setting the
    # right font, and fixes newer qt setting the font to a default
    # system font when it was rejected.
    # 
    # Unclear if QStyledItemDelegate is buggy or just poorly documented,
    # or if this is a race condition and the order is coincidental.
    def __init__(self, parent):
        super().__init__(parent)
        self.fontselected = False
        self.originalfont = None

    def convertsetting(self, val):
        if type(val)==str:
            font = QFont()
            if font.fromString(val):
                return font
            else:
                #print("old convert") # DEBUG
                return QFont(val)
        elif val and val.family() and val.pointSize()>0:
            return val
        else:
            return None
        
    def createEditor(self,parent,option,index):
        self.fontselected = False
        font = self.convertsetting(index.model().data(index,Qt.EditRole))
        #print('create editor '+font.toString()) # DEBUG
        self.originalfont = None
        if font:
            self.originalfont = font # prob don't actually need to save this
            fd= QFontDialog(font, parent)
        else:
            #print('created with no font') # DEBUG
            fd = QFontDialog(parent)
        fd.fontSelected.connect(self.fixfontsel)
        self.fd = fd
        fd.open()
        return fd


    def fixfontsel(self, font):
        self.fontselected = True
        # this tries to cover up an error where setModelData
        # is called before fontSelected is generated and selectedFont set,
        # so the wrong font is used without this
        DEBUG = typedQSettings().value('DEBUG',False)
        if hasattr(self, 'lastmodel'):
            self.setModelData(self.fd, self.lastmodel, self.lastindex)

    def setModelData(self, editor, model, index):
        font = editor.selectedFont()
        # save these for later, when the font is actually selected
        self.lastmodel = model
        self.lastindex = index
        if not self.fontselected:
            return # too early! set later. Or never if canceled.
        if font:
            model.setData(index, font, Qt.EditRole)

# and register the result for later use
settingsDialog.registerType(QFont, fontDelegate)


class historyView(QTableView):
    newFavorite = pyqtSignal(str)
    delayedScroll = pyqtSignal(QModelIndex) # XXXX or QPersistentModelIndex

    def __init__(self, parent):
        super().__init__(parent)
        self.realModel = None
        self.historyProxy = QtCore.QSortFilterProxyModel()
        # mess with the history corner button
        cb = self.findChild(QtWidgets.QAbstractButton)
        if cb:
            cb.disconnect()
            cb.clicked.connect(partial(self.resetHistorySort,True))
        self.horizontalHeader().sectionDoubleClicked.connect(self.resizeHheader)
        self.verticalHeader().sectionDoubleClicked.connect(self.resizeVheader)
        self.delayedScroll.connect(self.doDelayedScroll, Qt.QueuedConnection)
        vh = self.verticalHeader()
        vh.customContextMenuRequested.connect(self.buildContextMenu)
        vh.setContextMenuPolicy(Qt.CustomContextMenu)

    def setModel(self,model):
        self.realModel = model
        self.historyProxy.setSourceModel(model)
        self.historyProxy.setFilterKeyColumn(1)
        super().setModel(self.historyProxy)
        # this is probably too soon
        # self.resizeColumnsToContents()  # XX this makes last column too wide
        self.resizeColumnToContents(0)  # just fix the first column

    def resetHistorySort(self, remember=True):
        if remember:
            # keep the selected line on screen if there is one
            selected = self.selectedIndexes()
            if len(selected)<1:
                selected=None
            else:
                selected = selected[0] # just the first (last?) one
            oldrow = self.rowAt(10)
            hp = self.historyProxy
            row = hp.mapToSource(hp.index(oldrow,0)).row()
            #print('oldrow={}={}'.format(oldrow,row)) # DEBUG
        self.historyProxy.sort(-1)
        self.horizontalHeader().setSortIndicator(-1,0)
        self.adjustSize()
        # squeeze the last column
        hh = self.horizontalHeader()
        width = self.parent().width()-50 # XX arbitrary 50
        left = hh.sectionSize(0)
        #print("resize: w={} l={} old={} parent={}".format(width, left, hh.sectionSize(1), self.parent().width())) # DEBUG
        hh.resizeSection(1, width-left)
        
        #print('sort bottom') # DEBUG
        # self.scrollToBottom()  # this doesn't work due to a conflict
        #self.delayedScroll.emit(-1)
        if remember:
            if selected:
                self.delayedScroll.emit(selected)
            else:
                i=hp.index(row,0)
                self.delayedScroll.emit(i)
        else:
            self.delayedScroll.emit(QModelIndex()) # XX always scroll to bottom?

    def deleteOne(self, index):
        index.model().removeRow(index.row(), QModelIndex())

    def deleteSelected(self):
        # XX reuse this somehow?
        indexes = self.selectionModel().selectedRows()
        if not indexes:
            QErrorMessage(self).showMessage("Please select at least one whole row to delete selected rows")
            return
        #print("Deleting "+str(len(indexes))+'/'+str(len(self.realModel.data))) # DEBUG
        while indexes:  # XX delete ranges for higher efficency?
            i = indexes.pop()
            i.model().removeRow(i.row(), QModelIndex())
        #print(" deleted, left "+str(len(self.realModel.data))) # DEBUG
        

    def addFav(self, index):
        m = index.model()
        cmd = m.data(m.index(index.row(),1))
        self.newFavorite.emit(cmd)
    
    def contextMenuEvent(self, event):
        self.buildContextMenu(event.pos())
        
    def buildContextMenu(self, point):
        m = QMenu(self)
        # XXX disable or omit inappropriate actions in this menu
        index = self.indexAt(point)
        m.addAction("Add to favorites",partial(self.addFav, index)) # already there?
        m.addAction("Delete",partial(self.deleteOne, index))
        m.addAction("Delete selected rows",self.deleteSelected) # not a row?
        m.addAction("Collapse duplicates",self.realModel.collapseDups)
        m.addAction("Delete earlier duplicates",self.realModel.deletePrevDups)
        m.addAction("Resize rows vertically", self.resizeRowsToContents)
        m.addAction("Scroll to top", self.scrollToTop)
        m.addAction("Scroll to bottom", self.scrollToBottom)

        action = m.exec(self.mapToGlobal(point))  # event.globalPos())
        #print(action) # DEBUG

    def resizeVheader(self, logical):
        self.ui.tableView.resizeRowToContents(logical)

    def resetView(self, index=None):
        #print('start {},{}'.format(index.row(),index.column())) # DEBUG resetView
        row = None
        # XXX if index is invalid, should remember the current position instead
        # get the native row and rebuild the index later
        if index:
            if type(index)==QPersistentModelIndex or type(index.model())==History:
                row = index.row()
                # i = self.historyProxy.mapFromSource(index)
            else:
                row = self.historyProxy.mapToSource(index).row()
        # else scroll to bottom
        self.resetHistorySort(False)
        ## now base model and proxy model indexes are the same
        # print('new {},{}'.format(i.row(),i.column())) # DEBUG resetView
        if row:
            # build a fresh index
            i = self.model().index(row,0)
            if i.isValid():
                self.delayedScroll.emit(i)
        elif index and index.isValid():
            if type(index)==QModelIndex:
                # XXXXXX convert from QPersistentModelIndex sometimes??
                self.delayedScroll.emit(index)
        else:
            #self.scrollToBottom()
            #print('bottom') # DEBUG
            self.delayedScroll.emit(None)
       
    def doDelayedScroll(self, index):
        if index and index.isValid():
            self.scrollTo(index, 1)
        else:
            self.scrollToBottom()

    def resizeHheader(self, logical):
        self.resizeColumnToContents(logical)
    def resizeVheader(self, logical):
        self.resizeRowToContents(logical)



# thanks to https://stackoverflow.com/questions/18475870/qt-menu-with-qlinedit-action (gct)
# insert this into a menu
class menuLineEdit(QLineEdit):
    # note: use placeholder instead of contents!
    def __init__(self, parent, placeholder):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setClearButtonEnabled(True)
    @QtCore.pyqtSlot('QKeyEvent')
    def keyPressEvent(self,event):
        if event.key() in [Qt.Key_Enter, Qt.Key_Return]:
            self.returnPressed.emit()
        else:
            super().keyPressEvent(event)
    def textAndClear(self):
        t = self.text()
        self.clear()
        return t
            
class noacli(QtWidgets.QMainWindow):
    want_restore_geo_delay = pyqtSignal(str)
    apply_settings = pyqtSignal()
    def __init__(self, app):
        settingsDict()   # do this very early
        super().__init__()
        self.ui = Ui_noacli()
        self.ui.setupUi(self)
        self.ui.buttons = ButtonDock(self, 'Buttons') # make default button dock
        ButtonDock.run_command.connect(self.doButton)

        self.dontCloseYet = True
        
        # delayed resize works better
        self.want_restore_geo_delay.connect(self.restore_geo, Qt.QueuedConnection) # delay this

        self.settings = settings()
        # cheat a bit, so nearly everyone can get to these
        self.settings.apply_settings = self.apply_settings
        self.settings.apply_settings.connect(self.applyEditorFont)
        self.settings.app = app # XX redundant
        self.settings.smallOutputView = self.ui.smallOutputView
        self.settings.statusBar = self.statusBar()
        self.settings.mainwin = self

        self.historypos = 1;
        dir = os.path.dirname(os.path.realpath(__file__))
        p =  os.path.join(dir,'icons', 'noacli.png')
        icon = QtGui.QIcon(p)
        if icon.isNull() or len(icon.availableSizes())<1: # try again
            if typedQSettings().value('DEBUG',False):print('icon {} failed trying again'.format(p)) # DEBUG
            icon = QtGui.QIcon('noacli.png')
        self.setWindowIcon(icon)
        app.setWindowIcon(icon)  # we really want this icon!

        # hide all the docks by default (save a profile if you don't like it)
        ui=self.ui

        self.tabifyAll()
        # most obvious UI for new users is for all docks to be shown
        #self.hideAllDocks()  # if you want this, save a profile

        ui.actionTabifyDocks.triggered.connect(self.tabifyAll)

        # must load button dock settings before favorites or all
        # buttons get reinserted into default dock
        ButtonDock.loadSettings()
        # connect buttons to favorites
        self.settings.favorites.setFunctors( [ self.runSimpleCommand, self.ui.commandEdit.acceptCommand])
        self.settings.favorites.loadSettings()

        self.settings.logOutputView = self.ui.logBrowser

        # populate the view menu for DOCK (is there a more automatic way?)
        ui.menuViews.addAction(ui.history.toggleViewAction())
        ui.menuViews.addAction(ui.jobManager.toggleViewAction())
        ui.menuViews.addAction(ui.buttons.toggleViewAction())
        ui.menuViews.addAction(ui.smallOutputDock.toggleViewAction())
        ui.menuViews.addAction(ui.logDock.toggleViewAction())

        # attach the data models to the views
        ui.historyView.setModel(self.settings.history)
        ui.historySearch.textChanged['QString'].connect(ui.historyView.historyProxy.setFilterFixedString)

        # make all the tables fit
        ui.jobTableView.resizeColumnsToContents()

        # connect the command editor to the history data model
        # XX this should be a connect historySave->saveItem
        ui.commandEdit.setHistory(self.settings.history)

        ui.jobTableView.setModel(self.settings.jobs)
        ui.jobManager.keeplines = True
        self.settings.jobs.rowsInserted.connect(self.jobsChanged)
        self.settings.jobs.rowsRemoved.connect(self.jobsChanged)

        # mess with job manager corner button (is this even visible?)
        cb = ui.jobTableView.findChild(QtWidgets.QAbstractButton)
        if cb:
            cb.disconnect()
            cb.clicked.connect(self.settings.jobs.cleanup)

        self.ui.jobTableView.horizontalHeader().sectionDoubleClicked.connect(self.resizeJobHheader)
        self.ui.jobTableView.verticalHeader().sectionDoubleClicked.connect(self.resizeJobVheader)


        # build history context menu
        self.ui.historyMenu.aboutToShow.connect(self.buildHistoryMenu)
        self.ui.menuJobs.aboutToShow.connect(self.buildJobMenu)

        self.ui.historyView.scrollToBottom()
        self.ui.actionFavorites_editor.triggered.connect(partial(self.settings.favorites.editFavorites, self))

        # file browser shortcut
        self.fileShortcut = QShortcut(QKeySequence('ctrl+f'), self)
        self.fileShortcut.activated.connect(self.pickFile)

        # jump to command editor XXX can this be made more global?
        self.editorShortcut = QShortcut(QKeySequence('alt+c'), self)
        self.editorShortcut.activated.connect(self.ui.commandEdit.setFocus)
        self.editorShortcut.setContext(Qt.ApplicationShortcut) # XX doesn't work?

        self.ui.smallOutputView.oneLine.connect(self.showMessage)
        self.ui.smallOutputView.newJobStart.connect(self.statusBar().clearMessage)
        self.ui.jobTableView.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.jobTableView.customContextMenuRequested.connect(self.jobcontextmenu)
        
        ##### geometry profiles
        qs = typedQSettings()
        v = qs.value('DefWinProfile', True)
        if v:
            # load default config
            self.myRestoreGeometry()
        ## fix up the menu
        m = ui.menuSettings
        # Add a lineEdit to create new profiles
        le = menuLineEdit(m, "(New geometry profile)")
        le.returnPressed.connect(lambda: self.mySaveGeometry(le.textAndClear()))
        wa = QWidgetAction(m)
        wa.setDefaultWidget(le)
        m.addAction(wa)
        # browse QSettings to add a list of profiles
        qs = QSettings()
        qs.beginGroup('Geometry')
        g = qs.childGroups()
        #print('Profiles: '+str(g)) # DEBUG
        gm = QActionGroup(m)
        self.ui.profileMenuGroup = gm
        for p in g:
            mm = gm.addAction(p)
            mm.setData(p)
            mm.setObjectName(p)
            #redundant and wrong# mm.triggered.connect(lambda: self.myRestoreGeometry(p))
            mm.setCheckable(True)
            if p=='default': mm.setChecked(True)
            m.addAction(mm)
        gm.triggered.connect(self.actionRestoreGeomAct)
        qs.endGroup()

        self.showMessage('Version '+__version__)
        self.ui.smallOutputView.append('Version '+__version__+"\n")
        # connect slots QtCreator coudln't find
        self.ui.smallOutputView.buttonState.connect(self.ui.logOutputButton.setEnabled)
        self.ui.smallOutputView.buttonState.connect(self.setTerminateButton)
        # commandParser is not a Qt object, so we do it our own way
        self.settings.commandParser.new_default_wrapper = self.setTitleFromWrap

        self.applyEditorFont()  # do this again after everything is set up

        self.autoSaveTimer = QtCore.QTimer()
        self.autoSaveTimer.timeout.connect(self.autoSaveAll)
        self.setAutoSave()
        self.settings.apply_settings.connect(self.setAutoSave)

        ##### install signal handlers XXX
        #try:  # in case anything here is unportable
        #    signal.signal(signal.SIGINT, self.ouch)
        #    #X this is for output# signal.signal(signal.SIGTSTP, self.tstp)
        #    signal.signal(signal.SIGTTIN, self.terminalstop) # didn't work
        #    #signal.signal(signal.SIGTTIN, signal.SIG_IGN) # didn't work
        #except Exception as e:
        #    # XX ignore failed signal handler installs
        #    print("Not all signal handlers installed"+str(e)) # EXCEPT
        #    pass

    ## end __init__


    def jobsChanged(self, idx, first, last):
        # receive jobs(model).rows{Inserted,Removed}
        self.ui.jobManager.resetLines(self.settings.jobs.rowCount(None))

    def doButton(self, name):
        if name=='Run':
            self.ui.commandEdit.runCommand()
        elif name=='Rerun last':
            self.runLastCommand()
        # XX add more simple buttons later?

    def setTitleFromWrap(self, title):
        self.setWindowTitle('noacli: '+title)
    
    ## small output UI actions
    def rebuttonKill(self, label, slot, enab=True):
        self.ui.killButton.setText(label)
        self.ui.killButton.setEnabled(enab)
        self.ui.killButton.disconnect()
        self.ui.killButton.clicked.connect(slot)

    def terminateButton(self):
        self.ui.smallOutputView.smallTerminate()
        self.rebuttonKill('Kill harder',self.ui.smallOutputView.smallKill)
    
    def setTerminateButton(self,enab):
        self.rebuttonKill('Kill',self.terminateButton,enab)

    ####
    
    def terminalstop(self, sig, stack):
        print("Terminal stop blocked!") # EXCEPT
        self.showMessage("Terminal stop blocked!")
        # do something about the offending child process??
        
    def ouch(self, sig, stack):
        print('Ouch!') # EXCEPT
        # ignore a signal


    def tabifyAll(self):
        # convert all the DOCKs to tabs
        if self.ui.buttons.isFloating(): self.ui.buttons.setFloating(False)
        self.ui.jobManager.setFloating(False)
        self.ui.history.setFloating(False)
        self.ui.smallOutputDock.setFloating(False)
        self.tabifyDockWidget( self.ui.jobManager, self.ui.history)
        self.tabifyDockWidget( self.ui.history,   self.ui.logDock)
        self.tabifyDockWidget( self.ui.logDock, self.ui.smallOutputDock)
        self.tabifyDockWidget( self.ui.smallOutputDock, self.ui.buttons)
        ButtonDock.tabifyAll(self, self.ui.buttons)

    def start(self):
        # nothing else to initialize yet
        pass

    def pickFile(self):
        pattern = typedQSettings().value('FileDialogFilter',None)
        editor = self.ui.commandEdit
        quote = None

        cursor = editor.textCursor()
        if cursor.hasSelection():
            pattern = cursor.selectedText()
        
        # avoid the default constructor
        # results = QFileDialog.getOpenFileNames(None, "Pick some files", ".", pattern)
        #fs = results[0]
        # parent: Attaches dialog to the parent window and covers it (ick!) 
        # other defaults need customizing, default constructor not flexible enough
        # also make it non-modal

        fd = QFileDialog(self, Qt.Dialog)
        #fd.setWindowFlag(Qt.WindowStaysOnTopHint, True) # prevent modal from getting lost -- doesn't seem to help, prob redundant
        #fd.setOption(QFileDialog.DontUseNativeDialog)

        # check if user was trying to complete a partially typed path
        c = editor.textCursor() # get a fresh cursor
        c.clearSelection()
        c.movePosition(QTextCursor.StartOfWord, QTextCursor.KeepAnchor)
        while (c.positionInBlock()>0):
            d = QTextCursor(c) # don't mess with previous one yet
            d.movePosition(QTextCursor.PreviousCharacter,QTextCursor.KeepAnchor)
            ch = d.selectedText()[0]
            if not ch.isprintable() or ch.isspace(): break
            c=d
            c.movePosition(QTextCursor.StartOfWord, QTextCursor.KeepAnchor)

        # XXX possibly non-portable path construction
        cwd = os.getcwd()+'/'
        startdir = c.selectedText()
        if len(startdir)>0 and startdir[0] in '\'"': # quote all the filenames
            quote = startdir[0]
            startdir=startdir[1:]
            #print('new start: '+startdir) # DEBUG
        #print("dir="+startdir) # DEBUG
        if startdir=='*':
            startdir = None  # cancel!
            cwd = ''
            c.removeSelectedText()
        if not cursor.hasSelection() and not os.path.isdir(startdir):
            # maybe user didn't highlight trailing pattern?
            (dir,tail) = os.path.split(startdir)
            # XXX this breaks slighlty if it doesn't have a directory prefix
            if os.path.isdir(dir): # put back just the dirctory piece
                c.removeSelectedText()
                c.insertText(dir)
                startdir=dir
                # and use the remainder as a wildcard pattern
                if '*' not in tail:  # XX maybe this was suppose to be a prefix?
                    tail+='*' 
                pattern=tail + ';;' + pattern
        if startdir:
            # XX if startdir doesn't exist or has junk at the end, it may be partially ignored and then the prefix removal code below is funky
            fd.setDirectory(startdir)
        else:
            fd.setDirectory('.') # otherwise it remembers the previous dir
        
        #default# fd.setFileMode(QFileDialog.AnyFile) # Directory
        ## the following seems restrictive, but it's the only alternatives
        if pattern[0]=='/':
            if pattern=='/': pattern=None
            fd.setFileMode(QFileDialog.Directory) # select single directory
        else:
            fd.setFileMode(QFileDialog.ExistingFiles) # select multiple files

        fd.setNameFilter(pattern)
        # setLabelText
        # DontConfirmOverwrite
        # viewmode def:Detail/List

        if fd.exec():  # XXX icky modal
            fs = fd.selectedFiles()
        else:
            fs = None
        fd.setParent(None) # destroy
        fd=None

        #print(str(fs)) # DEBUG
        #print(cwd) # DEBUG
        if fs:  # do nothing if nothing selected
            if hasattr(fs,'removeprefix'):
                # python 3.9 feature
                fs = [x.removeprefix(cwd) or x for x in fs]
                # remove startdir from first entry only
                if startdir:
                    if fs[0].startswith(startdir):
                        fs[0] = fs[0].removeprefix(startdir)
                    else:
                        c.insertText(' ') # if prefix doesn't match, add space
            else:
                ## python 3.8 and earlier XXRemove this some day
                fsn = []
                for i in fs:
                    if i.startswith(cwd):
                        fsn.append(i[len(cwd):])
                    else:
                        fsn.append(i)
                if fsn[0].startswith(startdir):
                    fsn[0] = fsn[0][len(startdir):]
                else:
                    c.insertText(' ') # if prefix doesn't match, add space
                fs=fsn
            if quote: # quote all the filenames
                fs = [ quote + f + quote for f in fs]
                # except the first one
                fs[0] = fs[0][1:]

            ## and return the results to the editor
            f = ' '.join(fs)+' '  # leave a trailing space after filename
            editor.insertPlainText(f)
        
    ################
    # external slots
    # some of these could be moved

    # I hate modal dialog boxes.  Rather do this the hard way,
    # and get live font changes too!
    
    @QtCore.pyqtSlot()
    def pickDefaultFont(self):
        startfont = self.ui.commandEdit.document().defaultFont()
        fd = QFontDialog(startfont, None)
        fd.currentFontChanged.connect(self.liveFont)
        fd.rejected.connect(partial(self.liveFont,startfont) )
        fd.accepted.connect(self.acceptedFont)
        fd.finished.connect(self.doneFont)
        fd.setWindowTitle("Select editor font")
        fd.setCurrentFont(startfont)
        self.fontdialog = fd
        fd.open()
     
    def liveFont(self, font):
        if font: # just change one
            self.ui.commandEdit.document().setDefaultFont(font)
    def acceptedFont(self):
        # grab the font from the command window and copy
        ui = self.ui
        font = ui.commandEdit.document().defaultFont()
        QSettings().setValue('EditorFont', font)  # XX .toString())
        self.applyEditorFont()

    def applyEditorFont(self):
        # print('set font') # DEBUG
        font = typedQSettings().value('EditorFont', None)
        if font and font.family() and font.pointSize()>0:
            self.ui.commandEdit.document().setDefaultFont(font)
            self.ui.smallOutputView.document().setDefaultFont(font)
            self.ui.logBrowser.document().setDefaultFont(font)

    def doneFont(self):
        # tear it down
        self.fontdialog.deleteLater()  # possibly still delivering signals
        self.fontdialog = None
    
    @QtCore.pyqtSlot()
    def syncSettings(self):
        qs = QSettings()
        qs.sync() # XX is this necessary?
        # XXX maybe this should call various apply settings?
        # emit apply settings?
        self.settings.commandParser.applySettings()

    # in: whoever  out: favorites
    @QtCore.pyqtSlot(str)
    def addFavorite(self, cmd):
        self.settings.favorites.addFavorite(cmd)

    # in: jobView/JobModel  out: jobModel commandEditor
    @QtCore.pyqtSlot(QModelIndex)
    def jobDoubleClicked(self, index):
        if not index.isValid(): return
        col = index.column()
        if col==0:
            text = str(index.model().getItem(index).getpid())
            self.app.clipboard().setText(text)
            self.app.clipboard().setText(text, QClipboard.Selection)
        elif col==1: index.model().cleanupJob(index)  # job status
        elif col==2 or col==3: self.windowShowRaise(index)
        elif col==4: self.ui.commandEdit.acceptCommand(index.model().getItem(index).command())

    # in: jobView out: jobModel
    def windowShowRaise(self,index):
        if isinstance(index, QAction): index = index.data() # unwrap
        job = index.model().getItem(index)
        if job.window:
            job.windowOpen = True
            job.window.show()
            # also try moving the mouse to the window
            QtGui.QCursor().setPos(job.window.pos()+QtCore.QPoint(100,100))
            job.window.raise_()
            job.window.activateWindow()
            # XX maybe blink the mouse too?


    # in: view menu  out: all DOCKs
    @QtCore.pyqtSlot()
    def showAllDocks(self):
        ui = self.ui
        ui.history.setVisible(True)
        ui.buttons.setVisible(True)
        ui.jobManager.setVisible(True)
        ui.smallOutputDock.setVisible(True)
        ui.logDock.setVisible(True)
        # it's not enough to make these visible, need to show them too
        # OS window manager can close the window
        ui.history.show()
        ui.buttons.show()
        ui.jobManager.show()
        ui.smallOutputDock.show()
        ui.logDock.show()
        ButtonDock.setAllVisibility(True)

    @QtCore.pyqtSlot()
    def hideAllDocks(self):
        ui = self.ui
        ui.history.setVisible(False)
        ui.buttons.setVisible(False)
        ui.jobManager.setVisible(False)
        ui.smallOutputDock.setVisible(False)
        ui.logDock.setVisible(False)
        ButtonDock.setAllVisibility(False)


    # in: commandEditor runCurrent(button)
    # push button signal
    @QtCore.pyqtSlot()
    def runLastCommand(self):
        last = self.settings.history.last()
        self.runCommand(None,last)

    # in: view menu  out: general settings dialog
    @QtCore.pyqtSlot()
    def actionGsettings(self):
        self.settings.makeDialog(self)
    @QtCore.pyqtSlot()
    def actionEsettings(self):
        self.settings.environment.envDialog(self)

    @QtCore.pyqtSlot(str)
    def runSimpleCommand(self, cmd, title):
        self.runCommand(cmd,None,title)

    def showReadme(self):
        # make a fake job and use qtail to display our own readme
        j=jobItem(None)
        j.setTitle('Readme.md')
        j.setMode('QTail')
        # find our readme
        dir = os.path.dirname(os.path.realpath(__file__))
        p =  os.path.join(dir, 'documentation', 'Readme.md') # XX test path?
        j.outwinArgs = ['--url', '--findall=^=+']
        self.settings.jobs.newjob(j)
        j.startOutwin(p,self.settings)
        # XX clean up on fail?

    # in: self.runLast, commandEdit->command_to_run, QShortcuts
    # out: historyView, jobModel, jobTableView
    # slot to connect command window runCommand
    def runCommand(self, command, hist, title=None):
        histbase = hist
        if not hist and command:
            # make a new history entry!
            histbase = self.settings.history.saveItem(command, None, None)
            hist = QPersistentModelIndex(histbase)
        else: # make sure we have a histbase to play with to record status
            if type(hist)==QPersistentModelIndex:
                histbase = QModelIndex(hist)
            if type(histbase.model())==QtCore.QSortFilterProxyModel:
                histbase = histbase.model().mapToSource(histbase)
        if hist and not command: # extract command from history
            command = History.GetCommand(hist)
        if not command:
            return  # still no command!  Don't set status.
        self.ui.historyView.resetHistorySort(False) # likely invalidates QModelIndex
        cmdargs = self.settings.commandParser.parseCommand(command)
        #print("parsed: {} = {}".format(type(cmdargs),cmdargs)) # DEBUG
        if cmdargs==None:
            return # nothing was done, don't set status
        if type(cmdargs)==int: # pass/fail without message
            histbase.model().setStatus(histbase, cmdargs)
            return
        elif type(cmdargs)==str or len(cmdargs)==2:
            if len(cmdargs)==2:
                (msg, estatus) = cmdargs
            else:
                msg = cmdargs
                estatus = 'ok'  # did it pass or fail?
            self.ui.smallOutputView.internalOutput(self.settings,msg+"\n")
            histbase.model().setStatus(histbase, estatus)
            return
        outwinArgs = None
        if len(cmdargs)==4:
            outwinArgs = cmdargs.pop(2)
        # ok, we have a window to open, could be internal or external
        (title,outwin,args) = cmdargs
        if outwinArgs and ('--files' in outwinArgs or '--file' in outwinArgs):
            # handle internal qtail and tableview
            if not title: title=''
            if type(args)==str: args=[args]  # --file
            for f in args:
                j = jobItem(None)
                # XXX should elide title and make a history entry or something
                fn = f
                if len(fn)>30:
                    fn = os.path.basename(fn) # try shortening it
                if (title):
                    j.setTitle(title+' '+fn)
                else:
                    j.setTitle(fn)
                j.setMode(outwin)
                j.outwinArgs = outwinArgs
                j.history = hist # set it late XXX use the same hist entry??
                self.settings.jobs.newjob(j)
                try:
                    j.startOutwin(f, self.settings)
                except Exception as e:
                    msg = '{}: {}'.format(f,e)
                    self.ui.smallOutputView.internalOutput(self.settings,msg+'\n')
                    self.showMessage(msg) # XX this should be redundant but isn't
                    j.setStatus('Fail',-1)
                    j.finished = True
                    j.window = None
                else:
                    j.setStatus('OK',0)
        else: # external command
            j = jobItem(hist)  # XX construct new hist instead of reusing
            j.setMode(outwin)
            j.outwinArgs = outwinArgs
            j.args = args
            # print("parse mode: "+str(outwin)) #DEBUG
            if title and len(title)>0:
                j.setTitle(title)
            self.settings.jobs.newjob(j)
            j.start(self.settings)
            # XX try to fix job table size every time?
            self.ui.jobTableView.resizeColumnsToContents()
            self.ui.historyView.resetView(hist)

    # in: history menu->save
    def actionSaveHistory(self):
        self.settings.history.write()

    # dynamic portion of history menu
    @QtCore.pyqtSlot()
    def buildHistoryMenu(self):
        hm = self.ui.historyMenu
        # first destroy old entries
        for a in hm.actions():
            if a.data():
                hm.removeAction(a)
                a.setParent(None)
        # add new entries
        h = self.settings.history.last()
        qs = typedQSettings()
        i = int(qs.value('HistMenuSize', 10))
        cmds=set()
        width = int(qs.value('HistMenuWidth',30))
        while i>0 and h and h.data():
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
        self.ui.commandEdit.acceptHistory(act.data())

    # in: menuJobs->aboutToShow
    @QtCore.pyqtSlot()
    def buildJobMenu(self):
        jm = self.ui.menuJobs
        jm.clear()
        if self.settings.jobs.isEmpty():
            jm.addAction('No jobs left')
            return
        # XX threshold for too many jobs in this menu
        # XX if there's too many, how do we filter?
        # XX active jobs or all jobs?
        jobs = self.settings.jobs
        for j in jobs:
            s = str(j.model().getItem(j))
            act = QAction(s,  self)
            act.setData(j)
            jm.addAction(act)
            act.triggered.connect(partial(self.windowShowRaise,act))

    @QtCore.pyqtSlot()
    def actionSaveGeometry(self):
        a = self.ui.profileMenuGroup.checkedAction()
        if a:
            n = a.data()
            #print('Current profile: '+n) # DEBUG
        else:
            n = 'default'
        self.mySaveGeometry(n)
        
    def mySaveGeometry(self,name='default' ):
        #print("Saving profile "+name) # DEBUG
        qs = QSettings()
        qs.beginGroup('Geometry/'+name)
        qs.setValue('mainGeo', self.saveGeometry())
        qs.setValue('mainState', self.saveState())
        qs.endGroup()
        # check if this is already in the menu, and if not, add it
        gm = self.ui.profileMenuGroup
        c = gm.findChild(QAction, name)
        if c:
            #print(' already in menu') # DEBUG
            pass
        else:
            #print(' adding {} to profile menu'.format(name)) # DEBUG
            mm = gm.addAction(name)
            mm.setData(name)
            mm.setObjectName(name)
            mm.setCheckable(True)
            mm.setChecked(True)
            self.ui.menuSettings.addAction(mm)

    def myDeleteProfile(self):
        a = self.ui.profileMenuGroup.checkedAction()
        if a:
            name = a.data()
            self.showMessage('Deleting profile '+name)
        else:
            self.showMessage('Cant delete unselected profile')
            return
        # delete menu entry
        gm = self.ui.profileMenuGroup
        c = gm.findChild(QAction, name)
        gm.removeAction(c)
        # delete settings
        qs = QSettings()
        qs.beginGroup('Geometry')
        qs.remove(name)
        
    
    @QtCore.pyqtSlot(QAction)
    def actionRestoreGeomAct(self, act):
        # checkedAction()
        n = act.data()
        #print("action: "+n) # DEBUG
        if n: self.myRestoreGeometry(n)

    @QtCore.pyqtSlot()
    def actionRestoreGeometry(self):
        act = self.ui.profileMenuGroup.checkedAction()
        if act:
            self.actionRestoreGeomAct(act)
        else:
            self.myRestoreGeometry()

    def myRestoreGeometry(self, name='default'):
        self.restore_geo(name)
        # and do it again delayed but not recursive
        self.want_restore_geo_delay.emit(name)

    @QtCore.pyqtSlot(str)
    def restore_geo(self, name):
        # non-recursive version
        #print("Restoring profile "+name) # DEBUG
        qs = QSettings()
        qs.beginGroup('Geometry/'+name)
        if qs.contains('mainGeo'):
            self.restoreGeometry(qs.value('mainGeo',None))
            self.restoreState(qs.value('mainState',None))
            self.restoreGeometry(qs.value('mainGeo',None))
        else:
            #if typedQSettings().value('DEBUG',False):print('No profile for {} found'.format(name)) # DEBUG EXCEPTION this can't happen
            pass
        qs.endGroup()


    @QtCore.pyqtSlot(str)
    def showMessage(self, msg):
        qs = typedQSettings()
        delay = qs.value('MessageDelay',10)
        # append short messages!
        if (len(msg)<10): # arbitrary SETTING?
            msg = self.statusBar().currentMessage()+' | ' + msg
        self.statusBar().showMessage(msg, int(delay*1000))

    # in: this window closing
    def closeEvent(self, event):
        self.settings.jobs.cleanup()  # clean up dead stuff
        if self.dontCloseYet: # use this if not modal
            (wins, procs) = self.settings.jobs.hasJobsLeft() # XXX
            if wins or procs:  # Handle these before shutting down
                dialog = QMessageBox()
                bcan = dialog.addButton(QMessageBox.Cancel)
                bcan.setToolTip("Don't close noacli")
                bign = dialog.addButton(QMessageBox.Ignore)
                bign.setToolTip("Ignore these and close anyway")
                if wins:
                     bcloseWin = dialog.addButton("Close windows",QMessageBox.ActionRole)
                     bcloseWin.setToolTip("Close remaining open windows now")
                     bcloseWin.clicked.disconnect() # don't close dialog
                     bcloseWin.clicked.connect(self.settings.jobs.closeAllWins)  # and delete button?
                     bcloseWin.clicked.connect(partial(self.recheckClose, dialog, bcloseWin, None))
                if procs:
                    bkillProc = dialog.addButton("Kill processes",QMessageBox.ActionRole)
                    bkillProc.setToolTip("Kill remaining processes now")
                    bkillProc.clicked.disconnect()
                    self.firstKill = True
                    bkillProc.clicked.connect(partial(self.delaycheck, dialog,bkillProc))
                dialog.setDefaultButton(QMessageBox.Cancel)
                self.recheckClose(dialog) # set message
                #dialog.setInformativeText(msg)
                #dialog.setModality(Qt.NonModal)
                dialog.setWindowTitle("Quit noacli?")
                result = dialog.exec()
                if result == QMessageBox.Cancel:
                    event.ignore()
                    return
                elif result == QMessageBox.Ignore:
                    self.settings.jobs.ignoreJobsOnExit()
                    # move along and close
                    self.dontCloseYet = False
                #else: print(result) # EXCEPT DEBUG
        # really closing this time
        self.actionSaveHistory()
        self.settings.favorites.saveSettings()
        super().closeEvent(event)

    @QtCore.pyqtSlot()
    def autoSaveAll(self):
        if self.settings.history.modified:
            self.actionSaveHistory()
        # favorites should save on change now
    def setAutoSave(self):
        delay = typedQSettings().value('SettingsAutoSave',300)
        if delay:
            self.autoSaveTimer.start(delay*1000)
        

    def delaycheck(self,  dialog, button):
        if self.firstKill:
            self.firstKill = False
            self.settings.jobs.killAllProcs(False)
            button.setText("Kill harder") # XX
        else:
            self.settings.jobs.killAllProcs(True)
            button.hide() # possibly premature but what else to do
        self.delaytimer = QtCore.QTimer.singleShot(500, partial(self.recheckClose, dialog, None, button))

    def recheckClose(self, dialog, winbutton=None, procbutton=None):
        (wins, procs) = self.settings.jobs.hasJobsLeft() # XXX
        if not wins and winbutton: winbutton.hide()
        if not procs and procbutton: procbutton.hide()
        msg = 'There are still '
        if wins: msg += "{} windows open".format(wins)
        if wins and procs: msg += " and "
        if procs: msg += "{} processes running".format(procs)
        dialog.setText(msg)
        if not wins and not procs:
            # click ignore which will do the right thing anyway
            dialog.button(QMessageBox.Ignore).click()
        return wins or procs
                                              
    #### job manager fuctions (since it doesn't have its own class)
    def jobSqueezeRows(self):
        jobView = self.ui.jobTableView
        jobVH = jobView.verticalHeader()
        minsize = jobVH.minimumSectionSize()
        jobVH.setDefaultSectionSize(minsize)
        self.jobResizeRows(minsize)
    def jobRelaxRows(self):
        jobView = self.ui.jobTableView
        jobVH = jobView.verticalHeader()
        jobVH.resetDefaultSectionSize()
        self.jobResizeRows(jobVH.defaultSectionSize())
    def jobResizeRows(self,newsize):
        jobView = self.ui.jobTableView
        jobVH = jobView.verticalHeader()
        for i in range(jobVH.length()):
            jobVH.resizeSection(i,newsize)
    @QtCore.pyqtSlot('QPoint')
    def jobcontextmenu(self, point):
        jobView = self.ui.jobTableView
        index = jobView.indexAt(point)
        ## apparently QTableView doesn't have a standard context menu
        #m = jobView.createStandardContextMenu(point)
        m = QMenu()
        m.addAction("Fit rows vertically", jobView.resizeRowsToContents)
        m.addAction("Squeeze rows vertically", self.jobSqueezeRows)
        m.addAction("Relax rows vertically", self.jobRelaxRows)
        # XX jobcontext: convert to log / qtail window
        # XX jobcontext: job info
        job = None
        if index.isValid():
            job = index.model().getItem(index)
        if job:
            if job.process and job.process.state()!=QProcess.NotRunning:
                m.addAction("Terminate "+job.title(), job.process.terminate)
                m.addAction("Kill "+job.title(), job.process.kill)
            elif not job.windowOpen:
                m.addAction("clean dead: "+job.title(), partial(index.model().cleanupJob,index))
            if job.window: 
                m.addAction("Find window", partial(self.windowShowRaise,index))
            if job.window and job.windowOpen:
                m.addAction("Close window",job.window.close)
            ## add empty status items
            if job.process and job.process.state()!=QProcess.NotRunning:
                currun = time.monotonic()-job.timestart
                m.addAction("runtime: {:1.3f}s".format(currun))
            if job.window and hasattr(job.window,'timer') and job.window.timer.isActive():
                t = job.window.timer
                m.addAction("rerun in {:1.3f}/{:1.3f}s".format(t.remainingTime()/1000, t.interval()/1000))
            if job.runtime:
                m.addAction("avg runtime: {:1.3f}s".format(job.runtime))
            if job.window and hasattr(job.window, 'runcount'):
                m.addAction("run count: {}".format(job.window.runcount))
            
        action = m.exec(jobView.mapToGlobal(point))
        # all actions have their own handler, nothing to do here

    def resizeJobHheader(self, logical):
        self.ui.jobTableView.resizeColumnToContents(logical)
    def resizeJobVheader(self, logical):
        self.ui.jobTableView.resizeRowToContents(logical)

    def editButtonDocks(self):
        EditButtonDocks(self)
        
################ end noacli end

class commandEditor(QPlainTextEdit):
    command_to_run = pyqtSignal(str,QPersistentModelIndex )
    newFavorite = pyqtSignal(str)

    def __init__(self, parent):
        super().__init__(parent)
        self.ui = parent.parent().ui
        self.histindex = None
        self.history = None
        # XXX put all these key bindings in an array for a settings editor?
        self.histUp = QShortcut(QKeySequence('ctrl+up'),self)
        self.histUp.activated.connect(self.historyUp)
        self.histUp2 = QShortcut(QKeySequence('ctrl+p'),self)
        self.histUp2.activated.connect(self.historyUp)
        self.histDown = QShortcut(QKeySequence('ctrl+down'), self)
        self.histDown.activated.connect(self.historyDown)
        self.histDown2 = QShortcut(QKeySequence('ctrl+n'), self)
        self.histDown2.activated.connect(self.historyDown)
        self.runCmd2 = QShortcut(QKeySequence(QKeySequence.InsertLineSeparator), self)
        self.runCmd2.activated.connect(self.runCommand)
        self.runCmd3 = QShortcut(QKeySequence('Ctrl+Return'), self)
        self.runCmd3.activated.connect(self.runCommand)
        # shift return does not work!?  override keyPressEvent instead?
        self.runCmd4 = QShortcut(QKeySequence('Shift+Return'), self)
        self.runCmd4.activated.connect(self.runCommand)
        
        self.setContextMenuPolicy(Qt.DefaultContextMenu)
        # why can't designer set this?
        self.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)


    @QtCore.pyqtSlot('QContextMenuEvent')
    def contextMenuEvent(self, event):
        m=super().createStandardContextMenu(event.pos())
        m.addAction("Run", self.runCommand)
        m.addAction("Save to history and clear", self.clear)
        m.addAction("Clear", super().clear)
        m.addAction("Add to favorites",self.addFav)
        #return m
        action = m.exec(event.globalPos())
        # don't need to use action here

    def addFav(self):
        text = self.toPlainText()
        # have to do these two things separately or the closure messes it up
        self.newFavorite.emit(text)

    def setHistory(self, hist):
        self.history = hist

    @QtCore.pyqtSlot()
    def historyUp(self):
        if not self.history: return
        self.acceptHistory(self.history.prev(self.histindex))
        
    @QtCore.pyqtSlot()
    def historyDown(self):
        if not self.history: return
        self.acceptHistory(self.history.next(self.histindex))

    @QtCore.pyqtSlot()
    def runCommand(self):
        text = self.toPlainText()
        if text:
            h = self.history.saveItem(text, self.histindex, None)
            if type(h)!=QPersistentModelIndex:
                h=QPersistentModelIndex(h)
            self.command_to_run.emit(text, h)

            super().clear()  # bypass internal clear
            self.histindex = None

    def clear(self):
        # save previous contents in history if modified
        if self.document().isModified():
            # XX this should be done with a signal instead
            i = self.history.saveItem(self.toPlainText(), self.histindex, None)
            if i: self.ui.historyView.resetView(i)
        self.histindex = None
        super().clear()

    def acceptCommand(self, str, title=None):
        # XX do something with title
        # get current selected text before clearing it
        cursor = self.textCursor()
        if cursor.hasSelection():
            oldsel = cursor.selectedText()
        else:
            oldsel = None
        self.clear()
        if title: # save it, maybe some day we parse the title XX
            # XX try to put oldstr in title too? maybe not safe?
            str = '# '+title + '\n' + str
        self.setFocus()
        self.histindex = None
        self.setPlainText(str)
        # XX is there any use of acceptCommand for which this would be inconvenient?
        mark = typedQSettings().value('TemplateMark',None)
        if mark and len(mark):
            if self.find(mark) and oldsel:  # repaste selection on top of mark
                cursor = self.textCursor()
                cursor.insertText(oldsel)

    #is this right? @QtCore.pyqtSlot(QModelIndex)
    def acceptHistory(self, idx):
        self.clear()
        if idx:
            if type(idx)!=QPersistentModelIndex: idx=QPersistentModelIndex(idx)
        self.histindex = idx;
        if not idx: return  # None when wrapping, leave editor blank.
        # unwrap QPeristentIndex and QSortProxy
        str = idx.model().index(idx.row(),1).data(Qt.EditRole)
        self.setPlainText(str)
        c = self.textCursor()
        c.movePosition(QTextCursor.End)
        self.setTextCursor(c)
        # scroll history window to this entry and select it
        hv= self.ui.historyView
        hv.resetView(idx)
        hv.selectionModel().setCurrentIndex(idx.model().index(idx.row(),1), QtCore.QItemSelectionModel.ClearAndSelect )

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    QtCore.QCoreApplication.setOrganizationName("kg4ydw");
    QtCore.QCoreApplication.setApplicationName("noacli");

    # XX process noacli command line args (do to what?)

    mainwin = noacli(app)
    w = mainwin.ui

    mainwin.show()
    mainwin.start()

    app.exec()
