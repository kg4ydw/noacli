# This set of what should be unnecessary fixes is public domain

from functools import partial
from PyQt6.QtCore import QTimer, QSize, QCoreApplication
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QSettings

from lib.typedqsettings import typedQSettings

from inspect import getframeinfo, stack


# Wayland resize bugs:
# * Wayland ignores window resize requests for shown windows unless
#   you fix the window size so it can't be changed.
# * If you send multiple resize requests, wayland honors them in a random order.
# * Sometimes wayland/Qt doesn't trigger resize events at all.
# To work around this, this code:
# * sets the window size to a fixed non-resizable size
# * counts the incoming resize events and retries if not the last size requested
# * When all resize events have been accounted for OR the timer expires,
#   relax the window size to allow the user to resize


# this replaces  self.resize(...)
def resize_window(window, w, h=None, *, force=False):
    if isinstance(w, QSize):
        h = w.height()
        w = w.width()
    if typedQSettings().value('DEBUG',False):
        caller = getframeinfo(stack()[1][0])
        #caller2 = getframeinfo(stack()[2][0])
        #print(f" at {caller.filename}:{caller.lineno}:{caller.function}") # DEBUG
    window.wantsize = QSize(w,h)
    if window.wantsize==window.size():
        if typedQSettings().value('DEBUG',False): print(f"want resize already got one [{window.windowTitle()}] to ({w},{h})  at {caller.filename}:{caller.lineno}:{caller.function}")
        return
    window.resizeCount = max(getattr(window,'resizeCount',0),0)+1
    if typedQSettings().value('DEBUG',False):
        if typedQSettings().value('DEBUG',False): print(f"want resize [{window.windowTitle()}] to ({w},{h})  prev={QSF(window.size())} at {caller.filename}:{caller.lineno}:{caller.function}")
    if QApplication.platformName().startswith("wayland"):
        # for every platform except wayland, window.resize is enough!
        window.setFixedSize(w,h)
        #if force:  # we don't expect resizeEvent to be called
        setTimer(window, 1200) # always set it because wayland doesn't always resize
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
    else: # don't shorten timer if we had one
        rt =  window.fixResizeTimer.remainingTime()
        if rt > msec:
            if typedQSettings().value('DEBUG',False):
                print(f"  continue timer {rt} {window.windowTitle()}") # DEBUG
            return
    window.fixResizeTimer.start(msec)
    if typedQSettings().value('DEBUG',False):
        print(f"  start timer {msec} {window.windowTitle()}") # DEBUG
    

# call this from window's resizeEvent slot
def release_constraints(window,ev=None):
    window.resizeCount = getattr(window,'resizeCount',1)-1
    if window.resizeCount > 0: # more coming
        setTimer(window, 200)
        return
    if window.resizeCount < 0:
        return # user is probably resizing window
    if not QApplication.platformName().startswith("wayland"):
        return  # nobody else needs this
    if not hasattr(window,'wantsize'):
        return  # not currently trying to resize
    if ev and window.wantsize != ev.size():
        if typedQSettings().value('DEBUG',False):
            print(f"rEv wrong {QSF(ev.size())} want {QSF(window.wantsize)}") # DEBUG
            # send another resize request
            window.resize(window.wantsize)
            window.resizeCount += 1
            setTimer(window, 200)
        return
    # release constraints too soon and wayland screws it up
    if hasattr(window,'fixResizeTimer'):
        window.rmtm = window.fixResizeTimer.remainingTime()
        window.fixResizeTimer.stop()
    else:
        window.rmtm = -3
    setTimer(window, 100)
    #delay_release_constraints(window) # immediate release triggers re-resize



def delay_release_constraints(window):
    if typedQSettings().value('DEBUG',False):
        print(f"release {window.windowTitle()} {getattr(window,'resizeCount',False)} wanted {QSF(window.wantsize)} to sz={QSF(window.size())} max={QSF(window.screen().availableGeometry().size())} remaining={getattr(window,'rmtm',-2)}") # DEBUG
    window.setMinimumSize(window.minimumSizeHint())
    # don't ever want a window bigger than the screen in this app
    # on scaled screens, wayland gets this wrong too
    window.setMaximumSize(window.screen().availableGeometry().size())
