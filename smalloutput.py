
# receiver window for small amounts of output, send to qtail if it gets big

import os
import sys

from PyQt5 import QtCore
from PyQt5.QtCore import QTimer, QSettings, QTextStream
from PyQt5.QtGui import QTextCursor
from PyQt5.QtWidgets import QTextBrowser

from typedqsettings import typedQSettings

#  transfer last command output to qtail if:
#    output exceeds visible lines-1
#    process exit timeout
#    another command is run that produces output
#    user presses dup button (or shortcut?)
#  single line (or most recent?) output sent to status bar
#  don't remember more than visisible lines * 2 (option setting?)
#  option: disable small output window and send everything to qtail
#    auto
#    configured only (default qtail)
#    forced (disable auto-qtail)


## things to implement
# connect process
# set timeout
# read and count lines
# transfer to qtail
# clear buffer on next process
# reset max lines between processes if possible

class smallOutput(QTextBrowser):
    def __init__(self, parent):
        super(smallOutput,self).__init__(parent)
        self.keepState = False
        self.procCursor = None  # cursor
        self.rawtext = None  # keep raw text for later use
        self.process = None
        
        # apply settings
        qs = typedQSettings()
        mul = qs.value('SmallMultiplier', 2)
        # if a fixed number is set, use it, otherwise delay this
        if mul>10:
            self.document().setMaximumBlockCount(mul)
            
        
    ##### overrides
    def resizeEvent(self, event):
        super(smallOutput,self).resizeEvent(event)
        # XXX calculate new size
        doc = self.document()
        margin = doc.documentMargin()
        num_lines = (doc.size().height() - 2*margin)/self.fontMetrics().height()
        qs=typedQSettings()
        mul = qs.value('SmallMultiplier', 2)
        if mul>0 and mul<10:
            self.document().setMaximumBlockCount(int(num_lines * mul)+1)
        elif mul>10:  # reset it just in case it was changed
            self.document().setMaximumBlockCount( mul)
        else:
            self.document().setMaximumBlockCount(0)  # no limit

    ##### external signals
    @QtCore.pyqtSlot()
    def smallDup(self):
        # duplicate contents to a new top level small window (or qtail)
        text = self.ui.smallOutputView.text() # XXXX wrong function
        # QtTail.openPretext(pretext=text) # XXXX
        self.ui.smallOutputView.clear()
        pass # XXXX
    @QtCore.pyqtSlot(bool)
    def smallKeepToggle(self, checked):
        # if checked, clear immediately
        if checked: self.ui.smallOutputView.clear()
        self.keepState = checked

    def insertLine(self):
        c = self.textCursor()
        c.movePosition(QTextCursor.End)
        c.insertHtml("<hr/>")

    def getProcCursor(self):
        if not self.curProcStart:
            self.procCursor = self.textCursor()
            self.procCursor.movePosition(QTextCursor.End)
            # XXX alternately, find previous <hr> or move to start
        self.procCursor.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)
        return self.procCursor

    #### convenience functions
    def maxBlocks(self):
        return self.document().maximumBlockCount()
    def curBlock(self):
        return self.getProcCursor().blockNumber()
    
    ##### dunno if any of these are useful or correct yet
    def textLen(self):
        c = self.getProcCursor()
        return c.position() - c.anchor()

    def textBlockLen(self):
        b = getProcCursor()
        # not sure this is right
        a = self.textCursor().setPosition(b.anchor(), QTextCursor.NextCharacter)
        return b.blockNumber() - a.blockNumber()

    ################
    # process and I/O handling stuff

    # this class only handles process data, otherwise use qtail
    def openProcess(self, process):
        self.process = process
        self.textstream = QTextStream(process)
        self.opt.file = False
        self.file.readyRead.connect(self.readLines)
        self.file.finished.connect(self.procFinished)
        qs = typedQSettings()
        # XXX start oneshot timer
	
        

    def readLines(self):
        pass # XXXX
    def procFinished(self, exitcode, estatus):
        # XXX need to check if all data is read before adding status info
        # finishread
        if self.maxBlocks()>0 and self.curBlock() +2 < self.maxBlocks():
            c = getProcCursor()
            # XXX get time left / measured on timer
            c.insertHtml("<b>Exit {}<b><hr>".format(exitcode))
        pass # XXXX

    def timeoutProc():
        pass
