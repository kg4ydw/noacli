# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'noacli_ui.ui'
#
# Created by: PyQt5 UI code generator 5.15.6
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_noacli(object):
    def setupUi(self, noacli):
        noacli.setObjectName("noacli")
        noacli.resize(430, 239)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap("noacli.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        noacli.setWindowIcon(icon)
        self.centralwidget = QtWidgets.QWidget(noacli)
        self.centralwidget.setObjectName("centralwidget")
        self.verticalLayout_3 = QtWidgets.QVBoxLayout(self.centralwidget)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.plainTextEdit = QtWidgets.QPlainTextEdit(self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.plainTextEdit.sizePolicy().hasHeightForWidth())
        self.plainTextEdit.setSizePolicy(sizePolicy)
        self.plainTextEdit.setObjectName("plainTextEdit")
        self.verticalLayout_3.addWidget(self.plainTextEdit)
        noacli.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(noacli)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 430, 16))
        self.menubar.setObjectName("menubar")
        self.historyMenu = QtWidgets.QMenu(self.menubar)
        self.historyMenu.setObjectName("historyMenu")
        self.menuViews = QtWidgets.QMenu(self.menubar)
        self.menuViews.setObjectName("menuViews")
        noacli.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(noacli)
        self.statusbar.setObjectName("statusbar")
        noacli.setStatusBar(self.statusbar)
        self.history = QtWidgets.QDockWidget(noacli)
        self.history.setEnabled(True)
        self.history.setMaximumSize(QtCore.QSize(524287, 524287))
        self.history.setFloating(False)
        self.history.setObjectName("history")
        self.dockWidgetContents = QtWidgets.QWidget()
        self.dockWidgetContents.setObjectName("dockWidgetContents")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.dockWidgetContents)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.historySearch = QtWidgets.QLineEdit(self.dockWidgetContents)
        self.historySearch.setFrame(True)
        self.historySearch.setObjectName("historySearch")
        self.verticalLayout_2.addWidget(self.historySearch)
        self.historyView = QtWidgets.QTableView(self.dockWidgetContents)
        self.historyView.setObjectName("historyView")
        self.verticalLayout_2.addWidget(self.historyView)
        self.history.setWidget(self.dockWidgetContents)
        noacli.addDockWidget(QtCore.Qt.DockWidgetArea(4), self.history)
        self.buttons = QtWidgets.QDockWidget(noacli)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.buttons.sizePolicy().hasHeightForWidth())
        self.buttons.setSizePolicy(sizePolicy)
        self.buttons.setMinimumSize(QtCore.QSize(184, 56))
        self.buttons.setFloating(False)
        self.buttons.setFeatures(QtWidgets.QDockWidget.AllDockWidgetFeatures)
        self.buttons.setObjectName("buttons")
        self.buttonBox = QtWidgets.QWidget()
        self.buttonBox.setObjectName("buttonBox")
        self.gridLayout = QtWidgets.QGridLayout(self.buttonBox)
        self.gridLayout.setObjectName("gridLayout")
        self.rerunLast = QtWidgets.QPushButton(self.buttonBox)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.rerunLast.sizePolicy().hasHeightForWidth())
        self.rerunLast.setSizePolicy(sizePolicy)
        self.rerunLast.setObjectName("rerunLast")
        self.gridLayout.addWidget(self.rerunLast, 0, 1, 1, 1)
        self.runCurrent = QtWidgets.QPushButton(self.buttonBox)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.runCurrent.sizePolicy().hasHeightForWidth())
        self.runCurrent.setSizePolicy(sizePolicy)
        self.runCurrent.setObjectName("runCurrent")
        self.gridLayout.addWidget(self.runCurrent, 0, 0, 1, 1)
        self.buttons.setWidget(self.buttonBox)
        noacli.addDockWidget(QtCore.Qt.DockWidgetArea(4), self.buttons)
        self.jobManager = QtWidgets.QDockWidget(noacli)
        self.jobManager.setMinimumSize(QtCore.QSize(88, 107))
        self.jobManager.setObjectName("jobManager")
        self.dockWidgetContents_5 = QtWidgets.QWidget()
        self.dockWidgetContents_5.setObjectName("dockWidgetContents_5")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.dockWidgetContents_5)
        self.verticalLayout.setObjectName("verticalLayout")
        self.jobTableView = QtWidgets.QTableView(self.dockWidgetContents_5)
        self.jobTableView.setEnabled(False)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.jobTableView.sizePolicy().hasHeightForWidth())
        self.jobTableView.setSizePolicy(sizePolicy)
        self.jobTableView.setObjectName("jobTableView")
        self.verticalLayout.addWidget(self.jobTableView)
        self.jobManager.setWidget(self.dockWidgetContents_5)
        noacli.addDockWidget(QtCore.Qt.DockWidgetArea(4), self.jobManager)
        self.actionHistory = QtWidgets.QAction(noacli)
        self.actionHistory.setCheckable(True)
        self.actionHistory.setObjectName("actionHistory")
        self.actionButton_box = QtWidgets.QAction(noacli)
        self.actionButton_box.setCheckable(True)
        self.actionButton_box.setObjectName("actionButton_box")
        self.actionButton_editor = QtWidgets.QAction(noacli)
        self.actionButton_editor.setCheckable(True)
        self.actionButton_editor.setObjectName("actionButton_editor")
        self.actionJob_manager = QtWidgets.QAction(noacli)
        self.actionJob_manager.setCheckable(True)
        self.actionJob_manager.setObjectName("actionJob_manager")
        self.actionlast = QtWidgets.QAction(noacli)
        self.actionlast.setObjectName("actionlast")
        self.actionShowDocs = QtWidgets.QAction(noacli)
        self.actionShowDocs.setObjectName("actionShowDocs")
        self.actionHideDocs = QtWidgets.QAction(noacli)
        self.actionHideDocs.setObjectName("actionHideDocs")
        self.historyMenu.addAction(self.actionlast)
        self.menuViews.addAction(self.actionShowDocs)
        self.menuViews.addAction(self.actionHideDocs)
        self.menuViews.addSeparator()
        self.menubar.addAction(self.historyMenu.menuAction())
        self.menubar.addAction(self.menuViews.menuAction())

        self.retranslateUi(noacli)
        self.actionHideDocs.triggered.connect(noacli.hideAllDocs) # type: ignore
        self.actionShowDocs.triggered.connect(noacli.showAllDocs) # type: ignore
        QtCore.QMetaObject.connectSlotsByName(noacli)

    def retranslateUi(self, noacli):
        _translate = QtCore.QCoreApplication.translate
        noacli.setWindowTitle(_translate("noacli", "noacli"))
        self.historyMenu.setTitle(_translate("noacli", "History"))
        self.menuViews.setTitle(_translate("noacli", "Views"))
        self.history.setWindowTitle(_translate("noacli", "History"))
        self.historySearch.setPlaceholderText(_translate("noacli", "search history"))
        self.buttons.setWindowTitle(_translate("noacli", "buttons"))
        self.rerunLast.setText(_translate("noacli", "Rerun last"))
        self.runCurrent.setText(_translate("noacli", "Run"))
        self.jobManager.setWindowTitle(_translate("noacli", "Job manager"))
        self.actionHistory.setText(_translate("noacli", "History"))
        self.actionButton_box.setText(_translate("noacli", "Button box"))
        self.actionButton_editor.setText(_translate("noacli", "Button editor"))
        self.actionJob_manager.setText(_translate("noacli", "Job manager"))
        self.actionlast.setText(_translate("noacli", "last command"))
        self.actionShowDocs.setText(_translate("noacli", "Show all"))
        self.actionHideDocs.setText(_translate("noacli", "Hide all"))
