
# simple tables and widgets
# contaminated with app specific classes and GUI pieces

from PyQt5.Qt import Qt, QAbstractTableModel, QBrush
from PyQt5.QtWidgets import QTableView
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
        # XXX other roles?
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

class jobItem():
    def __init__(self, history):
        print('create job') # XXXX
        self.history = history
        self.setStatus('init')
        self.status = ''
        self.finished = False
        self.windowOpen = None
        self.fullstatus = None
        self.process = QProcess()
        self.process.errorOccurred.connect(self.collectError)
        self.process.finished.connect(self.collectFinish)
        self.process.started.connect(self.collectStarted)
        self.process.stateChanged.connect(self.collectNewstate)
        
    # private slots
    def collectError(self, err):
        self.status += 'E'+str(err)+' '
        self.setStatus(self.status)
    def collectFinish(self, exitCode, estatus):
        self.finished = True
        self.setStatus(self.status+'F'+str(exitCode)+':'+str(estatus))
    def collectStarted(self):
        self.setStatus('started')
    def collectNewstate(self, state):
        self.setStatus(self.status+str(state))

    def setStatus(self, status):
        self.fullstatus = status
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
        # XXXX do more parsing and give this a real title
        self.window.openProcess('subprocess' , self.process)
        print('start command: '+self.command()) # XXXX
        self.process.start('bash', [ '-c', self.command() ])

    def windowClosed(self):
        self.windowOpen = False
        # XXX trigger cleanup?
                   
class jobTableModel(QAbstractTableModel):
    def __init__(self):
        QAbstractTableModel.__init__(self)
        self.joblist = []
        self.headers = [ 'pid', 'state', 'window', 'command']
        self.cleanTime = QTimer(self)
        self.cleanTime.timeout.connect(self.cleanup)
        # don't start it until we have data
        
    # required functions rowCount columnCount data
    def rowCount(self, parent):
        return len(self.joblist)
    def columnCount(self, parent):
        return len(self.headers)
    def data(self, index, role):
        if not index.isValid():
            return None;
        row = index.row()
        col = index.column()
        if row < 0 or col<0 or row >= len(self.joblist):
            return None
        if role in [Qt.DisplayRole, Qt.UserRole, Qt.EditRole]:
            job = self.joblist[row]
            # if you update these, also udpate noacli.jobDoubleClicked
            if col==0: return job.process.processId()
            if col==1: return job.getStatus()
            if col==2: return str(job.windowOpen)
            if col==3: return job.command()
        return None

    def jobItem(self, index):
        if not index.isValid(): return None
        row = index.row()
        if row<0 or row>=len(self.joblist): return None
        return self.joblist[row]

    # can't delete a job unless it is dead, so don't implement removeRows
    def deleteJob(self,row, parent):
        self.beginRemoveRows(QModelIndex(),row,row)
        d = self.joblist.pop(row)
        # XXX clean up?
        self.endRemoveRows()
        
    # XXXX trigger this somehow
    def cleanup(self):
        #print('cleanup')
        i=0
        while i<len(self.joblist): # XXX watch for infinite loops!
            if self.joblist[i].finished and self.joblist[i].windowOpen==False:
                self.deleteJob(i,self)
            else:
                i +=1
        if len(self.joblist)<1: self.cleanTime.stop()
        
    # recommended: headerData
    def headerData(self, col, orientation, role):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal and col<len(self.headers):
            return self.headers[col]
        return None

    def newjob(self, jobitem):
        lastrow = len(self.joblist)
        self.beginInsertRows(QModelIndex(), lastrow,lastrow)
        self.joblist.append(jobitem)
        self.endInsertRows()
        # start a cleanup timer
        self.cleanTime.start(120000) # XXX 2m, should be a settable option
        
class History(simpleTable):
    def __init__(self):
        super(History,self).__init__([], ['exit', 'command'])

    # format cells
    def data(self, index, role):
        row = index.row()
        col = index.column()
        if row<0 or row>=len(self.data):
            return None
        if role==Qt.BackgroundRole and col==0:
            st = self.data[row][0]
            if st==None: return QBrush(Qt.gray)
            if st==0 or st=='F0:0':
                return QBrush(Qt.green)
            elif isinstance(self.data[row][0],str) and len(st)>1:
                if st[1]=='1': return QBrush(Qt.red) # XX or any number?
                else: return QBrush(Qt.yellow)
            elif st: return QBrush(Qt.red)
            else: return None
        else:
            return super(History,self).data(index,role)

    def setData(self, index, value, role):
        return False  # can't edit history
    def parent(self,index):
        return QModelIndex()
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
        if index and index.isValid() and exitval==None:
            row = index.row()
            if self.data[row][0]==None:
                self.data[row][1] = command
                i = index.siblingAtColumn(1)
                self.dataChanged.emit(i,i)
                return i
        lastrow = len(self.data)
        self.beginInsertRows(self.parent(index),lastrow,lastrow)
        #self.data[lastrow] = [exitval, command]
        self.data.append([exitval, command])
        self.endInsertRows()
        return self.index(len(self.data)-1, 1)

    def getCommand(self, index):
        if not index or not index.isValid(): return
        row = index.row()
        # XX validate
        return self.data[row][1]
    def setStatus(self, index, status):
        if not index or not index.isValid(): return
        row = index.row()
        self.data[row][0] = status
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
            # XXX fake it for now
            self.data=[[0, "test"],
                   [1, 'fail'],
                   [None, 'editme'],
                   [None, 'editme2'],
                ]
            self.layoutChanged.emit([])
            return
        # XXX parse file and insert data
        close(hfile)
    
    # def add(self, exitval, command)
    def editLine(self, pos = None):
        if pos == None: pos = self.pos
        if not pos: pos=0
        if self.data[pos][0] == None:
            c = self.data[pos][1]
            self.delete(pos)
            return c
        else:
            return data[pos][1]
