
__license__   = 'GPL v3'
__copyright__ = '2022, Steven Dick <kg4ydw@gmail.com>'

# Do all the job manipulation (view and model) parts of noacli

from PyQt5.Qt import Qt, QBrush
from PyQt5.QtCore import QIODevice, QTimer, QModelIndex, QProcess
from datamodels import itemListModel
from qtail import QtTail
from typedqsettings import typedQSettings
from commandparser import OutWin
from tableviewer import TableViewer

import re   # use python re instead of Qt
import os


class jobItem():
    def __init__(self, history):
        self.index = None
        self.history = history
        self.status = ''
        self.finished = False
        self.windowOpen = None
        self.windowTitle = None
        self.fullstatus = None
        self.mode = None
        self.pid = None # QProcess deletes pid too fast
        self.window=None
        self.paused = False
        if history:  # only for real jobs
            self.setStatus('init')
            self.process = QProcess()
            self.process.started.connect(self.collectPid)
            self.process.errorOccurred.connect(self.collectError)
            self.process.finished.connect(self.collectFinish)
            self.process.stateChanged.connect(self.collectNewstate)
            self.hasmore = True
        else:  # fake jobitem for internal commands
            self.hasmore = False
            self.fullstatus=' '
            self.setStatus(' ')
            self.process = None
        # events this should/could receive to update view:
        #   process state change
        #   window state change
        #   window title change

    def getpid(self):
        if self.pid: return self.pid
        if self.process:
            self.pid = self.process.processId()
            return self.pid
    def __str__(self):  # mash some stuff together
        qs = typedQSettings()
        width = int(qs.value('JobMenuWidth', 30))
        s = str(self.getStatus())+' | '+str(self.title())+' | '+str(self.command())
        return str(s)[0:width]
    def title(self):
        # XXX if command starts with # then strip first line and set title # DOCUMENT?
        if self.windowTitle:
            title = self.windowTitle
        elif self.window:
            title = self.windowTitle = self.window.windowTitle()
        else:
            # XXX or get title from somewhere else?
            # maybe build it from command?
            title = ''
        return title
    def setTitle(self,title):
        if not title: return
        self.windowTitle = title
        if self.window:
            self.window.setWindowTitle(title)
            if self.index:
                # QPersistentIndex doesn't have sibling
                i = self.index.model().index(self.index.row(),3)
                if i and i.model():
                    i.model().dataChanged.emit(i,i)
    def setMode(self,mode):  # mode is set in command parser
        if type(mode)==OutWin:
            self.mode = mode
            return
        try:
            newmode = OutWin[mode]
            if newmode: 
                self.mode = OutWin[mode]
                if self.index:
                    i = self.index.model().index(self.index.row(),2)
                    i.model().dataChanged.emit(i,i)
            else:
               #if typedQSettings().value('DEBUG',False): print("Failed to convert winmode "+mode) # DEBUG
                pass
        except Exception as e:
            print(e) # EXCEPT
            pass

    # private slots
    def collectPid(self):
        self.pid = self.process.processId()
        
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
        if not self.history or not self.history.model(): # not a real job
            pass
        elif exitStatus!=None:
            self.history.model().setStatus(self.history, exitStatus)
        else:
            self.history.model().setStatus(self.history, status)

    # public interfaces
    def command(self):
        if not self.history: return None
        return self.history.model().getCommand(self.history)
    def getStatus(self):
        if self.fullstatus: return self.fullstatus
        if self.status: return self.status
        # make something up
        return str(self.process.state())
    
    def start(self, settings):
        self.process.setProcessEnvironment(settings.environment)
        # XXX connect output to something
        # for now, just merge stdout,stderr and send to qtail
        self.process.setProcessChannelMode(QProcess.MergedChannels)
        self.process.closeWriteChannel() # close stdin if we have no infile XXX
        outwin = self.mode
        #print('start mode: '+str(outwin)) # DEBUG
        if outwin==OutWin.QTail:
            #print("start qtail") # DEBUG
            self.setWindow(QtTail(settings.qtail))
            title = self.title()
            if not title or len(title)==0:
                title = typedQSettings().value('QTailDefaultTitle','subprocess')
            self.window.openProcess(title , self.process)
        elif outwin==OutWin.Log:
            #print("start log") # DEBUG
            settings.logOutputView.openProcess(self.process, self, settings)
        elif outwin==OutWin.Table:
            self.setWindow(TableViewer())
            self.window.app = settings.app
            title = self.title()
            if not title or len(title)==0:
                # does tableviewer get its own default title SETTING?
                title = typedQSettings().value('QTailDefaultTitle','subprocess')
            self.window.openProcess(title , self.process)
        else:
            self.setMode('Small')
            #print("start small") # DEBUG
            settings.smallOutputView.openProcess(self.process, self, settings)
        #print('start command: '+self.command())  # DEBUG
        # XXX split QSettings.value('SHELL')
        #XXX old # self.process.start('bash', [ '-c', self.command() ], QIODevice.ReadOnly|QIODevice.Text)
        
        self.process.start(self.args[0], self.args[1:], QIODevice.ReadOnly|QIODevice.Text)

    def setWindow(self,w):
        self.window = w
        self.window.window_close_signal.connect(self.windowClosed)
        self.windowOpen = True
        self.window.show()
        self.window.start()
        
    def windowClosed(self):
        self.windowOpen = False
        if self.index:
            index = self.index.model().sibling(self.index.row(),2,QModelIndex())
            self.index.model().dataChanged.emit(index,index)
        # XXX trigger cleanup?  maybe on a timer
        # self.index.model().cleanupJob(self.index)
                   
class jobTableModel(itemListModel):
    def __init__(self):
        itemListModel.__init__(self, [ 'pid', 'state','mode', 'window', 'command'] )
        self.cleanTime = QTimer(self)
        self.cleanTime.timeout.connect(self.cleanup)
        # don't start it until we have data

    def data(self, index, role):
        if not self.validateIndex(index): return None
        col = index.column()
        job = self.data[index.row()]
        if role==Qt.ToolTipRole: return(str(job.index.row())) # XXX DEBUG
        if role==Qt.BackgroundRole and col==3:
            if job.mode and not job.window:
                return QBrush(Qt.lightGray)
            if not job.windowOpen:
                return QBrush(Qt.gray)
        if role in [Qt.DisplayRole, Qt.UserRole, Qt.EditRole]:
            # if you update these, also udpate noacli.jobDoubleClicked
            # also in jobitem emits above
            if col==0 and job.process: return job.process.processId()
            if col==1: return job.getStatus()
            if col==2:
                if job.mode: return job.mode.name
                else: return None
            if col==3: return job.title()
            if col==4: return job.command()
        return None

    def setData(self, index, value, role):
        if not self.validateIndex(index): return None
        col = index.column()
        if col!=3: return False  # only window title editable right now
        self.data[index.row()].setTitle(value)
        self.dataChanged.emit(index,index)
        return True
    # make window title editable
    def flags(self,index):
        if not index.isValid() or index.column()!=3:
            return super().flags(index)
        return Qt.ItemIsSelectable|Qt.ItemIsEnabled| Qt.ItemIsEditable
    # can't delete a job unless it is dead, so don't implement removeRows
    def removeRows(self, row, parent):
        return False
    def deleteJob(self,row):
        # skip validation -- done elsewhere
        #XX refactor?
        self.beginRemoveRows(QModelIndex(),row,row)
        d = self.data.pop(row)
        # XXX clean up item internals?
        self.endRemoveRows()
        
    def cleanupJob(self, index):
        if not self.validateIndex(index): return None
        row = index.row()
        job = self.data[row]
        if job.finished and not job.windowOpen:
            self.deleteJob(row)
        
    # delete all dead jobs
    def cleanup(self):
        #print('cleanup') # DEBUG
        i=0
        while i<len(self.data): # watch for infinite loops!
            if self.data[i].finished and not self.data[i].windowOpen:
                self.deleteJob(i)
            else:
                i +=1
        if len(self.data)<1: self.cleanTime.stop()

    def newjob(self, jobitem):
        self.appendItem(jobitem)
        # start a cleanup timer
        qs = typedQSettings()
        ct = int(qs.value('JobCleanTime', 120))*1000  # could be float
        self.cleanTime.start(ct)

class historyItem():
    def __init__(self, status, command, count=1):
        self.status = status
        self.command = command
        self.count = count
        
class History(itemListModel):
    def __init__(self):
        super().__init__(['exit', 'command'])

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
        elif role in [Qt.DisplayRole, Qt.UserRole, Qt.EditRole, Qt.ToolTipRole]:
            if col==0:
                if role==Qt.ToolTipRole:
                    return item.count
                else:
                    return item.status
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
        if row>=len(self.data): return None # row=0  # let it go invalid at the end
        return self.index(row,1)
    def prev(self, idx):
        h = self.prevNoWrap(idx)
        if h: return h
        else: return self.last()

    def prevNoWrap(self, idx):
        if not idx or not idx.isValid(): return None
        row = idx.row()-1
        if row<0: return None
        else: return self.index(row,1)

    def saveItem(self, command, index, exitval, count=1):
        # if exitval==None and isValid(index) replace existing entry
        # else append to end of history
        if self.validateIndex(index) and exitval==None:
            item = self.getItem(index)
            if item.status==None:
                item.command = command
                i = index.model().index(index.row(),1)
                self.dataChanged.emit(i,i)
                return i
        self.limitHistorySize()
        # XXX SETTING: skip appending if this is a duplicate command and nodup option set?
        item = historyItem(exitval, command, count)
        return self.appendItem(item)

    def limitHistorySize(self):
        qs = typedQSettings()
        try:
            hsize = int(qs.value('HISTSIZE', 1000))
        except Exception as e:
            print(str(e)) # EXCEPT
            return
        if len(self.data)>hsize:
            # print("Deleting history overflow: "+str(d)) # DEBUG
            d = len(self.data)-hsize
            self.removeRows(0,d,QModelIndex())

    def getCommand(self, index):
        if not self.validateIndex(index): return
        return self.data[index.row()].command
    def setStatus(self, index, status):
        if not self.validateIndex(index): return
        row = index.row()
        self.data[row].status = status
        i = index.model().index(index.row(),0)
        self.dataChanged.emit(i,i)
    
    # slots used by historyView context menu
    def collapseDups(self):
        i = 1
        start = 0
        while i<=len(self.data):
            if i<len(self.data) and self.data[start].command == self.data[i].command:
                i +=1
            else:
                if start<i-1:  # keep earliest duplicate
                    nc = i-start-1
                    for j in range(start+1,i):
                        self.data[start].count += self.data[j].count
                    #print('remove: ({},{})={}'.format(start,i,nc)) # DEBUG
                    self.removeRows(start+1, nc, QModelIndex())
                start +=1 
                i = start+1
                          
    def countHistory(self):
        f = { }
        counts = { }
        for h in self.data:
            if h.command in f:
                f[h.command]+=1
                counts[h.command]+=h.count
            else:
                f[h.command]= 0  # undercount to not delete last entry
                counts[h.command] = h.count
        return (f,counts)

    def deletePrevDups(self):
        # index all commands and then delete early duplicates
        (f,counts) = self.countHistory()
        i=0
        # and now delete entries
        while i<len(self.data):
            c = self.data[i].command
            if c in f and f[c]>0:
                f[c] -= 1
                self.removeRow(i, QModelIndex())
            else:
                i += 1
        # run through the whole list and update count of remaining entries
        for h in self.data:
            if h.command in counts:
                h.count = counts[h.command]

    def getHistfilename(self):
        qs = typedQSettings()
        f = qs.value('HistFile','.noacli_history')
        if f[0]=='/': return f
        # it's a relative path, try to construct full path
        try:
            # XXX nonportable?
            fname = os.environ.get('HOME') +'/'
        except Exception as e:
            print(str(e)) # EXCEPT
            fname= ''
        fname += f
        return fname

    def read(self, filename=None):
        # simple history data model for now, add frequency later
        # [ exitval, command ]
        if filename:
            fname = filename
        else:
            fname = self.getHistfilename()
        e = re.compile("^\s*(\d*)(,(\d+))?\s*:\s*(\S.*)")
        try:
            file = open(fname, 'r')
        except:
            return # XX no history file?
        with file:
            for line in file:
                count = 1
                line = line.rstrip()
                m = e.fullmatch(line)
                if m:
                    (g1, _, count, cmd) = m.groups()
                    if g1=='': g1=None
                    else: g1 = int(g1)
                    if count and  count.isnumeric(): count=int(count)
                    else: count=1
                    last = self.saveItem(cmd, None, g1, count )
                else:
                    if last:
                        # attempt to append entry
                        d = last.model().getItem(last)
                        d.command += "\n"+line
                    else:
                        self.saveItem(line, None, '')
        self.layoutChanged.emit([])

    def write(self, filename=None):  # export?
        qs = typedQSettings()
        maxhf = int(qs.value('HISTFILESIZE', 1000))
        start = 0
        if len(self.data)>maxhf:
            start = len(self.data)-maxhf
        if filename:
            fname = filename
        else:
            fname = self.getHistfilename()
        with open(fname, 'w') as file:
            for ii in range(start,len(self.data)):
                i = self.data[ii]
                st = i.status
                if type(st)==int or (type(st)==str and st.isnumeric()):
                    # XXX this doesn't handle newlines!!!!
                    # handle embedded newlines in input parser (less safe)
                    file.write("{},{}: {}\n".format(st, i.count, i.command.strip()))
                else:
                    file.write(": {}\n".format(i.command.strip()))
        # print("history write of "+filename+" failed") # DEBUG

