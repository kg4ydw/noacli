

from PyQt5 import QtCore
from PyQt5.Qt import Qt, pyqtSignal
from PyQt5.QtWidgets import QDockWidget

class myDock(QDockWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.basetitle = 'dock'

    @QtCore.pyqtSlot(str)
    def setWindowTitle(self, title):
        # XXX only change number of lines if not visible?
        self.basetitle = title
        self.newlines = 0
        super().setWindowTitle(title)

    @QtCore.pyqtSlot(int)
    def newLines(self, num):
        if num<0:
            self.newlines=0
        else:
            self.newlines += num
        self.adjustTitle()

    def resetLines(self):
        self.newlines = 0
        self.adjustTitle()

    def  adjustTitle(self):
        visible =  not self.visibleRegion().isEmpty() # XX not perfect
        if visible:
            self.newlines=0
        # do we need to throttle changing title when it doesn't need changed?
        if self.newlines==0:
            super().setWindowTitle(self.basetitle)
        else:
            super().setWindowTitle("{} ({})".format(self.basetitle, self.newlines))
    # this is never called
    #def visibilityChanged(self, visible):
    #    # XXX also check tabifiedDockWidgets(myDock).isEmpty())
    #    print("dock change "+str(visible))
    #    if visible:
    #        self.newlines = 0
    #        self.adjustTitle()
            
