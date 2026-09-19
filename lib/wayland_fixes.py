# This set of what should be unnecessary fixes is public domain

from functools import partial
from PyQt6.QtCore import QTimer, QSize, QCoreApplication
from PyQt6.QtWidgets import QApplication

# this replaces  self.resize(...)
def resize_window(window, w, h=None):
    if isinstance(w, QSize):
        h = w.height()
        w = w.width()
    if QApplication.platformName().startswith("wayland"):
        if not hasattr(window, 'origMinSize'):
            window.origMinSize = window.minimumSize()
        # more wayland fix attempts
        window.setMinimumSize(w,h)
        window.setMaximumSize(w,h)
        # XXX this time is arbitrary, tableviwer needs 500, rest is <200
        QCoreApplication.processEvents()
        QTimer.singleShot(500, partial(release_constraints, window))
    else:
        # reset max size in case we changed screens
        window.setMaximumSize(window.screen().size())
    window.resize(w,h)

def release_constraints(window):
    window.setMinimumSize(window.origMinSize)
    #window.setMaximumSize(16777215, 16777215)
    # don't ever want a window bigger than the screen in this app
    window.setMaximumSize(window.screen().size())
