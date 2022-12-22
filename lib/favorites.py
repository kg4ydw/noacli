from functools import partial

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.Qt import Qt, pyqtSignal, QBrush
from PyQt5.QtCore import QModelIndex, QPersistentModelIndex, QSettings
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import QDialogButtonBox, QKeySequenceEdit
from lib.typedqsettings import typedQSettings
from lib.datamodels import simpleTable, settingsDataModel, settingsDialog
from lib.buttonDock import commandPushButton

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
        if oldval and oldval in self.vdata[col]:
            self.vdata[col][oldval].discard(row)
            if len(self.vdata[col][oldval])==1: # update oldval if it's ok now
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
     
class favoriteItem():
    def __init__(self, buttonName=None, shortcut=None, immediate=True):
        self.buttonName = buttonName
        self.shortcut = shortcut
        self.immediate = immediate
        self.button = None
   
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
        if c.shortcut:
            c.shortcuto = QtWidgets.QShortcut(QKeySequence(c.shortcut), self.buttonbox)
            #print('bind {} to {}'.format(c.shortcut.toString(), command)) # DEBUG
            if c.immediate:
                f = self.runfuncs[0]
            else:
                f = self.runfuncs[1]  # XXX make right click always do this
            #c.shortcuto.activated.connect(lambda: f(command, None))
            c.shortcuto.activated.connect(partial(self.runkey, f, command))
    def runkey(self, f, command):
        #print('gotkey for '+command) # DEBUG
        f(command,'')

    def delFavorite(self, command):
        #print('del favorite '+command) # DEBUG
        if command not in self.cmds:
            #print('missing button: '+command) # DEBUG
            return
        c = self.cmds.pop(command)
        # remove button
        layout = self.buttonbox.layout()
        if c.button:
            layout.removeWidget(c.button)
            c.button = None
        # remove shortcut
        if c.shortcut:
            c.shortcuto.activated.disconnect()
            c.shortcuto.setKey(QKeySequence())
            c.shortcuto.setParent(None)
            c.shortcuto = None

    def addButton(self, cmd, fav):
        if fav.immediate:
            f = self.runfuncs[0]
        else:
            f = self.runfuncs[1]  # XXX make right click always do this
        b = commandPushButton(fav.buttonName, cmd, self.buttonbox, f)
        if fav.immediate:
            b.setStyleSheet("QToolButton { font-weight: bold; }")
        else:
            b.setStyleSheet("QToolButton { font-style: italic; }")


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
        model = favoritesModel(data,
            ['keep', 'name',  'key', 'Immediate',  'count', 'command'], datatypesrow=datatypes,
          editmask=[True, True, True, True, False, True],
                            validator=self.validateData)
        # extra features
        
        # if anything is checked or edited (not blanked), check keep
        self.dialog = settingsDialog(parent, 'Favorites editor', model, 'Favorites, shortcuts, and buttons')
        self.dialog.finished.connect(self.doneFavs)
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
                print("Warning: ignoring duplicate cmd: "+command) # EXCEPT
            elif keep:
                if command not in self.cmds:
                    gotcmd.add(command)
                    self.addFavorite(command, name, shortcut, immediate)
        # above code won't work on a second pass (removed apply button, moot)
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
            index.model().setData(index.siblingAtColumn(0),True, Qt.EditRole) # XXXX sibling
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


class keySequenceDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, parent):
        super().__init__(parent)
    
    def createEditor(self,parent,option,index):
        # XXX do something with option? set background?
        w = QKeySequenceEdit(parent)
        ## well this didn't work
        #if option and option.backgroundBrush:
        #    w.setBackgroundRole(option.backgroundBrush.color())
        return w
    def setEditorData(self, editor, index):
        data = index.model().data(index, Qt.EditRole)
        if data:
            # XXX pick correct keySequence translation flavor?  important for mac?
            editor.setKeySequence(data)
        # else leave with default
        
    #??# def updateEditorGeometry(self, editor, option, index):

    def setModelData(self, editor, model, index):
        k = editor.keySequence()
        if k==QKeySequence.Backspace or k.toString()=='Backspace':
            # cancel shortcut; this is a work around in qt misfeature
            model.setData(index, '', Qt.EditRole)
            editor.clear() # looks wierd but works
        else:
            model.setData(index, k.toString(), Qt.EditRole)
    ####
settingsDialog.registerType(QKeySequence, keySequenceDelegate)
