
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
from datamodels import jobItem
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



class logOutput(QTextBrowser):
    oneLine = pyqtSignal(str)
    readmore = pyqtSignal(jobItem)
    # XXX set a watcher on the maxlines option?
    
    def __init__(self, parent):
        super().__init__(parent)
        self.joblist=set()
        self.findcount = 0
        self.followCheck = True
        self.searchtext = None
        # apply settings
        qs = typedQSettings()
        max = qs.value('logMaxLines',10000)
        if max>0:
            self.document().setMaximumBlockCount(max)
        # if a fixed number is set, use it, otherwise delay this
        self.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere) # SETTING
        self.readmore.connect(self.readLines, Qt.QueuedConnection)  # for delayed reads
        self.show()

    ######## process and I/O handling stuff
        
    def endCursor(self):
        c = self.textCursor()
        c.movePosition(QTextCursor.End)
        if self.followCheck:
            self.setTextCursor(c) # jump to end
        return c

    def openProcess(self, process, jobitem, settings, pretext='', title=''):
        # XXX we don't use title here, but should we?
        self.settings = settings  # need this for qtail
        self.joblist.add(jobitem)
        jobitem.process = process
        jobitem.textstream = QTextStream(process)
        jobitem.prefix = str(process.processId())+': '
        jobitem.setMode('Log')
        self.connectProcess(jobitem)
        c = self.endCursor()
        if pretext:
            for line in str.splitlines():
                c.insertText(jobitem.prefix+'(S) '+line+"\n")

    def receiveJob(self, jobitem):
        # like openProcess but jobitem already packed up
        self.joblist.add(jobitem)
        jobitem.prefix = str(jobitem.process.processId())+': '
        jobitem.setMode('Log')
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
        # XXX For now, this will read up to 10 lines and then move on,
        # so one process can't cause performance issues.  Also, high
        # volume procs should probably be throttled or moved out of
        # the log window.
        lines = 10 # SETTING
        e = self.endCursor()
        while lines>0 and jobitem.process.canReadLine():
            t = jobitem.textstream.readLine()
            if t:
                e.insertText(jobitem.prefix+t+"\n")
            lines -= 1
        if jobitem.process.canReadLine():  # more to read but we're not ready
            self.readmore.emit(jobitem)
        elif jobitem.process.atEnd() and jobitem.process.state()==QProcess.NotRunning:
            self.cleanProc(jobitem)
        if self.followCheck:
            self.setTextCursor(e)
            
    def procFinished(self, jobitem, exitcode, estatus):
        # XXXX rewrite this?
        c = self.endCursor()
        c.insertHtml(jobitem.prefix+'<b>Exit {}</b> <br/>'.format(exitcode))
        c.insertText("\n")
        if exitcode:
            self.oneLine.emit('E({})'.format(exitcode))
        else:
            self.oneLine.emit('(exit)')
        if jobitem.process.atEnd():
            self.cleanProc(jobitem)

    def cleanProc(self, jobitem):
        self.disconnectProcess(jobitem)
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
        jobs = [j for j in self.joblist if j.process.processId()==pid]
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
        
        job = pid = killAct = deleteAct = None
        if pidT and pidT.isnumeric():
            pid = int(pidT)
            job = self.findPid(pid)
        if job and job.process and job.process.state()==QProcess.Running:
            killAct = m.addAction("Kill pid "+pidT)
        else:
            deleteAct = m.addAction("Delete log for pid "+pidT)
                    
        # XXX log context menu
        # search options
        # delete dead pid entries

        # Unfortuantely as of Qt 5.15 block.setVisibility doesn't do anything useful

        action = m.exec_(event.globalPos())
        # use action if things weren't attached above
        if job and action==killAct:
            job.process.kill()
        elif deleteAct and action==deleteAct:
            c = self.textCursor()
            c.movePosition(QTextCursor.Start)
            c.beginEditBlock()
            while not c.atEnd():
                if c.block().text().startswith(pidT):
                    c.movePosition(QTextCursor.NextBlock, QTextCursor.KeepAnchor)
                    c.removeSelectedText()
                else:
                    c.movePosition(QTextCursor.NextBlock, QTextCursor.KeepAnchor)
            c.endEditBlock()
        #elif action==

            
            
