# This set of what should be unnecessary fixes is public domain

from functools import partial
from PyQt6.QtCore import QTimer, QSize, QCoreApplication
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QSettings

from lib.typedqsettings import typedQSettings


# this replaces  self.resize(...)
def resize_window(window, w, h=None, *, force=False):
    if isinstance(w, QSize):
        h = w.height()
        w = w.width()
    window.wantsize = QSize(w,h)
    if typedQSettings().value('DEBUG',False):
        if typedQSettings().value('DEBUG',False): print(f"want resize [{window.windowTitle()}] to ({w},{h})  prev={QSF(window.size())}")
    if QApplication.platformName().startswith("wayland"):
        # for every platform except wayland, window.resize is enough!
        window.setFixedSize(w,h)
        window.startResizeWait = True
        if force:  # we don't expect resizeEvent to be called
            setTimer(window, 1000)
    else:
        # not wayland, just set the max for good luck
        window.setMaximumSize(window.screen().availableGeometry().size())
    window.resize(w,h)


def QSF(qs):
    return f"({qs.width()},{qs.height()})"


def adjustWindowSize(window):
    window.updateGeometry()
    window.layout().activate()
    window.setMaximumSize(window.screen().availableGeometry().size())
    window.setMinimumSize(window.minimumSizeHint())
    

### every window that calls resize_window needs something like the following
#    def resizeEvent(self,ev):
#        super().resizeEvent(ev)
#        release_constraints(self,ev)


def setTimer(window, msec):
    if not hasattr(window, 'fixResizeTimer'):
        window.fixResizeTimer=QTimer(window)
        window.fixResizeTimer.setSingleShot(True)
        window.fixResizeTimer.timeout.connect(partial(delay_release_constraints,window))
    window.fixResizeTimer.start(msec)
    if typedQSettings().value('DEBUG',False):
        print(f"  start timer {msec} {window.windowTitle()}") # DEBUG
    

# call this from window's resizeEvent slot
def release_constraints(window,ev=None):
    if not QApplication.platformName().startswith("wayland"):
        return  # nobody else needs this
    if not hasattr(window,'wantsize') or not getattr(window, 'startResizeWait',True):
        return  # not currently trying to resize
    if ev and window.wantsize != ev.size():
        if typedQSettings().value('DEBUG',False):
            print(f"rEv wrong {ev.size()} want {QSF(window.wantsize)}") # DEBUG
        return
    # release constraints too soon and wayland screws it up
    setTimer(window, 200)


def delay_release_constraints(window):
    if typedQSettings().value('DEBUG',False):
        print(f"release {window.windowTitle()} to sz={QSF(window.size())} max={QSF(window.screen().availableGeometry().size())}") # DEBUG
    window.startResizeWait = False
    window.setMinimumSize(window.minimumSizeHint())
    # don't ever want a window bigger than the screen in this app
    # on scaled screens, wayland gets this wrong too
    window.setMaximumSize(window.screen().availableGeometry().size())
