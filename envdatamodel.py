
__license__   = 'GPL v3'
__copyright__ = '2022, Steven Dick <kg4ydw@gmail.com>'

# Remember, edit, save, and manage environment variables for subprocess use.

from enum import Enum

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QStyledItemDelegate, QComboBox, QMenu, QInputDialog
from PyQt5.Qt import Qt
from PyQt5.QtCore import QProcess, QProcessEnvironment, QSettings, QAbstractListModel, QModelIndex

from datamodels import settingsDialog, settingsDataModel, simpleTable

class envModes(Enum):
    Inherit = 0
    Session = 1
    Save = 2
    Deleted = 3
    Mask = 4
envModes.Inherit.__doc__ = "Inherit from external environment, reset local changes"
envModes.Session.__doc__ = "Changes used for this session only" 
envModes.Save.__doc__ = "Save changes for future sessions"
envModes.Deleted.__doc__ = "Will not be used for subprocesses in this session"
envModes.Mask.__doc__ = "Masked from use in this and future sessions"

class envModeModel(QAbstractListModel):
    def __init__(self,parent):
        super().__init__(parent)
    def rowCount(self,parent):
        return len(envModes)
    def data(self,index, role):
        i = index.row()
        try:
            v = envModes(i)
        except ValueError:
            print("bad envModes {}".format(i)) # EXCEPT
            return None
        if role==Qt.DisplayRole:
            return v.name
        if role==Qt.EditRole:
            return v
        elif role==Qt.ToolTipRole:
            return v.__doc__
        return None

class envModesDelegate(QStyledItemDelegate):
    def __init__(self, parent):
        super().__init__(parent)

    def createEditor(self,parent,option,index):
        # XXX do something with option? set background?
        w = QComboBox(parent)
        w.setModel(envModeModel(parent))
        #data = index.model().data(index, Qt.EditRole)
        #w.setCurrentIndex(data.value)
        #w.insertItems(0,[i.name for i in envModes])
        return w
    def setEditorData(self, editor, index):
        data = index.model().data(index, Qt.EditRole)
        if data:
            if type(data)==str: data=envModes[data]
            editor.setCurrentIndex(data.value)
    def setModelData(self, editor, model, index):
        val = editor.currentIndex()
        index.model().setData(index,envModes(val), Qt.EditRole)
    def paint(self, painter, option, index):
        d = index.data(Qt.DisplayRole)
        if type(d)!=str: d=d.name
        QStyledItemDelegate.paint(self, painter, option, QModelIndex())
        painter.save()
        rect = QtCore.QRectF(option.rect)
        painter.setClipRect(rect)
        painter.drawText(rect, Qt.AlignCenter|Qt.AlignVCenter|Qt.TextSingleLine, d)
        painter.restore()

class envSettings(QProcessEnvironment):
    def __init__(self):
        super().__init__(QProcessEnvironment.systemEnvironment())
        settingsDialog.registerType(envModes, envModesDelegate)
        self.modes = {}
        for key in self.keys():
            self.modes[key] = envModes.Inherit
        self.loadEnvironment()
    
    def loadEnvironment(self):
        # load environment changes from QSettings
        qs = QSettings()
        qs.beginGroup('environment')
        for key in qs.childGroups():
            mode = qs.value(key+'/mode',None)
            if mode=='save':
                self.modes[key] = envModes.Save
                self.insert(key, qs.value(key+'/val', None))
            elif mode=='mask':
                self.modes[key] = envModes.Mask
                self.remove(key)

    def saveEnvironment(self):
        qs = QSettings()
        qs.beginGroup('environment')
        for key in self.modes.keys():
            if self.modes[key]==envModes.Save:
                qs.setValue(key+'/mode','save')
                qs.setValue(key+'/val', self.value(key))
                #oldvals.discard(key)
            elif self.modes[key]==envModes.Mask:
                qs.setValue(key+'/mode','mask')
                #oldvals.discard(key)
            elif self.modes[key]==envModes.Inherit and (
                    qs.contains(key) or qs.contains(key+'/mode')):
                # delete a now inherited key
                qs.remove(key+'/mode')
                qs.remove(key+'/val')
                qs.remove(key)
            # ignore session vars
        qs.endGroup()

    def envDialog(self, parent):
        # make an editable table of environment settings and add some blanks
        self.envset = set(self.modes.keys()) # remember what we started with
        self.origenv = QProcessEnvironment.systemEnvironment()
        self.envdata = []
        # assume modes has deleted and masked values too
        for key in sorted(self.envset):
            if self.contains(key):
                val = self.value(key)
            else:
                val=''
            self.envdata.append( [key,  self.modes[key].name, val])
        # add empty entries for editing in custom values
        # this is wrong, key isn't editable, use context menu instead
        #self.envdata += [['',envModes.Session, ''],['', envModes.Session,'']] 
        model = simpleTable(self.envdata, ['Env Var','Mode', 'Value'], editmask=[False, True, True], datatypesrow = [str, envModes, str], validator=self.validator)
        self.model = model
        self.envDia = settingsDialog(parent,'Environment variables', model)
        self.envDia.finished.connect(self.finishEnv)
        self.envDia.setContextMenuPolicy(Qt.CustomContextMenu)
        self.envDia.customContextMenuRequested.connect(self.envContextMenu)

    def validator(self, index, value):
        col = index.column()
        old = index.data()
        row = index.row()
        key = self.envdata[row][0]
        if col==1: # changing mode
            if type(old)==str: old=envModes[old]
            if value==old: return True
            if value==envModes.Inherit:
                index.model().setData(index.siblingAtColumn(2), self.origenv.value(key,''), Qt.EditRole) # XX sibling
        elif col==2:
            if old==value: return True
            mode = self.envdata[row][1]
            if type(mode)==str: mode=envModes[mode]
            if mode in [envModes.Deleted, envModes.Inherit]:
                index.model().setData(index.siblingAtColumn(1), envModes.Session, Qt.EditRole) # XX sibling
            elif mode==envModes.Mask:
                index.model().setData(index.siblingAtColumn(1), envModes.Save, Qt.EditRole)
        return True
        
    def finishEnv(self, result):
        if result:
            for i in range(len(self.envdata)):
                (key,mode,value) = self.envdata[i][0:3]
                ## if mode is str, then row is unchanged
                if type(mode)==str: # no changes
                    self.envset.discard(key)
                    continue
                if mode in [envModes.Deleted, envModes.Mask] :
                    self.remove(key)
                elif mode==envModes.Inherit:
                    self.insert(key, self.origenv.value(key))
                    self.modes[key] = mode
                elif mode in [envModes.Save, envModes.Session]:
                    self.insert(key, value)
                self.modes[key] = mode
                self.envset.discard(key)
            ## nothing should be missing
            #for missing in self.envset:
            #    self.remove(missing)
            if self.envset:
                print("Missing env: "+(" ".join(self.envset))) # EXCEPT
        self.envset = None
        self.envdata = None
        self.envDia.setParent(None)
        self.envDia = None
        self.origenv = None
        self.model = None
        self.saveEnvironment()

    #@QtCore.pyqtSlot(QtCore.QPoint)
    def envContextMenu(self, point):
        # XXX special env context menu things here later maybe
        m = QMenu()
        m.addAction("Add new variable", self.addnewvar)
        # reset to default by changing mode to inherited, which has immediate effect
        action = m.exec_(self.envDia.mapToGlobal(point))

    def addnewvar(self):
        (name, result) = QInputDialog.getText(self.envDia, "Add new environment variable", "Variable name")
        if not result: return
        if name and len(name):
            if name not in self.envset:
                self.model.appendRow([name, envModes.Session, ''])
                self.envset.add(name)
            # else: find and select matching entry
