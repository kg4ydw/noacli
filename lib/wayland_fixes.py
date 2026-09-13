# This set of what should be unnecessary fixes is public domain

from functools import partial
from PyQt6.QtCore import QTimer, QSize
from PyQt6.QtWidgets import QApplication

# this replaces  self.resize(...)
def resize_window(window, w, h=None):
    if isinstance(w, QSize):
        h = w.height()
        w = w.width()
    if QApplication.platformName().startswith("wayland"):
        # more wayland fix attempts
        window.setMinimumSize(w,h)
        window.setMaximumSize(w,h)
        # XXX this time is arbitrary, tableviwer needs 500, rest is <200
        QTimer.singleShot(500, partial(release_constraints, window))
    window.resize(w,h)

def release_constraints(window):
    window.setMinimumSize(200, 200) 
    window.setMaximumSize(16777215, 16777215) 
    
