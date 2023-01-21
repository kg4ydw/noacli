
__license__   = 'GPL v3'
__copyright__ = '2022, 2023, Steven Dick <kg4ydw@gmail.com>'

# Add a few features to QDockWidget to
# * make activity in log windows obvious.
# * resize to use available space
# * work around a dock close bug in Qt

from PyQt5 import QtCore
from PyQt5.Qt import Qt, pyqtSignal
from PyQt5.QtWidgets import QDockWidget, QAbstractScrollArea, QWidget

class myDock(QDockWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.keeplines = False
        self.newlines = 0
        self.basetitle = 'dock'
        self.visibilityChanged.connect(self.adjustTitle)
        self.topLevelChanged.connect(self.resizeOnFloat)

    def resizeOnFloat(self, float):
        if not float: return
        # resize the dock when it floats to get rid of horizontal scrollbar
        # but try to not grow every time we are floated
        o = self.findChild(QAbstractScrollArea)
        if o:
            hw =  o.sizeHint().width()
            w = self.size().width()
            frame = w  - o.viewport().size().width()
            nw = hw+frame # + 50  # XX 50 is a guess
            hsbv = o.horizontalScrollBar().isVisible()
            #print('sbv={} w={} hw={} ow={} vsw={} nw={}'.format(hsbv, w, hw ,o.size().width(),  o.viewport().size().width(),nw)) # DEBUG
            if hsbv and w==nw: # hint wasn't enough to get rid of HScrollBar
                nw += 20
            if nw>w and hsbv:
                self.resize(QtCore.QSize(nw, self.size().height()))
        else:
            # alternately, resize by height if it doesn't have a scroll bar
            # but dock doesn't inherit widget's layout policy so calculate
            # the size difference and then get the widget size
            w = self.widget()
            hs = w.sizeHint()
            s = w.size()
            diff = self.size()-s
            # is best size based on hint or height for width?
            hh = w.heightForWidth(s.width())
            if hh<10 or hs.height() < hh:
                hh = hs.height()
            if s.height() < hh:
                self.resize(QtCore.QSize(s.width(), hh)+diff)
        
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

    def resetLines(self, val=0):
        self.newlines = val
        self.adjustTitle()

    def  adjustTitle(self):
        visible =  not self.visibleRegion().isEmpty() # XX not perfect
        if visible and not self.keeplines:
            self.newlines=0
        # do we need to throttle changing title when it doesn't need changed?
        if self.newlines==0:
            super().setWindowTitle(self.basetitle)
        elif self.keeplines: # display kept count differently
            super().setWindowTitle("{} [{}]".format(self.basetitle, self.newlines))
        else:
            super().setWindowTitle("{} ({})".format(self.basetitle, self.newlines))

    # bug workaround for QTBUG-74606 Oct 2021, fixed in Qt 6.11+? buggy in 5.15.3
    def closeEvent(self, event):
        if self.isFloating():
            self.setFloating(False)
            self.hide()
            event.ignore()
        else:
            super().closeEvent(event)
