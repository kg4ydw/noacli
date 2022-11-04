
# simple tables and widgets

from PyQt5.Qt import Qt, QAbstractTableModel
from PyQt5.QtWidgets import QTableView

class simpleTable(QAbstractTableModel):
    def __init__(self,data, headers ):
        QAbstractTableModel.__init__(self)
        self.data = data
        self.headers = headers
        self.ncols = len(self.headers)
        #super(simpleTable).__init__(self)
    # required functions rowCount columnCount data
    def rowCount(self, parent):
        return len(self.data)
    def columnCount(self, parent):
        return self.ncols
    def data(self, index, role):
        if not index.isValid():
            return None;
        row = index.row()
        col = index.column()
        if row < 0 or col<0 or row >= len(self.data) or col>=self.ncols:
            return None
        if role in [Qt.DisplayRole, Qt.UserRole, Qt.EditRole]:
            return self.data[row][col]
        # XXX other roles?
        return None
        
    # recommended: headerData
    def headerData(self, col, orientation, role):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal and col<self.ncols:
            return self.headers[col]
        return None
    
    # required for editing: setData flags
    # resizable: removeRows addRows
    # other: addHistory 

        
