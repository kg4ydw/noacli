
# simple tables and widgets
# contaminated with app specific classes and GUI pieces

from PyQt5.Qt import Qt, QAbstractTableModel, QBrush
from PyQt5.QtCore import QModelIndex, QProcess, QTimer, QObject
from qtail import QtTail

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
        return None
        
    # recommended: headerData
    def headerData(self, col, orientation, role):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal and col<self.ncols:
                return self.headers[col]
            elif orientation == Qt.Vertical and col<len(self.data):
                # if you don't like veritcal headers, turn them off in designer
                return str(col)
        return None
    
    # required for editing: setData flags
    # resizable: removeRows addRows
    # other: addHistory 

class itemListModel(QAbstractTableModel):
    # an array of items, where each item is a row
    def __init__(self, headers):
        QAbstractTableModel.__init__(self)
        self.data = [ ]
        self.headers = headers
    
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
        if role == Qt.DisplayRole and orientation == Qt.Horizontal and col<len(self.headers):
            return self.headers[col]
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
        item.index = self.index(lastrow,0) # and item remembers itself
        return item.index
        
class jobItem():
    def __init__(self, history):
        self.index = None
        self.history = history
        self.status = ''
        self.finished = False
        self.windowOpen = None
        self.fullstatus = None
        self.process = QProcess()
        self.setStatus('init')
        self.process.errorOccurred.connect(self.collectError)
        self.process.finished.connect(self.collectFinish)
        self.process.stateChanged.connect(self.collectNewstate)

    # private slots
    def collectError(self, err):
        self.status += 'E'+str(err)+' '
        self.setStatus(self.status)
        
    def collectFinish(self, exitCode, estatus):
        self.finished = True
        self.setStatus(self.status+'F'+str(exitCode)+':'+str(estatus),exitCode)
    def collectNewstate(self, state):
        if state==QProcess.Starting:
            self.setStatus(self.status+str('Starting'))
        if state==QProcess.Running:
            self.setStatus(self.status+str('Running'))
        # let finished take care of its own

    def setStatus(self, status,exitStatus=None):
        self.fullstatus = status
        if self.index:
            index = self.index.model().sibling(self.index.row(),1,QModelIndex())
            self.index.model().dataChanged.emit(index,index)
        if exitStatus!=None:
            self.history.model().setStatus(self.history, exitStatus)
        else:
            self.history.model().setStatus(self.history,status)

    # public interfaces
    def command(self):
        return self.history.model().getCommand(self.history)
    def getStatus(self):
        if self.fullstatus: return self.fullstatus
        if self.status: return self.status
        # make something up
        return str(self.process.state())
    
    def start(self):
        # XXX connect output to something
        # for now, just merge stdout,stderr and send to qtail
        self.process.setProcessChannelMode(QProcess.MergedChannels)
        self.process.closeWriteChannel() # close stdin if we have no infile XXX
        self.window = QtTail(None) # XXX options??
        self.window.window_close_signal.connect(self.windowClosed)
        self.windowOpen = True
        self.window.show()
        self.window.start()
        # XXX Do more parsing and give this a real title
        self.window.openProcess('subprocess' , self.process)
        #print('start command: '+self.command())
        self.process.start('bash', [ '-c', self.command() ])

    def windowClosed(self):
        self.windowOpen = False
        if self.index:
            index = self.index.model().sibling(self.index.row(),2,QModelIndex())
            self.index.model().dataChanged.emit(index,index)
        # XXX trigger cleanup?  maybe on a timer
        # self.index.model().cleanupJob(self.index)
                   
class jobTableModel(itemListModel):
    def __init__(self):
        itemListModel.__init__(self, [ 'pid', 'state', 'window', 'command'] )
        self.cleanTime = QTimer(self)
        self.cleanTime.timeout.connect(self.cleanup)
        # don't start it until we have data
    def data(self, index, role):
        if not self.validateIndex(index): return None
        col = index.column()
        job = self.data[index.row()]
        if role==Qt.BackgroundRole and col==2 and not job.windowOpen:
            return QBrush(Qt.gray)
        if role in [Qt.DisplayRole, Qt.UserRole, Qt.EditRole]:
            # if you update these, also udpate noacli.jobDoubleClicked
            if col==0: return job.process.processId()
            if col==1: return job.getStatus()
            if col==2: return job.window.windowTitle()
            if col==3: return job.command()
        return None

    def setData(self, index, value, role):
        if not self.validateIndex(index): return None
        col = index.column()
        if col!=2: return False  # only window title editable right now
        self.data[row].window.setWindowTitle(value)
        self.dataChanged.emit(index,index)
        return True
    # make window title editable
    def flags(self,index):
        if not index.isValid() or index.column()!=2:
            return super(jobTableModel,self).flags(index)
        return Qt.ItemIsSelectable|Qt.ItemIsEnabled| Qt.ItemIsEditable
    # can't delete a job unless it is dead, so don't implement removeRows
    def deleteJob(self,row):
        # skip validation
        self.beginRemoveRows(QModelIndex(),row,row)
        d = self.data.pop(row)
        # XXX clean up job internals?
        self.endRemoveRows()
        
    def cleanupJob(self, index):
        if not self.validateIndex(index): return None
        row = index.row()
        job = self.data[row]
        if job.finished and not job.windowOpen:
            self.deleteJob(row)
        
    # delete all dead jobs
    def cleanup(self):
        #print('cleanup')
        i=0
        while i<len(self.data): # XXX watch for infinite loops!
            if self.data[i].finished and self.data[i].windowOpen==False:
                self.deleteJob(i)
            else:
                i +=1
        if len(self.data)<1: self.cleanTime.stop()

    def newjob(self, jobitem):
        self.appendItem(jobitem)
        # start a cleanup timer
        self.cleanTime.start(120000) # XXX 2m, should be a settable option

class historyItem():
    def __init__(self, status, command):
        self.status = status
        self.command = command
        
class History(itemListModel):
    def __init__(self):
        super(History,self).__init__(['exit', 'command'])

    # format cells
    def data(self, index, role):
        if not self.validateIndex(index): return None
        item = self.getItem(index)
        col = index.column()
        if role==Qt.BackgroundRole and col==0:
            st = item.status
            if st==None: return QBrush(Qt.gray)
            if st==0 or st=='F0:0':
                return QBrush(Qt.green)
            elif isinstance(st,str) and len(st)>1:
                if st[1]=='1': return QBrush(Qt.red) # XX or any number?
                else: return QBrush(Qt.yellow)
            elif st: return QBrush(Qt.red)
            else: return None
        elif role in [Qt.DisplayRole, Qt.UserRole, Qt.EditRole]:
            if col==0: return item.status
            elif col==1: return item.command
        return None

    #def setData(self, index, value, role):
    #    return False  # can't edit history
    #def parent(self,index):
    #    return QModelIndex()
    def first(self):
        return self.index(0,1)
    def last(self):
        return self.index(len(self.data)-1,1)
    def next(self, idx):
        if not idx or not idx.isValid(): return self.first()
        row = idx.row()+1
        if row>=len(self.data): row=0
        return self.index(row,1)
    def prev(self, idx):
        if not idx or not idx.isValid(): return self.last()
        row = idx.row()-1
        if row<0: row= len(self.data)-1
        return self.index(row,1)

    def saveItem(self, command, index, exitval):
        # XX if exitval==None and isValid(index) replace existing entry
        # else append
        if self.validateIndex(index) and exitval==None:
            item = self.getItem(index)
            if item.status==None:
                item.command = command
                i = index.siblingAtColumn(1)
                self.dataChanged.emit(i,i)
                return i
        item = historyItem(exitval, command)
        return self.appendItem(item)

    def getCommand(self, index):
        if not self.validateIndex(index): return
        return self.data[index.row()].command
    def setStatus(self, index, status):
        if not self.validateIndex(index): return
        row = index.row()
        self.data[row].status = status
        i = index.siblingAtColumn(0)
        self.dataChanged.emit(i,i)
    
    def read(self, file=None):
        # simple history data model for now, add frequency later
        # [ exitval, command ]
        if file:
            fname = file
        else:
            try:
                fname = os.environ.get('HOME') +'/'
            except:
                fname= ''
            fname += '.noacli_history'

        try:
            hfile = open(fname, 'r')
        except:
            self.data = [ ]
            self.layoutChanged.emit([])
            return
        # XXXX parse file and insert data
        #while (l=hfile.read
        close(hfile)
 
