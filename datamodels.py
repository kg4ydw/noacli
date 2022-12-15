
__license__   = 'GPL v3'
__copyright__ = '2022, Steven Dick <kg4ydw@gmail.com>'

# simple tables and widgets for manipulating tables
# contaminated with app specific classes and GUI pieces

from PyQt5 import QtCore
from PyQt5.Qt import Qt, QAbstractTableModel, QBrush, pyqtSignal
from PyQt5.QtCore import QObject, QModelIndex, QPersistentModelIndex
from PyQt5 import QtWidgets
from settingsdialog_ui import Ui_settingsDialog

class simpleTable(QAbstractTableModel):
    def __init__(self,data, headers, datatypes=None, datatypesrow=None, editmask=None, validator=None ):
        QAbstractTableModel.__init__(self)
        #super().__init__(self)  # why does this break?
        self.mydata = data
        self.headers = headers
        self.datatypes = datatypes
        self.datatypesrow = datatypesrow
        self.editmask = editmask
        self.validator = validator
    # required functions rowCount columnCount data
    def rowCount(self, parent):
        return len(self.mydata)
    def columnCount(self, parent):
        return len(self.headers)
    def dataType(self, row,col):
        if self.datatypes and self.datatypes[row][col]:
            return  self.datatypes[row][col]
        elif self.datatypesrow and  self.datatypesrow[col]:
            return self.datatypesrow[col]
        return False
    def data(self, index, role):
        if not self.validateIndex(index): return None;
        row = index.row()
        col = index.column()
        # don't return normal data if this is suppose to be a checkbox
        ctype = self.dataType(row,col)
        if ctype and (ctype==bool or type(self.mydata[row][col])==bool):
            if role==Qt.CheckStateRole:
                if self.mydata[row][col]:
                    return Qt.Checked
                else:
                    return Qt.Unchecked
            else:
                return None
        if role in [Qt.DisplayRole, Qt.UserRole, Qt.EditRole]:
            try:  # ignore messy tables
                return self.mydata[row][col]
            except:
                return None
        return None
    def setData(self, index, value, role):
        if not self.validateIndex(index): return False
        # flags() controls if cell is writable
        row = index.row()
        col = index.column()
        # try user validator
        if self.validator and role in [Qt.EditRole, Qt.CheckStateRole]:
            if not self.validator(index,value): return False
        # validate and force type
        ctype = self.dataType(row,col)
        if ctype:
            try:
                self.mydata[row][col] = ctype(value)
                self.dataChanged.emit(index,index)
                return True
            except Exception as e:
                print(str(e)) # EXCEPT
                return False
        self.mydata[row][col] = value  # do it without any validation or cast
        self.dataChanged.emit(index,index)
        return True

    def flags(self,index):
        col = index.column()
        if not (self.datatypesrow or self.editmask) or col<0 or col>=len(self.headers):
            return super(simpleTable,self).flags(index)
        mask = Qt.ItemIsSelectable|Qt.ItemIsEnabled
        ctype = self.dataType(index.row(),col)
        if ctype==bool:
            mask |=  Qt.ItemIsUserCheckable
        elif self.editmask and self.editmask[col]:
            mask |= Qt.ItemIsEditable
        return mask
        
    def validateIndex(self, index):
        if not index or not index.isValid(): return False
        row = index.row()
        if row<0 or row>=len(self.mydata): return False
        col = index.column()
        if col<0 or col>=len(self.headers): return false
        return True
    # recommended: headerData
    def headerData(self, col, orientation, role):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal and col<len(self.headers):
                return self.headers[col]
            elif orientation == Qt.Vertical and col<len(self.mydata):
                # if you don't like veritcal headers, turn them off in designer
                return str(col+1)
        return None
    def insertRowsAt(self, where, rows):
        # non-standard manipulator
        # where=0 at start, where=1 at end
        count = len(rows)
        if where:
            start=len(self.mydata)
        else:
            start=0
        self.beginInsertRows(QModelIndex(),start,start+count-1)
        if where:
            self.mydata = self.mydata+rows
        else:
            self.mydata = rows + self.mydata
        maxx = max([len(row) for row in rows])
        self.endInsertRows()
        self.checkExtendHeaders(maxx)
        
    def checkExtendHeaders(self, maxx):
        if maxx> len(self.headers):
            start = len(self.headers)
            for i in range(start,maxx):
                self.headers.append(str(i+1))
            self.headerDataChanged.emit(Qt.Horizontal, start,maxx)
        
    def appendRow(self, row):
        lastrow = len(self.mydata)
        self.beginInsertRows(QModelIndex(), lastrow,lastrow)
        self.mydata.append(row)
        self.endInsertRows()

    def mergeCells(self, index, count=1):
        '''merge this cell with its adjacent neighbors in the same row, shifting
           down remaining cells
        '''
        # note: model doesn't have a beginMangleCells, sigh.
        row = index.row()
        col = index.column()
        if col+count>=len(self.mydata[row]): return False # whoops!
        # XX this should merge cells with the correct delimiter, oops
        for i in range(1,count+1):
            self.mydata[row][col] += ' '+self.mydata[row][col+i]
        del self.mydata[row][col+1:col+count+1]
        self.dataChanged.emit(self.index(row,col), self.index(row,len(self.mydata[row])))
        return True

class itemListModel(QAbstractTableModel):
    # an array of items, where each item is a row
    def __init__(self, headers):
        QAbstractTableModel.__init__(self)
        self.data = [ ]
        self.headers = headers

    # make this iterable
    def __getitem__(self, key):
        # note: this returns an index rather than returning the data
        if not type(key)==int: raise TypeError
        if key<0 or key>=len(self.data): raise IndexError
        return self.index(key,0)
        ### this could return the entry instead
        #return self.data[key]
    def isEmpty(self):
        return len(self.data)==0
    
    # required functions rowCount columnCount data
    def rowCount(self, parent):
        return len(self.data)
    def columnCount(self, parent):
        return len(self.headers)
    # convenience function
    def validateIndex(self, index):
        if not index or not index.isValid(): return False
        row = index.row()
        if row<0 or row>=len(self.data): return False
        # up to subclass to validate column
        return True

    # recommended: headerData
    def headerData(self, col, orientation, role):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal and col<len(self.headers):
                return self.headers[col]
            elif orientation == Qt.Vertical and col<len(self.data):
                # if you don't like veritcal headers, turn them off in designer
                return str(col+1)
        return None

    def getItem(self, index):
        if not self.validateIndex(index): return None
        return self.data[index.row()]

    # most added items are added at the end...
    def appendItem(self, item):
        lastrow = len(self.data)
        self.beginInsertRows(QModelIndex(), lastrow,lastrow)
        self.data.append(item)
        self.endInsertRows()
        item.index = QPersistentModelIndex(self.index(lastrow,1)) # and item remembers itself
        return item.index

    # subclass needs to first verify these can be deleted
    def removeRows(self, start, count, parent):
        if start<0 or start+count>len(self.data): return False
        self.beginRemoveRows(QModelIndex(),start, start+count-1)
        for i in range(count):
            d = self.data.pop(start)
            # clean up?  only some datatypes
        self.endRemoveRows()
        return True

class settingsDataModel(simpleTable):
    def __init__(self, docdict, data, typedata=None):
        self.docdict = docdict
        # XX this could be 3 column with the tool tips in col 3
        super().__init__(data, ['Setting', 'Value'], typedata, editmask=[False, True])
        # nothing else to do, most done in gui model
    def data(self, index, role):
        if not self.validateIndex(index): return None
        col = index.column()
        row = index.row()
        rowname = self.mydata[row][0]
        # color and supply default data
        if col==1 and self.mydata[row][1]==None: # not set, use default
            if role==Qt.BackgroundRole:
                return QBrush(Qt.lightGray)
            if self.docdict[rowname][2]==bool:
                if role==Qt.CheckStateRole:
                    if self.docdict[rowname][0]: return Qt.Checked
                    else: return Qt.Unchecked
                elif role!=Qt.ToolTipRole:
                    return None  # no text label on bools
            elif role in [Qt.DisplayRole, Qt.UserRole, Qt.EditRole]:
                # have to fill in default data to get type right
                return self.docdict[rowname][0]
        if role==Qt.ToolTipRole:  # XX and StatusRole ?
            if self.mydata[row][0] not in self.docdict: return None
            doc = self.docdict[rowname]
            # swap tooltip columns
            return doc[1-col]
        return super(settingsDataModel,self).data(index, role)

class settingsDialog(QtWidgets.QDialog):
    typedelegates = {}
    want_resize = pyqtSignal()
    def __init__(self, parent, title, model, doc=None):
        # need parent so that this isn't persistent in window close
        super().__init__(parent)
        ui = Ui_settingsDialog()
        self.model = model
        # XX proxy model?  search?
        self.ui = ui
        ui.setupUi(self)
        ui.tableView.setModel(model)
        self.want_resize.connect(self.adjustSize, Qt.QueuedConnection)
        if hasattr(model,'datatypesrow') and model.datatypesrow:
            for i in range(len(model.datatypesrow)):
                typename = str(model.datatypesrow[i])
                if typename in self.typedelegates:
                    ui.tableView.setItemDelegateForColumn(i,self.typedelegates[typename][1](ui.tableView))
        # very special, only check col=1
        if hasattr(model,'datatypes') and model.datatypes:
            for row in range(len(model.datatypes)):
                typename = str(model.datatypes[row][1])
                if typename in self.typedelegates:
                    ui.tableView.setItemDelegateForRow(row,self.typedelegates[typename][1](ui.tableView))
        self.setWindowTitle(title)
        if doc:
            ui.label.setText(doc)
        else:
            ui.label.setText(title)
        ui.tableView.resizeColumnsToContents()
        #XX not without reset function ### self.ui.tableView.horizontalHeader().sectionDoubleClicked.connect(self.resizeHheader)
        self.ui.tableView.verticalHeader().sectionDoubleClicked.connect(self.resizeVheader)
        # replace corner
        cb = self.ui.tableView.findChild(QtWidgets.QAbstractButton)
        if cb:
            cb.disconnect()
            cb.clicked.connect(self.adjustSize)

        # resize top window too?
        self.want_resize.emit()
        self.show()

    def adjustSize(self):
        hh = self.ui.tableView.horizontalHeader()
        vh = self.ui.tableView.verticalHeader()
        hw = hh.length() + vh.size().width()
        tw = self.ui.tableView.size().width()

        lastc = hh.count()-1
        lastw = hh.sectionSize(lastc)

        newtw = (hh.length()-lastw)*2 + vh.size().width()

        mw = self.size().width()
        frame = mw - tw
        #print("hw={} tw={} ntw={} mw={}".format(hw,tw,newtw, mw)) # DEBUG
        if newtw>tw:
            size = QtCore.QSize(newtw+frame+30, self.size().height())
            #print("resize {}".format(size.width())) # DEBUG
            self.resize(size)
  
    def resizeHheader(self, logical):
        self.ui.tableView.resizeColumnToContents(logical)
    def resizeVheader(self, logical):
        self.ui.tableView.resizeRowToContents(logical)

    @classmethod
    def registerType(cls, typec, delegate):
        cls.typedelegates[str(typec)] = [typec, delegate]
