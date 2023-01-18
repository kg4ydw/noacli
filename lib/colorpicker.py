
__license__   = 'GPL v3'
__copyright__ = '2023, Steven Dick <kg4ydw@gmail.com>'


import functools
from functools import partial

from PyQt5.Qt import Qt
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QDockWidget, QTextEdit, QMenu, QListWidgetItem, QDialog
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtCore import QSettings

#from lib.colorlisteditor_ui import Ui_colorListEditor

class ColorPicker():
    lastcolor = 0
    # XXX these are light colors, this should detect dark mode or something
    defcolorlist = [
        # start with standard colors in a rearranged order
        'yellow', 'cyan', 'red', 'magenta', 'gray', 'green', 'blue',
        # extras we like
        'pink', 'lime', 'cornflowerblue', 'tan', 'coral', 'limegreen',
        'orange', 'salmon', 'skyblue'
        ]
    colorlist = []

    # init can't be called before QCoreApplication.setApplicationName
    # so call it only when first needed
    def initColors(self):
        if self.colorlist: return
        c = QSettings().value('colorlist',None)
        if c=='None': c=None
        if c:
           self.colorlist = c.split()
        if not self.colorlist:
            self.colorlist.extend(self.defcolorlist)
        
    def nextColor(self):
        self.initColors()
        if not self.colorlist: return None
        self.lastcolor = (self.lastcolor+1)%len(self.colorlist)
        #print(self.lastcolor, self.colorlist[self.lastcolor]) # DEBUG
        return self.colorlist[self.lastcolor]
    
    def colorMenu(self, m=None):
        if not m:
            m = QMenu()
        self.initColors()
        for c in self.colorlist:
            a = m.addAction(c)
            a.setData(c)
        cm = m.addMenu("more...")
        self.allColorMenu(cm)
        #m.addAction("Edit colors",self.editColors)
        return m

    #def editColors(self):
    #    self.ecDialog = colorListEditor(self)
    #    # XXX connect and destroy when done
    #    self.ecDialog.exec() # XXX 

    def allColorMenu(self, m):
        # delete colors already used?
        used = set(self.colorlist)
        if not m:
            m = QMenu("more...")
        for c in QtGui.QColor.colorNames():
            if c not in used:
                a = m.addAction(c)
                a.setData(c)
        return m

    def execColorMenu(self, event):
        m = self.colorMenu()
        act = m.exec(event.globalPos())
        color = None
        if act:
            color = act.data()
            if not color: return None
            try:
                colornum = self.colorlist.index(color)
                self.lastcolor = colornum % len(self.colorlist)
            except ValueError:
                self.colorlist.append(color)
                # XX save index in lastcolor too?
                self.saveColors()
        return color

    def execAllColorMenu(self, event):
        m = self.allColorMenu()
        act = m.exec(event.globalPos())
        return act.data()
 
    def saveColors(self):
        QSettings().setValue('colorlist', ' '.join(self.colorlist))
