#!/usr/bin/env python3

import os
import sys
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.Qt import Qt, pyqtSignal, QBrush
from PyQt5.QtGui import QTextCursor, QKeySequence,QTextOption 
from PyQt5.QtWidgets import *
from PyQt5.QtCore import QCommandLineParser, QCommandLineOption, QIODevice, QModelIndex, QSettings, QProcessEnvironment

from functools import partial

from noacli_ui import Ui_noacli
from settingsdialog_ui import Ui_settingsDialog
from typedqsettings import typedQSettings

from datamodels import simpleTable, History, jobItem, jobTableModel, settingsDataModel
from smalloutput import smallOutput
from qtail import myOptions as qtailSettings

import noaclires
import signal

__version__ = '0.9.4'

class settingsDict():
    # key : [ default, tooltip, type ]
    settingsDirectory = {
    # All uppercase are inherited(?) from bash
    'DefWinProfile':[True, 'Load the Default window profile at start', bool],
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
    'MessageDelay':[10, 'Timeout (seconds) for transient message bar messages', float],
    'SHELL':       [ 'bash -c', 'external shell wrapper command to run complex shell commands', str],
    'TemplateMark':['{}', 'Move cursor to this string after loading a command into the edit window', str],
# qtail options
    'QTailMaxLines': [ 10000, 'maximum lines remembered in a qtail window', int],
    'QTailEndBytes': [ 1024*1024, 'Number of bytes qtail rewinds a file', int],
    'QTailDefaultTitle': [ 'subprocess', 'Default title for a qtail process window', str ],
   #'QTailFormat': [ 'plaintext', 'plaintext or html', str ],
   #'QTailFollow': [ False, 'scroll qtail to the end of the file on updates', bool ],
   #'QTailWrap':  [ True, 'wrap long lines', bool ]
   #'QTailSearchMode': ['exact', 'exact or regex search mode', str],
   #'QTailCaseInsensitive': [True, 'Ignore case when searching', bool],
    'SmallMultiplier': [2, 'Number of lines to keep in the small output window, <10 is in screens, >=10 is paragraphs, <1 for infinite', int],
    }

    def __init__(self):
        q= typedQSettings()
        q.setDict(self.settingsDirectory)

# initialize, load, hold, and save various global settings
class settings():
    def __init__(self):
        qs = typedQSettings()
        self.settingsDirectory = qs.setdict
        # create skelectons of settings and read previous or set defaults
        self.history = History()
        self.history.read()
        self.favorites = Favorites(self)
        # don't call this before setting buttonbox, so call it in caller
        #self.favorites.loadSettings()

        # XXX populate environment from system environment
        self.environment = QProcessEnvironment.systemEnvironment()
        ## XXX later [ 'name', 'value', 'propagate', 'save' ])
        self.jobs = jobTableModel()
        # job manager gets its own special class
        
        self.qtail = qtailSettings()
        self.copy2qtail()

        ## settings dialog info
        # name, default, tooltip / description
        # Note: defaults here might not match the real defaults embeeded in code
    def makeDialog(self, parent):
        # collect list of rows including settings
        # build a list of settings, each source sorted separately
        rows = sorted(self.settingsDirectory.keys())
        # add additional settings from QSettings (missing from dict)
        qs = typedQSettings()
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
                    # XXX put this in a try
                    val = self.settingsDirectory[name][2](val)
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
        self.dialog.apply.connect(self.acceptchanges)

    def copy2qtail(self):
        qs = typedQSettings()
        # copy qtail settings
        self.qtail.maxLines = int(qs.value('QTailMaxLines', self.qtail.maxLines))
        self.qtail.tailFrag = int(qs.value('QTailEndBytes', self.qtail.tailFrag))
        # QTailDefaultTitle: default title is set somewhere else XXX
        # XXX more qtail settings not implemented yet
        
    def acceptchanges(self):
        print('accept') # DEBUG
        qs = typedQSettings()
        for d in self.data:
            if d[1]!=None:
                #print('save '+str(d[0])+' = '+str(d[1])) # XXX # DEBUG
                qs.setValue(d[0], d[1])
        self.copy2qtail()
        qs.sync()
    def acceptOrReject(self, result):
        if result: self.acceptchanges()
        #print('finished') # DEBUG
        # destroy everything
        self.dialog = None
        self.data = None

    def envDialog(self,parent):
        # make an editable table of environment settings and add some blanks
        self.envset = set(self.environment.keys())
        self.envdata = [ [key, self.environment.value(key)] for key in sorted(self.envset)]
        self.envdata += [['',''],['','']]
        model = simpleTable(self.envdata, ['Env Var','Value'], editmask=[True, True])
        self.envDia = settingsDialog(parent,'Environment variables', model)
        self.envDia.finished.connect(self.finishEnv)
    def finishEnv(self, result):
        if result:
            for row in self.envdata:
                if row[0] and row[1]:
                    self.environment.insert(row[0], row[1])
                    self.envset.discard(row[0])
            for missing in self.envset:
                self.environment.remove(missing)
        self.envset = None
        self.envdata = None
        self.envDia = None

class settingsDialog(QtWidgets.QDialog):
    def __init__(self, parent, title, model, doc=None):
        # need parent so that this isn't persistent in window close
        super().__init__(parent)
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
            ui.label.setText(title)
        ui.tableView.resizeColumnsToContents()
        self.apply = self.ui.buttonBox.button(QDialogButtonBox.Apply).clicked
        # XX resize top window too?
        self.show()

class historyView(QTableView):
    newFavorite = pyqtSignal(str)

    def __init__(self, parent):
        super().__init__(parent)
        self.realModel = None
        self.historyProxy = QtCore.QSortFilterProxyModel()
        # mess with the history corner button
        cb = self.findChild(QtWidgets.QAbstractButton)
        if cb:
            cb.disconnect()
            cb.clicked.connect(self.resetHistorySort)

    def setModel(self,model):
        self.realModel = model
        self.historyProxy.setSourceModel(model)
        self.historyProxy.setFilterKeyColumn(1)
        super().setModel(self.historyProxy)
        # this is probably too soon
        self.resizeColumnsToContents()

    def resetHistorySort(self):
        self.historyProxy.sort(-1)
        self.horizontalHeader().setSortIndicator(-1,0)
        #self.historyProxy.invalidate()
        self.resizeColumnsToContents()

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
        cmd = index.data()
        self.newFavorite.emit(cmd)
    
    def contextMenuEvent(self, event):
        m = QMenu(self)
        # XXX disable or omit inappropriate actions
        index = self.indexAt(event.pos())
        act = m.addAction("Add to favorites",partial(self.addFav, index))
        act = m.addAction("Delete",partial(self.deleteOne, index))
        act = m.addAction("Delete selected rows",self.deleteSelected)
        # make the model do these two
        act = m.addAction("Collapse duplicates",self.realModel.collapseDups)
        act = m.addAction("Delete earlier duplicates",self.realModel.deletePrevDups)
        action = m.exec_(event.globalPos())
        #print(action) # DEBUG

    def resetView(self, index=None):
        self.resetHistorySort()
        if index:
            # one of these should work
            #self.scrollTo(index)
            i = self.historyProxy.mapFromSource(index)
            self.scrollTo(i.siblingAtColumn(0))
        else:
            self.scrollToBottom()

            
class commandPushButton(QToolButton):
    # this is a push button that remembers what it is suppose to do
    def __init__(self, name, command,parent, functor):
        super().__init__(parent)
        self.setText(name)
        self.command = command
        self.setToolTip(command) # XXX different for immediate vs template?
        self.actionfunc = functor
        ## dunno if all this goo is needed, but designer emits it with gridview
        #sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        #sizePolicy.setHorizontalStretch(0)
        #sizePolicy.setVerticalStretch(0)
        #sizePolicy.setHeightForWidth(self.sizePolicy().hasHeightForWidth())
        #self.setSizePolicy(sizePolicy)
        self.setObjectName(name) # XX redundant? merge name and data for use?
        self.clicked.connect(self.pushButtonAction)
        # XXX layout mess
        parent.layout().addWidget(self)

    @QtCore.pyqtSlot()
    def pushButtonAction(self):
        self.actionfunc(self.command, self.text())



class favoriteItem():
    def __init__(self, buttonName=None, shortcut=None, immediate=True):
        self.buttonName = buttonName
        self.shortcut = shortcut
        self.immediate = immediate
        self.button = None

# data model for favorites to apply validator
# and add tooltip for command
class favoritesModel(simpleTable):
    def __init__(self,data, headers, datatypes=None, datatypesrow=None, editmask=None, validator=None ):
        super().__init__(data, headers, datatypes, datatypesrow, editmask, validator)
        # build validator dictionaries
        self.vdata = {}
        for col in [1,2,5]:
            self.vdata[col] = {}
            for row in range(len(data)):
                if data[row][col]:
                    d = data[row][col]
                    if d in self.vdata[col]:
                        self.vdata[col][d].add(row)
                    else:
                        self.vdata[col][d] = set([row])
        # color invalid cells
    def data(self, index, role):
        if not self.validateIndex(index): return None
        col = index.column()
        row = index.row()
        if col==5 and role==Qt.ToolTipRole and self.mydata[row][col]:
            return self.mydata[row][col]
        if role!=Qt.BackgroundRole or not col in [1,2,5] or not self.mydata[row][col]:
            return super().data(index,role)
        d = self.mydata[row][col]
        if d in self.vdata[col] and len(self.vdata[col][d])>1:
            if col==5: # XXX is key critical too?
                return QBrush(Qt.red)
            else:
                return QBrush(Qt.yellow)
        return super().data(index,role)
    
    # update background of related rows, don't emit for this one
    def setData(self,index,value,role):
        if not self.validateIndex(index): return None
        col = index.column()
        row = index.row()
        if col not in [1,2,5] or self.mydata[row][col]==value:
            return super().setData(index,value,role)
        oldval = self.mydata[row][col]
        if oldval:
            self.vdata[col][oldval].remove(row)
        if oldval and len(self.vdata[col][oldval])==1: # update oldval if it's ok now
            remaining = next(iter(self.vdata[col][oldval]))
            i = self.index(remaining, col, QModelIndex())
            self.dataChanged.emit(i,i)
        if value and value in self.vdata[col]:
            if len(self.vdata[col][value])==1: # update newval if it's now dup
                remaining = next(iter(self.vdata[col][value]))
                i = self.index(remaining, col, QModelIndex())
                self.dataChanged.emit(i,i)
            self.vdata[col][value].add(row)
        else:
            self.vdata[col][value] = set([row])
        return super().setData(index,value,role)
        
class Favorites():
    # buttons, keyboard shortcuts, and other marked commands
    # This doesn't use an abstract data model because one will be
    # constructed on the fly to also include frequent and recent commands.
    def __init__(self, settings):
        self.cmds = {}
        self.settings = settings
        self.buttonbox = None
        self.runfuncs = None

    def setButtonBox(self, box, runfuncs):
        self.buttonbox = box
        self.runfuncs=runfuncs
        
    def addFavorite(self, command,  buttonName=None, keybinding=None, immediate=True):
        #print("add favorite {} = {}".format(buttonName,command)) # DEBUG
        c = self.cmds[command] = favoriteItem(buttonName, keybinding, immediate)
        if buttonName:
            self.addButton(command, c)
        # XXX add keybinding

    def delFavorite(self, command):
        #print('del favorite '+command) # DEBUG
        if command not in self.cmds:
            print('missing button: '+command) # DEBUG
            return
        c = self.cmds.pop(command)
        # remove button
        layout = self.buttonbox.layout()
        if c.button:
            layout.removeWidget(c.button)
            c.button = None
        # XXXX remove shortcut

    def addButton(self, cmd, fav):
        if fav.immediate:
            f = self.runfuncs[0]
        else:
            f = self.runfuncs[1]  # XXX make right click always do this
        b = commandPushButton(fav.buttonName, cmd, self.buttonbox, f)
        fav.button = b
        return b
        
    
    def editFavorites(self, parent):
        data = []
        # save this so the validator can get it
        self.data = data
        qs = typedQSettings()
        # schema: *=checkbox
        # *keep name key *checkImmediate count command 
        # collect commands from frequent history
        (_, count) = self.settings.history.countHistory()
        # collect commands from favorites
        f = sorted(self.cmds.keys())
        data+=[ [True, self.cmds[c].buttonName, self.cmds[c].shortcut, self.cmds[c].immediate, (c in count and count[c]) or 0 , c] for c in f]
        # only remember previously saved favorites, and in order
        self.oldcmds = [ data[x][5] for x in range(len(data))]
        cmdlist = set(f)  # don't put dup commands in
        # add frequenty history commands
        freq = sorted([k for k in count.keys() if k not in cmdlist], key=lambda k: count[k])
        freq.reverse()
        nfreq = int(qs.value('FavFrequent',10))
        data += [ [False, None, None, True, count[k], k] for k in freq[0:nfreq]]
        cmdlist |= set(freq[0:nfreq])

        # collect commands from recent history
        nh = int(qs.value('FavRecent',10))
        h = self.settings.history.last()
        while nh>0 and h:
            c = str(h.data())
            if c not in cmdlist:
                data.append([False, None, None, True, count[c], c])
                cmdlist.add(c)
                nh -= 1
            h = h.model().prevNoWrap(h)
        datatypes = [bool, str, QKeySequence, bool, None, str]
        # XXX might need to subclass simpleTable to make a shortcut editor
        model = favoritesModel(data,
            ['keep', 'name',  'key', 'Immediate',  'count', 'command'], datatypesrow=datatypes,
          editmask=[True, True, True, True, False, True],
                            validator=self.validateData)
        # extra features
        #XXX if anything is checked or edited (not blanked), check keep
        self.dialog = settingsDialog(parent, 'Favorites editor', model, 'Favorites, shortcuts, and buttons')
        self.dialog.finished.connect(self.doneFavs)
        self.dialog.apply.connect(self.saveFavs)
        buttonbox = self.dialog.ui.buttonBox
        buttonbox.setStandardButtons(buttonbox.standardButtons()| QDialogButtonBox.Save)
        savebutton = buttonbox.button(QDialogButtonBox.Save).clicked.connect(self.saveSettings)

    #@QtCore.pyqtSlot(bool)
    def saveFavs(self,checked):
        # repopulate favorites and buttons
        # purge deleted and changed stuff
        for i in range(len(self.oldcmds)):
            # name, shortcut, immediate
            (keep, name, shortcut, immediate, count, command) = self.data[i]
            fav = favoriteItem(name, shortcut, immediate)
            # delete old stuff that changed
            if self.oldcmds[i]!=command or not keep or command in self.cmds and self.cmds[command]!=fav:
                    self.delFavorite(self.oldcmds[i])
                
        # only take the first instance of each command
        gotcmd = set()
        for row in self.data:
            (keep, name, shortcut, immediate, count, command) = row
            if command in gotcmd:
                print("Warning: ignoring duplicate cmd: "+command) # DEBUG
            elif keep:
                if command not in self.cmds:
                    gotcmd.add(command)
                    self.addFavorite(command, name, shortcut, immediate)
        # XXX above code won't work on a second pass
        ## don't destroy this in case apply is clicked a second time
        #self.data = None

    #@QtCore.pyqtSlot(int)
    def doneFavs(self,result):
        #print('done') # DEBUG
        if result:
            self.saveFavs(False)
        # destroy temp data
        self.data = None
        self.oldcmd = None
        
    def validateData(self, index, val):
        if not index.isValid(): return False
        # don't mess with the keep checkbox if it is being changed
        if index.column()==0: return True # also prevents recursion
        # if anything else is edited and not blanked, check keep
        if val and val!=self.data[index.row()][index.column()]:
            index.model().setData(index.siblingAtColumn(0),True, Qt.EditRole)
        return True

    def saveSettings(self):
        qs = QSettings()
        qs.beginGroup('Favorites')
        # how much will QSettings hate me if I dump stuff on it
        val = [ [ c, self.cmds[c].buttonName,  self.cmds[c].shortcut, self.cmds[c].immediate] for c in self.cmds]
        #print(str(val)) # DEBUG
        qs.setValue('favorites', val)
        qs.endGroup()

    def loadSettings(self):
        qs = QSettings()
        qs.beginGroup('Favorites')
        val = qs.value('favorites', None)
        #print('favorites: '+str(val)) # DEBUG
        if not val: return
        for v in val:
            self.addFavorite(*v[0:4])  # super lazy
        qs.endGroup()

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
    def __init__(self):
        settingsDict()   # do this very early
        super().__init__()
        self.ui = Ui_noacli()
        self.ui.setupUi(self)

        # mess with style
        #self.setStyleSheet("QMainWindow::separator{ width: 0px; height: 0px; }");
        f = self.ui.buttonBox.layout()
        f.setContentsMargins(3,3,3,3)

        # delayed resize works better
        self.want_restore_geo_delay.connect(self.restore_geo, Qt.QueuedConnection) # delay this

        self.settings = settings()
        # cheat a bit
        self.settings.smallOutputView = self.ui.smallOutputView
        self.settings.statusBar = self.statusBar()

        self.historypos = 1;
        #dir = os.path.dirname(os.path.realpath(__file__))
        self.setWindowIcon(QtGui.QIcon(':noacli.png'))

        # hide all the docks by default (save a profile if you don't like it)
        ui=self.ui
        self.hideAllDocks()

        ## XXX show buttons by default?
        # connect buttons to favorites
        self.settings.favorites.setButtonBox(self.ui.buttonBox, [ self.runSimpleCommand, self.ui.commandEdit.acceptCommand])
        self.settings.favorites.loadSettings()

        # populate the view menu for DOCK (is there a more automatic way?)
        ui.menuViews.addAction(ui.history.toggleViewAction())
        ui.menuViews.addAction(ui.jobManager.toggleViewAction())
        ui.menuViews.addAction(ui.buttons.toggleViewAction())
        ui.menuViews.addAction(ui.smallOutputDock.toggleViewAction())

        self.tabifyAll()
        ui.actionTabifyDocks.triggered.connect(self.tabifyAll)

        # attach the data models to the views
        ui.historyView.setModel(self.settings.history)
        ui.historySearch.textChanged['QString'].connect(ui.historyView.historyProxy.setFilterFixedString)

        # make all the tables fit
        ui.jobTableView.resizeColumnsToContents()

        # connect the command editor to the history data model
        # XX this should be a connect historySave->saveItem
        ui.commandEdit.setHistory(self.settings.history)

        ui.jobTableView.setModel(self.settings.jobs)

        # mess with job manager corner button (is this even visible?)
        cb = ui.jobTableView.findChild(QtWidgets.QAbstractButton)
        if cb:
            cb.disconnect()
            cb.clicked.connect(self.settings.jobs.cleanup)

        # build history context menu
        self.ui.historyMenu.aboutToShow.connect(self.buildHistoryMenu)
        self.ui.menuJobs.aboutToShow.connect(self.buildJobMenu)

        self.ui.historyView.scrollToBottom()
        self.ui.actionFavorites_editor.triggered.connect(partial(self.settings.favorites.editFavorites, self))

        # file browser shortcut
        self.fileShortcut = QShortcut(QKeySequence('ctrl+f'), self)
        self.fileShortcut.activated.connect(self.pickFile)

        self.ui.smallOutputView.oneLine.connect(self.showMessage)
        self.ui.smallOutputView.newJobStart.connect(self.statusBar().clearMessage)
        # close and reopen stdin. We dont need it, and bad things happen
        # if subprocesses try to use it.
        ## nonportable out of unix?
        # XXX this didn't help
        #os.close(0)
        #os.open("/dev/null", os.O_RDWR)
        
        ##### geometry profiles
        qs = typedQSettings()
        v = qs.value('DefWinProfile', True)
        if v: # XXX str convert?
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
        # XXX sort these, put default first and select it?
        for p in g:
            mm = gm.addAction(p)
            mm.setData(p)
            mm.setObjectName(p)
            #redundant and wrong# mm.triggered.connect(lambda: self.myRestoreGeometry(p))
            mm.setCheckable(True)
            m.addAction(mm)
            # XXX also add context menu: delete rename load ??
        gm.triggered.connect(self.actionRestoreGeomAct)
        qs.endGroup()

        self.showMessage('Version '+__version__)
        self.ui.smallOutputView.append('Version '+__version__)

        ##### install signal handlers
        try:  # in case anything here is unportable
            signal.signal(signal.SIGINT, self.ouch)
            #X this is for output# signal.signal(signal.SIGTSTP, self.tstp)
            signal.signal(signal.SIGTTIN, self.terminalstop) # XXX didn't work
            #signal.signal(signal.SIGTTIN, signal.SIG_IGN) # XXX didn't work
        except Exception as e:
            # XX ignore failed signal handler installs
            print("Not all signal handlers installed"+str(e)) # EXCEPT
            pass

    def terminalstop(self, sig, stack):
        print("Terminal stop blocked!") # EXCEPT
        self.showMessage("Terminal stop blocked!")
        # do something about the offending child process??
        
    def ouch(self, sig, stack):
        print('Ouch!') # EXCEPT
        # ignore a signal

    ## end __init__

    def tabifyAll(self):
        # convert all the DOCKs to tabs
        if self.ui.buttons.isFloating(): self.ui.buttons.setFloating(False)
        self.ui.jobManager.setFloating(False)
        self.ui.history.setFloating(False)
        self.ui.smallOutputDock.setFloating(False)
        self.tabifyDockWidget( self.ui.buttons,    self.ui.jobManager)
        self.tabifyDockWidget( self.ui.jobManager, self.ui.history)
        self.tabifyDockWidget( self.ui.history,    self.ui.smallOutputDock)

    def start(self):
        # nothing else to initialize yet
        pass

    def pickFile(self):
        pattern = typedQSettings().value('FileDialogFilter',None)
        editor = self.ui.commandEdit

        cursor = editor.textCursor()
        if cursor.hasSelection():
            pattern = cursor.selectedText()
        
        # avoid the default constructor
        # results = QFileDialog.getOpenFileNames(None, "Pick some files", ".", pattern)
        #fs = results[0]
        # parent: Attaches dialog to the parent window and covers it (ick!) 
        # other defaults need customizing, default constructor not flexible enough
        # also make it non-modal

        fd = QFileDialog(None, Qt.Dialog)
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

        if fd.exec_():
            fs = fd.selectedFiles()
        else:
            fs = None

        #print(str(fs)) # DEBUG
        cwd = os.getcwd()+'/'
        print(fs) # DEBUG
        #print(cwd) # DEBUG
        if fs:  # do nothing if nothing selected
            try:
                # python 3.9 feature
                fs = [x.removeprefix(cwd) or x for x in fs]
            except:
                pass
            ## and return the results to the editor
            f = ' '.join(fs)
            editor.insertPlainText(f)
        
    ################
    # external slots
    # some of these could be moved

    @QtCore.pyqtSlot()
    def syncSettings(self):
        qs = QSettings()
        qs.sync() # XX is this necessary?

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
            text = str(index.model().getItem(index).process.processId())
            self.app.clipboard().setText(text)
        elif col==1: index.model().cleanupJob(index)  # job status
        elif col==2: self.windowShowRaise(index)
        elif col==3: self.ui.commandEdit.acceptCommand(index.model().getItem(index).command())

    # in: jobView out: jobModel
    def windowShowRaise(self,index):
        if isinstance(index, QAction): index = index.data() # unwrap
        job = index.model().getItem(index)
        if job.window:
            job.windowOpen = True
            job.window.show()
            job.window.raise_()
            job.window.activateWindow()


    # in: view menu  out: all DOCKs
    @QtCore.pyqtSlot()
    def showAllDocks(self):
        ui = self.ui
        ui.history.setVisible(True)
        ui.buttons.setVisible(True)
        ui.jobManager.setVisible(True)
        ui.smallOutputDock.setVisible(True)

    @QtCore.pyqtSlot()
    def hideAllDocks(self):
        ui = self.ui
        ui.history.setVisible(False)
        ui.buttons.setVisible(False)
        ui.jobManager.setVisible(False)
        ui.smallOutputDock.setVisible(False)

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
        self.settings.envDialog(self)

    @QtCore.pyqtSlot(str)
    def runSimpleCommand(self, cmd, title):
        self.runCommand(cmd,None,title)

    # in: self.runLast, commandEdit->command_to_run, QShortcuts
    # out: historyView, jobModel, jobTableView
    # slot to connect command window runCommand
    def runCommand(self, command, hist, title=None):
        if not hist and command:
            # make a new history entry!
            hist = self.settings.history.saveItem(command, None, None)
        if hist and isinstance(hist.model(),QtCore.QSortFilterProxyModel ):
            hist=hist.model().mapToSource(hist)
        self.ui.historyView.resetHistorySort()  # XXX this might be annoying
        j = jobItem(hist)  # XX construct new job
        if title: j.setTitle(title)
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
            if a.data(): hm.removeAction(a)
        # add new entries
        h = self.settings.history.last()
        qs = typedQSettings()
        i = int(qs.value('HistMenuSize', 10))
        cmds=set()
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
        self.ui.commandEdit.acceptHistory(act.data())

    # in: menuJobs->aboutToShow
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

    @QtCore.pyqtSlot()
    def actionSaveGeometry(self):
        a = self.ui.profileMenuGroup.checkedAction()
        if a:
            n = a.data()
            print('Current profile: '+n) # DEBUG
        else:
            n = 'default'
        self.mySaveGeometry(n)
        
    def mySaveGeometry(self,name='default' ):
        # XXX later make this into a named profile
        # XXX does each window need to be saved separately?
        print("Saving profile "+name) # DEBUG
        qs = QSettings()
        qs.beginGroup('Geometry/'+name)
        qs.setValue('mainGeo', self.saveGeometry())
        qs.setValue('mainState', self.saveState())
        qs.endGroup()
        # check if this is already in the menu, and if not, add it
        gm = self.ui.profileMenuGroup
        c = gm.findChild(QAction, name)
        if c: print(' already in menu') # DEBUG
        else:
            print(' adding {} to profile menu'.format(name)) # DEBUG
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
        print("action: "+n) # DEBUG
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
            print('No profile for {} found'.format(name)) # DEBUG EXCEPTION this can't happen
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
        self.actionSaveHistory()
        self.settings.favorites.saveSettings()
        super().closeEvent(event)

################ end noacli end

class commandEditor(QPlainTextEdit):
    command_to_run = pyqtSignal(str, QModelIndex)
    newFavorite = pyqtSignal(str)

    def __init__(self, parent):
        super().__init__(parent)
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
        action = m.exec_(event.globalPos())
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
        self.acceptHistory(self.history.next(self.histindex))

    @QtCore.pyqtSlot()
    def runCommand(self):
        text = self.toPlainText()
        if text:
            h = self.history.saveItem(text, self.histindex, None)
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
        # XXX do something with title
        # get current selected text before clearing it
        cursor = self.textCursor()
        if cursor.hasSelection():
            oldsel = cursor.selectedText()
        else:
            oldsel = None
        self.clear()
        if title: # save it, maybe some day we parse the title XXX
            # XXX try to put oldstr in title too? maybe not safe?
            str = '# '+title + '\n' + str
        self.setFocus()
        self.histindex = None
        self.setPlainText(str)
        # XX is there any us of acceptCommand for which this would be inconvenient?
        mark = typedQSettings().value('TemplateMark',None)
        if mark and len(mark):
            if self.find(mark) and oldsel:  # repaste selection on top of mark
                cursor = self.textCursor()
                cursor.insertText(oldsel)

    #is this right? @QtCore.pyqtSlot(QModelIndex)
    def acceptHistory(self, idx):
        self.clear()
        self.histindex = idx;
        str = idx.siblingAtColumn(1).data(Qt.EditRole)
        self.setPlainText(str)
        #unnecssary?# self.document().setModified( idx.siblingAtColumn(0).data(Qt.DisplayRole)==None)
        # scroll history window to this entry XX optional?
        self.ui.historyView.resetView(idx)

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    QtCore.QCoreApplication.setOrganizationName("kg4ydw");
    QtCore.QCoreApplication.setApplicationName("noacli");

    # XXX process command line args

    mainwin = noacli()
    mainwin.app = app
    w = mainwin.ui

    mainwin.show()
    mainwin.start()

    app.exec_()
