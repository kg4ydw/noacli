
# receiver for output from multiple processes

import os
import sys
import re

from PyQt5 import QtCore
from PyQt5.Qt import Qt, pyqtSignal
from PyQt5.QtCore import QTimer, QSettings, QTextStream, QProcess
from PyQt5.QtGui import QTextCursor, QImage, QTextOption
from PyQt5.QtWidgets import QTextBrowser

from typedqsettings import typedQSettings
from noajobs import jobItem
from qtail import QtTail
from functools import partial

# features:
#  collect logs from multiple processes
#  each line tagged (pid, command?)
#  collect stderr separate from stdout? (small vs. log)
#  search (simple, regex?)
#  tail
#  notification filters (regex, pid, command, whitelist, blacklist)?
#  adjust word wrap mode
#  move process back to smalloutput or qtail?
#  filter log: hide/show by pid or regex
#  context menu
#    search options (find next/prev)
#    kill
#    filter options (show/hide/set)
#    delete

# bugs: QProcess.atEnd is different from (non-existant) QTextStream.atEnd()


class logOutput(QTextBrowser):
    oneLine = pyqtSignal(str)
    readmore = pyqtSignal(jobItem)
    
    def __init__(self, parent):
        super().__init__(parent)
        self.joblist=set()
        self.findcount = 0
        self.followCheck = True
        self.searchtext = None
        self.applySettings()
        # if a fixed number is set, use it, otherwise delay this
        self.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere) # SETTING
        self.readmore.connect(self.readLines, Qt.QueuedConnection)  # for delayed reads
        self.show()

    def applySettings(self):
        qs = typedQSettings()
        max = qs.value('LogMaxLines',10000)
        self.document().setMaximumBlockCount(max)

    ######## process and I/O handling stuff
        
    def endCursor(self):
        c = self.textCursor()
        c.movePosition(QTextCursor.End)
        if self.followCheck:
            self.setTextCursor(c) # jump to end
        return c

    # call triggered by dcommand processor
    def openProcess(self, process, jobitem, settings, pretext='', title=''):
        # XXX we don't use title here, but should we?
        self.settings = settings  # need this for qtail
        self.joblist.add(jobitem)
        jobitem.process = process
        jobitem.textstream = QTextStream(process)
        ## do this in job item XX
        #p = process.processId()
        #if p: jobitem.pid = p # don't accidentally zero it
        #jobitem.prefix = str(jobitem.pid)+': ' # XXX buggy
        jobitem.setMode('Log')
        self.connectProcess(jobitem)
        c = self.endCursor()
        p = jobitem.getpid()
        if p==0: # instead of logging start, schedule this for later
            c.insertHtml('Early: <b>Start log</b> <br/>')
            c.insertText("\n")
            jobitem.process.started.connect(partial(self.processStarted,jobitem))
        else:
            c.insertHtml(str(jobitem.getpid())+': <b>Start log</b> <br/>')
            c.insertText("\n")
        if pretext: # pid should be set by now, so this should work
            for line in str.splitlines():
                c.insertText(str(jobitem.getpid())+': (S) '+line+"\n")

    def processStarted(self, jobitem):
        # couldn't do this earlier
        c = self.endCursor()
        c.insertHtml(str(jobitem.getpid())+': <b>Start log</b> <br/>')
        c.insertText("\n")

    def receiveJob(self, jobitem):
        # like openProcess but jobitem already packed up
        self.joblist.add(jobitem)
        #jobitem.pid = jobitem.process.processId() # XX do this in jobitem
        #jobitem.prefix = str(jobitem.pid)+': ' # this works, but not above
        jobitem.setMode('Log') # XX redundant?
        c = self.endCursor()
        c.insertHtml(str(jobitem.getpid())+': <b>Start log</b> <br/>')
        c.insertText("\n")
        self.connectProcess(jobitem)
                
    def connectProcess(self, jobitem):
        jobitem.lc1 = jobitem.process.readyRead.connect(partial(self.readLines, jobitem))
        jobitem.lc2 = jobitem.process.finished.connect(partial(self.procFinished, jobitem))

    def disconnectProcess(self, jobitem):
        if not hasattr(jobitem,'process') or not jobitem.process: return
        self.disconnect(jobitem.lc1)
        self.disconnect(jobitem.lc2)
        #p = jobitem.process
        #p.readyRead.disconnect(partial(self.readLines,jobitem))
        #p.finished.disconnect(partial(self.procFinished,jobitem))

    def readLines(self, jobitem):
        # For now, this will read up to 10 lines and then move on,
        # so one process can't cause performance issues.  Also, high
        # volume procs should probably be throttled or moved out of
        # the log window.
        lines = typedQSettings().value('LogBatchLines',5)
        e = self.endCursor()
        e.beginEditBlock()
        jobitem.hasmore = True
        # note: when reading textstream, don't worry about what's unread in fd
        while lines>0:
            t = jobitem.textstream.readLine()
            if t:
                e.insertText(str(jobitem.getpid())+': '+t+"\n")
            else:
                jobitem.hasmore = False
                break
            lines -= 1
        e.endEditBlock()
        if jobitem.hasmore or jobitem.process.canReadLine():
            if not jobitem.paused:  # more to read but we're not ready
                self.readmore.emit(jobitem)
        elif jobitem.process.atEnd() and jobitem.process.state()==QProcess.NotRunning:
            self.cleanProc(jobitem)
        if self.followCheck:
            self.setTextCursor(e)

    def pauseJob(self, jobitem):
        jobitem.paused = True
        self.disconnectProcess(jobitem)
        bytes = 0
        if jobitem.process:
            bytes = jobitem.process.bytesAvailable()
            c = self.endCursor()
            c.insertText("{} paused with {} bytes available\n".format(jobitem.pid, bytes))
    def resumeJob(self,jobitem):
        jobitem.paused = False
        self.connectProcess(jobitem)
        self.readmore.emit(jobitem)
    
    def procFinished(self, jobitem, exitcode, estatus):
        c = self.endCursor()
        c.insertHtml('{}: <b>Exit {}</b> <br/>'.format(jobitem.pid, exitcode))
        c.insertText("\n")
        if exitcode:
            self.oneLine.emit('E({})'.format(exitcode))
        else:
            self.oneLine.emit('(exit)')
        # make sure there's no more data
        if jobitem.hasmore and jobitem.process.atEnd():
            self.readLines(jobitem) # one more can't hurt
        if not jobitem.hasmore and jobitem.process.atEnd():
            self.cleanProc(jobitem)
        else:
            print("Not cleaned at exit: pid={} m={} e={}".format(jobitem.pid, jobitem.hasmore, jobitem.process.atEnd())) # EXCEPT

    def cleanProc(self, jobitem):
        if jobitem and jobitem.process:
            if jobitem.hasmore or not jobitem.process.atEnd():
                print("cleanproc too soon m={} e={} b={}".format(jobitem.hasmore, jobitem.process.atEnd(), jobitem.process.bytesAvailable())) # EXCEPT
                return
            self.disconnectProcess(jobitem)
            c=self.endCursor()
            if jobitem in self.joblist:
                c = self.endCursor()
                c.insertHtml('{}: <b>Exit {}</b> <br/>'.format(jobitem.pid, jobitem.process.exitCode()))
                c.insertText("\n")
                self.joblist.discard(jobitem)  # XXX clean anything first?
            

    ######## GUI stuff
    @QtCore.pyqtSlot(int)
    def setFollowCheck(self, checked):
        self.followCheck = checked
        if checked: self.endCursor()  # scroll immediately

    @QtCore.pyqtSlot(str)
    def simpleFind(self, text=None):
        if not text and self.searchtext:
            text = self.searchtext
        if not text: return
        start = self.textCursor()
        success = self.find(text)
        if success:
            self.findcount += 1
            #XX self.statusBar().showMessage('Found '+str(self.findcount))
        else:
            # try again
            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.Start)
            self.setTextCursor(cursor)
            success = self.find(text)
            if success:
                # XXX need a status bar
                #if self.findcount:
                #    m = 'Wrapped after '+str(self.findcount)
                #else:
                #    m = 'Wrapped'
                #self.statusBar().showMessage(m)
                self.findcount = 1;
            else:
                self.setTextCursor(start)
                #XX self.statusBar().showMessage('Not found')
    
    @QtCore.pyqtSlot(str)
    def simpleFindNew(self, text):
        self.searchtext = text
        self.findcount = 0
        self.simpleFind(text)

    @QtCore.pyqtSlot()
    def simpleFind2(self):
        self.simpleFind(self.searchtext)

    def findPid(self, pid):
        jobs = [j for j in self.joblist if j.pid==pid]
        if len(jobs)==1:
            return next(iter(jobs))
        else:
            return None
        
    def contextMenuEvent(self, event):
        m=super().createStandardContextMenu(event.pos())
        c = self.cursorForPosition(event.pos())
        # get pid
        c.movePosition(QTextCursor.StartOfLine)
        c.movePosition(QTextCursor.NextWord, QTextCursor.KeepAnchor)
        pidT = c.selectedText()
        
        job = None
        if pidT and pidT.isnumeric():
            pid = int(pidT)
            job = self.findPid(pid)
        if job and job.process and job.process.state()==QProcess.Running:
            m.addAction("Kill pid "+pidT, partial(self.termJob,job))
            m.addAction("Kill pid {} hard".format(pidT),partial(self.killJob,job))
        elif pidT:
            m.addAction("Delete log for pid "+pidT, partial(self.delLog,pidT))
        #if job and job.process!=None: # DEBUG
        #    print("bytes={} paused={} textstream={}".format(job.process.bytesAvailable(),job.paused, job.textstream.status())) # DEBUG
        if job and job.textstream:
            m.addAction("Flush output",job.textstream.flush)
            if job.paused:
                try:
                    status = str(job.process.bytesAvailable())+' bytes'
                except:
                    status = ''
                m.addAction("Resume this pid "+status, partial(self.resumeJob,job))
            else:
                m.addAction("Pause this pid",partial(self.pauseJob,job))
        if job!=None:
            skipjob = job.pid
        else:
            skipjob = 0
        deadjobs = set()
        for job in self.joblist:
            if not job.paused or job.pid==skipjob: continue
            m.addAction("Resume pid {} at {} bytes".format(job.pid, job.process.bytesAvailable()) , partial(self.resumeJob,job))

            # XXX autopause if bytes waiting > threshold
        m.addAction("Clear finished jobs from log",self.clearDead)
        if self.joblist:
            m.addAction("Check status of log jobs",self.checkStatus)
        # XXX log context menu missing items
        # search options
        # Unfortuantely as of Qt 5.15 block.setVisibility doesn't do anything useful so can't filter log

        action = m.exec_(event.globalPos())
        # non-context sensitive stuff handlers go here

    def termJob(self, job):
        job.process.terminate()
    def killJob(self,job):
        job.process.kill()
    def delLog(self, pidT):
        if not pidT or len(pidT)==0:
            print("empty del log") # EXCEPT DEBUG
            return
        c = self.textCursor()
        c.movePosition(QTextCursor.Start)
        c.beginEditBlock()
        while not c.atEnd():
            if c.block().text().startswith(pidT):
                c.movePosition(QTextCursor.NextBlock, QTextCursor.KeepAnchor)
                c.removeSelectedText()
            else:
                c.movePosition(QTextCursor.NextBlock, QTextCursor.MoveAnchor)
        c.endEditBlock()
    def clearDead(self):
        # we don't have a list of dead jobs, so just delete everything not in joblist
        okjobs = [str(job.pid) for job in self.joblist]
        c = self.textCursor()
        c.movePosition(QTextCursor.Start)
        c.beginEditBlock()
        while not c.atEnd():
            (start,_,_) = c.block().text().partition(':')
            if start not in okjobs:
                c.movePosition(QTextCursor.NextBlock, QTextCursor.KeepAnchor)
                c.removeSelectedText()
            else:
                c.movePosition(QTextCursor.NextBlock, QTextCursor.MoveAnchor)
        c.endEditBlock()
    def checkStatus(self):
        c=self.endCursor()
        c.beginEditBlock()
        for job in self.joblist:
            t = []
            if job.paused: t.append('Paused')
            if job.process:
                s = job.process.state() # this doesn't seem to really be an enum
                if s==0: ss='Dead'
                elif s==1: ss='Starting'
                elif s==2: ss='Running'
                else: ss='Unknown'
                t.append(ss)
            if job.window: # not possible yet
                t.append('window')
            c.insertText(" ".join([str(job.getpid())+':']+ t)+"\n")
        c.endEditBlock()
