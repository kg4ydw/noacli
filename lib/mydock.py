
__license__   = 'GPL v3'
__copyright__ = '2022, 2023, 2026, Steven Dick <kg4ydw@gmail.com>'

# Add a few features to QDockWidget to
# * make activity in log windows obvious.
# * resize to use available space

from PyQt6 import QtCore
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QDockWidget, QAbstractScrollArea, QWidget
from lib.wayland_fixes import resize_window, release_constraints, adjustWindowSize, QSF


class myDock(QDockWidget):
    def __init__(self, parent, name='dock'):
        super().__init__(parent)
        self.setObjectName(name)
        self.basetitle = name
        self.keeplines = False
        self.newlines = 0
        self.visibilityChanged.connect(self.adjustTitle)
        self.topLevelChanged.connect(self.resizeOnFloat)

    def resizeOnFloat(self, floatw):
        scrsz = self.screen().availableGeometry().size()
        if not floatw:
            # reset size limits in case we fixed them previously
            self.setMinimumSize(100,100)
            #self.setMinimumSize(self.minimumSizeHint()) # seems to be too big
            self.setMaximumSize(scrsz)
            # and cancel the resize timer if there is one
            if hasattr(self, 'fixResizeTimer'):
                self.fixResizeTimer.stop()
            return
        # resize the dock when it floats to get rid of horizontal scrollbar
        # but try to not grow every time we are floated
        # XXX should this resize height too?
        o = self.findChild(QAbstractScrollArea)
        scrh = scrsz.height()//2
        if o:
            #print(f"dock {self.windowTitle()} size={QSF(self.size())} min={QSF(self.minimumSizeHint())} hint={QSF(self.sizeHint())}") # DEBUG
            hw = o.sizeHint().width()
            hh = min(o.sizeHint().height(), scrh)
            # print(f"  sub early=({hw},{hh}) size={QSF(o.size())} min={QSF(o.minimumSizeHint())} hint={QSF(o.sizeHint())}") # DEBUG
            w = self.size().width()
            frame = w - o.viewport().size().width()
            nw = hw+frame       # + 50  # XX 50 is a guess
            hsbv = o.horizontalScrollBar().isVisible()
            #print('sbv={} w={} hw={} ow={} vsw={} nw={}'.format(hsbv, w, hw ,o.size().width(),  o.viewport().size().width(),nw)) # DEBUG
            if hsbv and w==nw:  # hint wasn't enough to get rid of HScrollBar
                nw += 20
            if nw>w and hsbv or hh>self.size().height():
                resize_window(self, nw, hh)  # hh: self.size().height())
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
                resize_window(self, QtCore.QSize(s.width(), hh)+diff)

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        if self.isFloating():
            release_constraints(self,ev)
        else:
            self.setMinimumSize(self.minimumSizeHint())
            self.setMaximumSize(self.screen().availableGeometry().size())

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

    def adjustTitle(self):
        visible = not self.visibleRegion().isEmpty()  # XX not perfect
        if visible and not self.keeplines:
            self.newlines=0
        # do we need to throttle changing title when it doesn't need changed?
        if self.newlines==0:
            super().setWindowTitle(self.basetitle)
        elif self.keeplines:    # display kept count differently
            super().setWindowTitle("{} [{}]".format(self.basetitle, self.newlines))
        else:
            super().setWindowTitle("{} ({})".format(self.basetitle, self.newlines))
