# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'lib/noacli_ui.ui'
#
# Created by: PyQt5 UI code generator 5.15.6
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_noacli(object):
    def setupUi(self, noacli):
        noacli.setObjectName("noacli")
        noacli.resize(612, 297)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(noacli.sizePolicy().hasHeightForWidth())
        noacli.setSizePolicy(sizePolicy)
        noacli.setDockNestingEnabled(True)
        noacli.setDockOptions(QtWidgets.QMainWindow.AllowNestedDocks|QtWidgets.QMainWindow.AllowTabbedDocks|QtWidgets.QMainWindow.AnimatedDocks|QtWidgets.QMainWindow.GroupedDragging)
        noacli.setUnifiedTitleAndToolBarOnMac(True)
        self.centralwidget = QtWidgets.QWidget(noacli)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.centralwidget.sizePolicy().hasHeightForWidth())
        self.centralwidget.setSizePolicy(sizePolicy)
        self.centralwidget.setObjectName("centralwidget")
        self.verticalLayout_3 = QtWidgets.QVBoxLayout(self.centralwidget)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.commandEdit = commandEditor(self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.commandEdit.sizePolicy().hasHeightForWidth())
        self.commandEdit.setSizePolicy(sizePolicy)
        self.commandEdit.setObjectName("commandEdit")
        self.verticalLayout_3.addWidget(self.commandEdit)
        noacli.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(noacli)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 612, 16))
        self.menubar.setObjectName("menubar")
        self.historyMenu = QtWidgets.QMenu(self.menubar)
        self.historyMenu.setObjectName("historyMenu")
        self.menuViews = QtWidgets.QMenu(self.menubar)
        self.menuViews.setObjectName("menuViews")
        self.menuJobs = QtWidgets.QMenu(self.menubar)
        self.menuJobs.setObjectName("menuJobs")
        self.menuSettings = QtWidgets.QMenu(self.menubar)
        self.menuSettings.setObjectName("menuSettings")
        noacli.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(noacli)
        self.statusbar.setObjectName("statusbar")
        noacli.setStatusBar(self.statusbar)
        self.history = myDock(noacli)
        self.history.setEnabled(True)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(2)
        sizePolicy.setHeightForWidth(self.history.sizePolicy().hasHeightForWidth())
        self.history.setSizePolicy(sizePolicy)
        self.history.setMaximumSize(QtCore.QSize(524287, 524287))
        self.history.setFloating(False)
        self.history.setObjectName("history")
        self.dockWidgetContents = QtWidgets.QWidget()
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.dockWidgetContents.sizePolicy().hasHeightForWidth())
        self.dockWidgetContents.setSizePolicy(sizePolicy)
        self.dockWidgetContents.setObjectName("dockWidgetContents")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.dockWidgetContents)
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.historySearch = QtWidgets.QLineEdit(self.dockWidgetContents)
        self.historySearch.setFrame(True)
        self.historySearch.setClearButtonEnabled(True)
        self.historySearch.setObjectName("historySearch")
        self.verticalLayout_2.addWidget(self.historySearch)
        self.historyView = historyView(self.dockWidgetContents)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(2)
        sizePolicy.setHeightForWidth(self.historyView.sizePolicy().hasHeightForWidth())
        self.historyView.setSizePolicy(sizePolicy)
        self.historyView.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.historyView.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.historyView.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.historyView.setTextElideMode(QtCore.Qt.ElideMiddle)
        self.historyView.setHorizontalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        self.historyView.setSortingEnabled(True)
        self.historyView.setCornerButtonEnabled(True)
        self.historyView.setObjectName("historyView")
        self.historyView.horizontalHeader().setStretchLastSection(True)
        self.verticalLayout_2.addWidget(self.historyView)
        self.history.setWidget(self.dockWidgetContents)
        noacli.addDockWidget(QtCore.Qt.DockWidgetArea(4), self.history)
        self.jobManager = myDock(noacli)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(2)
        sizePolicy.setHeightForWidth(self.jobManager.sizePolicy().hasHeightForWidth())
        self.jobManager.setSizePolicy(sizePolicy)
        self.jobManager.setMinimumSize(QtCore.QSize(88, 107))
        self.jobManager.setObjectName("jobManager")
        self.dockWidgetContents_5 = QtWidgets.QWidget()
        self.dockWidgetContents_5.setObjectName("dockWidgetContents_5")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.dockWidgetContents_5)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.jobTableView = QtWidgets.QTableView(self.dockWidgetContents_5)
        self.jobTableView.setEnabled(True)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(2)
        sizePolicy.setVerticalStretch(2)
        sizePolicy.setHeightForWidth(self.jobTableView.sizePolicy().hasHeightForWidth())
        self.jobTableView.setSizePolicy(sizePolicy)
        self.jobTableView.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.jobTableView.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.jobTableView.setEditTriggers(QtWidgets.QAbstractItemView.AnyKeyPressed|QtWidgets.QAbstractItemView.DoubleClicked|QtWidgets.QAbstractItemView.EditKeyPressed|QtWidgets.QAbstractItemView.SelectedClicked)
        self.jobTableView.setTextElideMode(QtCore.Qt.ElideMiddle)
        self.jobTableView.setSortingEnabled(False)
        self.jobTableView.setObjectName("jobTableView")
        self.jobTableView.horizontalHeader().setSortIndicatorShown(False)
        self.jobTableView.horizontalHeader().setStretchLastSection(True)
        self.verticalLayout.addWidget(self.jobTableView)
        self.jobManager.setWidget(self.dockWidgetContents_5)
        noacli.addDockWidget(QtCore.Qt.DockWidgetArea(4), self.jobManager)
        self.smallOutputDock = myDock(noacli)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(self.smallOutputDock.sizePolicy().hasHeightForWidth())
        self.smallOutputDock.setSizePolicy(sizePolicy)
        self.smallOutputDock.setObjectName("smallOutputDock")
        self.dockWidgetContents_3 = QtWidgets.QWidget()
        self.dockWidgetContents_3.setObjectName("dockWidgetContents_3")
        self.verticalLayout_4 = QtWidgets.QVBoxLayout(self.dockWidgetContents_3)
        self.verticalLayout_4.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_4.setObjectName("verticalLayout_4")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.dupOutput = QtWidgets.QToolButton(self.dockWidgetContents_3)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.dupOutput.sizePolicy().hasHeightForWidth())
        self.dupOutput.setSizePolicy(sizePolicy)
        self.dupOutput.setObjectName("dupOutput")
        self.horizontalLayout_2.addWidget(self.dupOutput)
        self.logOutputButton = QtWidgets.QToolButton(self.dockWidgetContents_3)
        self.logOutputButton.setEnabled(False)
        self.logOutputButton.setObjectName("logOutputButton")
        self.horizontalLayout_2.addWidget(self.logOutputButton)
        self.killButton = QtWidgets.QToolButton(self.dockWidgetContents_3)
        self.killButton.setEnabled(False)
        self.killButton.setObjectName("killButton")
        self.horizontalLayout_2.addWidget(self.killButton)
        self.keepOutput = QtWidgets.QCheckBox(self.dockWidgetContents_3)
        self.keepOutput.setObjectName("keepOutput")
        self.horizontalLayout_2.addWidget(self.keepOutput)
        self.verticalLayout_4.addLayout(self.horizontalLayout_2)
        self.smallOutputView = smallOutput(self.dockWidgetContents_3)
        self.smallOutputView.setEnabled(True)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(self.smallOutputView.sizePolicy().hasHeightForWidth())
        self.smallOutputView.setSizePolicy(sizePolicy)
        self.smallOutputView.setObjectName("smallOutputView")
        self.verticalLayout_4.addWidget(self.smallOutputView)
        self.smallOutputDock.setWidget(self.dockWidgetContents_3)
        noacli.addDockWidget(QtCore.Qt.DockWidgetArea(4), self.smallOutputDock)
        self.logDock = myDock(noacli)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(2)
        sizePolicy.setHeightForWidth(self.logDock.sizePolicy().hasHeightForWidth())
        self.logDock.setSizePolicy(sizePolicy)
        self.logDock.setObjectName("logDock")
        self.dockWidgetContents_2 = QtWidgets.QWidget()
        self.dockWidgetContents_2.setObjectName("dockWidgetContents_2")
        self.verticalLayout_6 = QtWidgets.QVBoxLayout(self.dockWidgetContents_2)
        self.verticalLayout_6.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_6.setObjectName("verticalLayout_6")
        self.dockTools = QtWidgets.QHBoxLayout()
        self.dockTools.setObjectName("dockTools")
        self.checkBox = QtWidgets.QCheckBox(self.dockWidgetContents_2)
        self.checkBox.setChecked(True)
        self.checkBox.setObjectName("checkBox")
        self.dockTools.addWidget(self.checkBox)
        self.logSearch = QtWidgets.QLineEdit(self.dockWidgetContents_2)
        self.logSearch.setClearButtonEnabled(True)
        self.logSearch.setObjectName("logSearch")
        self.dockTools.addWidget(self.logSearch)
        self.verticalLayout_6.addLayout(self.dockTools)
        self.logBrowser = logOutput(self.dockWidgetContents_2)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(self.logBrowser.sizePolicy().hasHeightForWidth())
        self.logBrowser.setSizePolicy(sizePolicy)
        self.logBrowser.setObjectName("logBrowser")
        self.verticalLayout_6.addWidget(self.logBrowser)
        self.logDock.setWidget(self.dockWidgetContents_2)
        noacli.addDockWidget(QtCore.Qt.DockWidgetArea(4), self.logDock)
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
        self.actionlastCommand = QtWidgets.QAction(noacli)
        self.actionlastCommand.setObjectName("actionlastCommand")
        self.actionShowDocks = QtWidgets.QAction(noacli)
        self.actionShowDocks.setObjectName("actionShowDocks")
        self.actionHideDocks = QtWidgets.QAction(noacli)
        self.actionHideDocks.setObjectName("actionHideDocks")
        self.actionsave_history = QtWidgets.QAction(noacli)
        self.actionsave_history.setObjectName("actionsave_history")
        self.actionGsettings = QtWidgets.QAction(noacli)
        self.actionGsettings.setObjectName("actionGsettings")
        self.actionFavorites_editor = QtWidgets.QAction(noacli)
        self.actionFavorites_editor.setObjectName("actionFavorites_editor")
        self.actionGeoSave = QtWidgets.QAction(noacli)
        self.actionGeoSave.setObjectName("actionGeoSave")
        self.actionGeoRestore = QtWidgets.QAction(noacli)
        self.actionGeoRestore.setObjectName("actionGeoRestore")
        self.actionDeleteProfile = QtWidgets.QAction(noacli)
        self.actionDeleteProfile.setObjectName("actionDeleteProfile")
        self.actionSync_settings = QtWidgets.QAction(noacli)
        self.actionSync_settings.setObjectName("actionSync_settings")
        self.actionTabifyDocks = QtWidgets.QAction(noacli)
        self.actionTabifyDocks.setObjectName("actionTabifyDocks")
        self.actionEnvironment_Variables = QtWidgets.QAction(noacli)
        self.actionEnvironment_Variables.setObjectName("actionEnvironment_Variables")
        self.actionEditor_font = QtWidgets.QAction(noacli)
        self.actionEditor_font.setObjectName("actionEditor_font")
        self.actionHelp = QtWidgets.QAction(noacli)
        self.actionHelp.setObjectName("actionHelp")
        self.actionButtonDockEditor = QtWidgets.QAction(noacli)
        self.actionButtonDockEditor.setObjectName("actionButtonDockEditor")
        self.historyMenu.addAction(self.actionlastCommand)
        self.historyMenu.addAction(self.actionsave_history)
        self.historyMenu.addSeparator()
        self.menuViews.addAction(self.actionShowDocks)
        self.menuViews.addAction(self.actionHideDocks)
        self.menuViews.addAction(self.actionTabifyDocks)
        self.menuViews.addSeparator()
        self.menuSettings.addAction(self.actionFavorites_editor)
        self.menuSettings.addAction(self.actionGsettings)
        self.menuSettings.addAction(self.actionEnvironment_Variables)
        self.menuSettings.addAction(self.actionButtonDockEditor)
        self.menuSettings.addAction(self.actionHelp)
        self.menuSettings.addSeparator()
        self.menuSettings.addAction(self.actionEditor_font)
        self.menuSettings.addAction(self.actionSync_settings)
        self.menuSettings.addSeparator()
        self.menuSettings.addAction(self.actionGeoSave)
        self.menuSettings.addAction(self.actionGeoRestore)
        self.menuSettings.addAction(self.actionDeleteProfile)
        self.menubar.addAction(self.historyMenu.menuAction())
        self.menubar.addAction(self.menuJobs.menuAction())
        self.menubar.addAction(self.menuViews.menuAction())
        self.menubar.addAction(self.menuSettings.menuAction())

        self.retranslateUi(noacli)
        self.actionHideDocks.triggered.connect(noacli.hideAllDocks) # type: ignore
        self.actionShowDocks.triggered.connect(noacli.showAllDocks) # type: ignore
        self.historyView.doubleClicked['QModelIndex'].connect(self.commandEdit.acceptHistory) # type: ignore
        self.commandEdit.command_to_run['QString','QPersistentModelIndex'].connect(noacli.runCommand) # type: ignore
        self.jobTableView.doubleClicked['QModelIndex'].connect(noacli.jobDoubleClicked) # type: ignore
        self.actionsave_history.triggered.connect(noacli.actionSaveHistory) # type: ignore
        self.actionlastCommand.triggered.connect(noacli.runLastCommand) # type: ignore
        self.actionGsettings.triggered.connect(noacli.actionGsettings) # type: ignore
        self.historyView.newFavorite['QString'].connect(noacli.addFavorite) # type: ignore
        self.actionGeoSave.triggered.connect(noacli.actionSaveGeometry) # type: ignore
        self.actionGeoRestore.triggered.connect(noacli.actionRestoreGeometry) # type: ignore
        self.dupOutput.clicked.connect(self.smallOutputView.smallDup) # type: ignore
        self.keepOutput.toggled['bool'].connect(self.smallOutputView.smallKeepToggle) # type: ignore
        self.actionSync_settings.triggered.connect(noacli.syncSettings) # type: ignore
        self.commandEdit.newFavorite['QString'].connect(noacli.addFavorite) # type: ignore
        self.actionEnvironment_Variables.triggered.connect(noacli.actionEsettings) # type: ignore
        self.checkBox.stateChanged['int'].connect(self.logBrowser.setFollowCheck) # type: ignore
        self.logSearch.textChanged['QString'].connect(self.logBrowser.simpleFindNew) # type: ignore
        self.logSearch.returnPressed.connect(self.logBrowser.simpleFind2) # type: ignore
        self.logOutputButton.clicked['bool'].connect(self.smallOutputView.smallLog) # type: ignore
        self.smallOutputView.sendToLog['PyQt_PyObject'].connect(self.logBrowser.receiveJob) # type: ignore
        self.logBrowser.gotNewLines['int'].connect(self.logDock.newLines) # type: ignore
        self.smallOutputView.gotNewLines['int'].connect(self.smallOutputDock.newLines) # type: ignore
        self.actionEditor_font.triggered.connect(noacli.pickDefaultFont) # type: ignore
        self.actionHelp.triggered.connect(noacli.showReadme) # type: ignore
        self.actionDeleteProfile.triggered.connect(noacli.myDeleteProfile) # type: ignore
        self.actionButtonDockEditor.triggered.connect(noacli.editButtonDocks) # type: ignore
        QtCore.QMetaObject.connectSlotsByName(noacli)

    def retranslateUi(self, noacli):
        _translate = QtCore.QCoreApplication.translate
        noacli.setWindowTitle(_translate("noacli", "noacli"))
        self.historyMenu.setTitle(_translate("noacli", "History"))
        self.menuViews.setTitle(_translate("noacli", "Views"))
        self.menuJobs.setTitle(_translate("noacli", "Jobs"))
        self.menuSettings.setTitle(_translate("noacli", "Settings"))
        self.history.setWindowTitle(_translate("noacli", "History"))
        self.historySearch.setToolTip(_translate("noacli", "Filter history"))
        self.historySearch.setPlaceholderText(_translate("noacli", "search history"))
        self.jobManager.setWindowTitle(_translate("noacli", "Job manager"))
        self.smallOutputDock.setWindowTitle(_translate("noacli", "Small output"))
        self.dupOutput.setToolTip(_translate("noacli", "Copy output to a new window"))
        self.dupOutput.setText(_translate("noacli", "dup"))
        self.logOutputButton.setText(_translate("noacli", "log"))
        self.killButton.setText(_translate("noacli", "kill"))
        self.keepOutput.setToolTip(_translate("noacli", "Keep or (or clear) output between commands"))
        self.keepOutput.setText(_translate("noacli", "keep"))
        self.logDock.setWindowTitle(_translate("noacli", "Log viewer"))
        self.checkBox.setText(_translate("noacli", "follow"))
        self.logSearch.setPlaceholderText(_translate("noacli", "Search log"))
        self.actionHistory.setText(_translate("noacli", "History"))
        self.actionButton_box.setText(_translate("noacli", "Button box"))
        self.actionButton_editor.setText(_translate("noacli", "Button editor"))
        self.actionJob_manager.setText(_translate("noacli", "Job manager"))
        self.actionlastCommand.setText(_translate("noacli", "last command"))
        self.actionShowDocks.setText(_translate("noacli", "Show all"))
        self.actionHideDocks.setText(_translate("noacli", "Hide all"))
        self.actionsave_history.setText(_translate("noacli", "Save history"))
        self.actionGsettings.setText(_translate("noacli", "General settings"))
        self.actionFavorites_editor.setText(_translate("noacli", "Favorites editor"))
        self.actionGeoSave.setText(_translate("noacli", "Save window Geometry"))
        self.actionGeoRestore.setText(_translate("noacli", "Restore window geometry"))
        self.actionDeleteProfile.setText(_translate("noacli", "Delete profile"))
        self.actionSync_settings.setText(_translate("noacli", "Sync settings"))
        self.actionTabifyDocks.setText(_translate("noacli", "Tabify all"))
        self.actionEnvironment_Variables.setText(_translate("noacli", "Environment Variables"))
        self.actionEditor_font.setText(_translate("noacli", "Editor font"))
        self.actionHelp.setText(_translate("noacli", "Help"))
        self.actionButtonDockEditor.setText(_translate("noacli", "Button dock editor"))
from lib.logoutput import logOutput
from lib.mydock import myDock
from lib.smalloutput import smallOutput
from noacli import commandEditor, historyView
