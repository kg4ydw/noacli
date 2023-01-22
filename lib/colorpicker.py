
__license__   = 'GPL v3'
__copyright__ = '2023, Steven Dick <kg4ydw@gmail.com>'


import functools
from functools import partial

from PyQt5.Qt import Qt
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QDockWidget, QTextEdit, QMenu, QListWidgetItem, QDialog, QLabel
from PyQt5.QtGui import QPixmap, QIcon, QPalette
from PyQt5.QtCore import QSettings, QItemSelectionModel

from lib.colorlisteditor_ui import Ui_colorListEditor

class ColorPicker():
    lastcolor = 0
    # XXX these are light colors, this should detect dark mode or something
    defcolorlist = [
        # start with standard colors in a rearranged order
        'yellow', 'cyan', 'red', 'magenta', 'gray', 'green', 'blue',
        # extras we like
        'pink', 'lime', 'cornflowerblue', 'tan', 'coral', 'limegreen',
        'orange', 'salmon', 'skyblue', 'violet'
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
            a = m.addAction(self.colorIcon(c), c)
            a.setData(c)
        cm = m.addMenu("more...")
        self.allColorMenu(cm)
        m.addAction("Edit colors",self.editColors)
        return m

    def editColors(self):
        self.ecDialog = colorListEditor(self)
        # connect and destroy when done
        self.ecDialog.finished.connect(self.doneEditColors)
        self.ecDialog.show()

    def doneEditColors(self):
        self.ecDialog = None
        
    def allColorMenu(self, m):
        # delete colors already used?
        used = set(self.colorlist)
        if not m:
            m = QMenu("more...")
        for c in QtGui.QColor.colorNames():
            if c not in used:
                # this didn't work and also had bad spacing
                #x# l = QLabel(c, m)
                #x# p = l.palette()
                #x# p.setColor(l.backgroundRole(), QColor(c))
                #x# l.setPalette(p)
                #x# a = QtWidgets.QWidgetAction(m)
                #x# a.setDefaultWidget(l)
                #x# m.addAction(a)
                a = m.addAction(self.colorIcon(c), c)
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

    @staticmethod
    def colorIcon(color):
        #pixmap = QPixmap()
        #mask = pixmap.createMaskFromColor(QColor('black'), Qt.MaskOutColor)
        #pixmap.fill((QColor(color)))
        #pixmap.setMask(mask)
        #return QIcon(pixmap)
        pixmap = QPixmap(50,50) # XXX hardcoded size, does it matter?
        pixmap.fill(QColor(color))
        return QIcon(pixmap)

class colorListEditor(QDialog):
    def __init__(self, colorpicker):
        super().__init__()
        self.colorpicker = colorpicker
        self.ui = Ui_colorListEditor()
        self.ui.setupUi(self)
        buttonbox = self.ui.buttonBox
        buttonDefault = buttonbox.addButton("Reset Defaults",QtWidgets.QDialogButtonBox.ActionRole)
        buttonDefault.clicked.connect(partial(self.selectColorSet,self.colorpicker.defcolorlist))
        self.accepted.connect(self.saveColors)
        self.finished.connect(self.done)
        self.buildlist()

    def saveColors(self):
        newlist = []
        indexes = self.ui.listWidget.selectionModel().selectedIndexes()
        for i in indexes:
            newlist.append(i.data())
        #print(newlist) # DEBUG
        self.colorpicker.colorlist = newlist
        self.colorpicker.saveColors()

    def done(self, result):
        if result: self.saveColors()
        self.deleteLater()
        
    def buildlist(self):
        self.colorpicker.initColors() # XX or pull from QSettings unconditionally?
        wl = self.ui.listWidget
        wl.clear()
        for color in QtGui.QColor.colorNames():
            i = QListWidgetItem(ColorPicker.colorIcon(color), color)
            wl.addItem(i)
        self.selectColorSet(self.colorpicker.colorlist)

    def selectColorSet(self, colors):
        colorset = set(colors)
        wl = self.ui.listWidget
        m = wl.model()
        sm = QItemSelectionModel(m)
        for row in range(m.rowCount()):
            i = m.index(row,0)
            if i.data() in colorset:
                sm.select(i, QItemSelectionModel.Select)
        wl.setSelectionModel(sm)

