# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'lib/qtail_ui.ui'
#
# Created by: PyQt5 UI code generator 5.15.6
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_QtTail(object):
    def setupUi(self, QtTail):
        QtTail.setObjectName("QtTail")
        QtTail.resize(719, 507)
        self.centralwidget = QtWidgets.QWidget(QtTail)
        self.centralwidget.setObjectName("centralwidget")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.centralwidget)
        self.verticalLayout.setObjectName("verticalLayout")
        self.toolBar_2 = QtWidgets.QFrame(self.centralwidget)
        self.toolBar_2.setLineWidth(0)
        self.toolBar_2.setObjectName("toolBar_2")
        self.toolBar = QtWidgets.QHBoxLayout(self.toolBar_2)
        self.toolBar.setSizeConstraint(QtWidgets.QLayout.SetDefaultConstraint)
        self.toolBar.setContentsMargins(-1, 0, -1, 0)
        self.toolBar.setObjectName("toolBar")
        self.followCheck = QtWidgets.QCheckBox(self.toolBar_2)
        self.followCheck.setObjectName("followCheck")
        self.toolBar.addWidget(self.followCheck)
        self.reloadButton = QtWidgets.QPushButton(self.toolBar_2)
        self.reloadButton.setObjectName("reloadButton")
        self.toolBar.addWidget(self.reloadButton)
        self.label = QtWidgets.QLabel(self.toolBar_2)
        self.label.setObjectName("label")
        self.toolBar.addWidget(self.label)
        self.searchTerm = QtWidgets.QLineEdit(self.toolBar_2)
        self.searchTerm.setClearButtonEnabled(True)
        self.searchTerm.setObjectName("searchTerm")
        self.toolBar.addWidget(self.searchTerm)
        self.verticalLayout.addWidget(self.toolBar_2)
        self.textBrowser = myBrowser(self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(self.textBrowser.sizePolicy().hasHeightForWidth())
        self.textBrowser.setSizePolicy(sizePolicy)
        self.textBrowser.setMinimumSize(QtCore.QSize(100, 50))
        self.textBrowser.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self.textBrowser.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.textBrowser.setObjectName("textBrowser")
        self.verticalLayout.addWidget(self.textBrowser)
        QtTail.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(QtTail)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 719, 16))
        self.menubar.setObjectName("menubar")
        self.menuView = QtWidgets.QMenu(self.menubar)
        self.menuView.setObjectName("menuView")
        self.menuMode = QtWidgets.QMenu(self.menubar)
        self.menuMode.setObjectName("menuMode")
        self.menuSearch = QtWidgets.QMenu(self.menubar)
        self.menuSearch.setObjectName("menuSearch")
        QtTail.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(QtTail)
        self.statusbar.setObjectName("statusbar")
        QtTail.setStatusBar(self.statusbar)
        self.actionAdjust = QtWidgets.QAction(QtTail)
        self.actionAdjust.setObjectName("actionAdjust")
        self.actionCount_lines = QtWidgets.QAction(QtTail)
        self.actionCount_lines.setObjectName("actionCount_lines")
        self.actionWrap_lines = QtWidgets.QAction(QtTail)
        self.actionWrap_lines.setCheckable(True)
        self.actionWrap_lines.setChecked(True)
        self.actionWrap_lines.setObjectName("actionWrap_lines")
        self.actionFont = QtWidgets.QAction(QtTail)
        self.actionFont.setObjectName("actionFont")
        self.actionWatch = QtWidgets.QAction(QtTail)
        self.actionWatch.setCheckable(True)
        self.actionWatch.setObjectName("actionWatch")
        self.actionAutorefresh = QtWidgets.QAction(QtTail)
        self.actionAutorefresh.setCheckable(True)
        self.actionAutorefresh.setObjectName("actionAutorefresh")
        self.actionFontMono = QtWidgets.QAction(QtTail)
        self.actionFontMono.setObjectName("actionFontMono")
        self.actionFontMono_2 = QtWidgets.QAction(QtTail)
        self.actionFontMono_2.setObjectName("actionFontMono_2")
        self.actionClear_selections = QtWidgets.QAction(QtTail)
        self.actionClear_selections.setObjectName("actionClear_selections")
        self.actionClearFinds = QtWidgets.QAction(QtTail)
        self.actionClearFinds.setObjectName("actionClearFinds")
        self.actionShowToolbar = QtWidgets.QAction(QtTail)
        self.actionShowToolbar.setCheckable(True)
        self.actionShowToolbar.setChecked(True)
        self.actionShowToolbar.setObjectName("actionShowToolbar")
        self.actionReload = QtWidgets.QAction(QtTail)
        self.actionReload.setObjectName("actionReload")
        self.actionUseRegEx = QtWidgets.QAction(QtTail)
        self.actionUseRegEx.setCheckable(True)
        self.actionUseRegEx.setChecked(True)
        self.actionUseRegEx.setObjectName("actionUseRegEx")
        self.actionCaseInsensitive = QtWidgets.QAction(QtTail)
        self.actionCaseInsensitive.setCheckable(True)
        self.actionCaseInsensitive.setChecked(True)
        self.actionCaseInsensitive.setObjectName("actionCaseInsensitive")
        self.actionUnicode = QtWidgets.QAction(QtTail)
        self.actionUnicode.setCheckable(True)
        self.actionUnicode.setObjectName("actionUnicode")
        self.actionWholeWords = QtWidgets.QAction(QtTail)
        self.actionWholeWords.setCheckable(True)
        self.actionWholeWords.setObjectName("actionWholeWords")
        self.actionSaveExtra = QtWidgets.QAction(QtTail)
        self.actionSaveExtra.setObjectName("actionSaveExtra")
        self.actionSetExtra = QtWidgets.QAction(QtTail)
        self.actionSetExtra.setObjectName("actionSetExtra")
        self.actionListHighlights = QtWidgets.QAction(QtTail)
        self.actionListHighlights.setObjectName("actionListHighlights")
        self.actionFind_all = QtWidgets.QAction(QtTail)
        self.actionFind_all.setObjectName("actionFind_all")
        self.menuView.addAction(self.actionShowToolbar)
        self.menuView.addSeparator()
        self.menuView.addAction(self.actionAdjust)
        self.menuView.addAction(self.actionCount_lines)
        self.menuView.addAction(self.actionWrap_lines)
        self.menuView.addSeparator()
        self.menuView.addSeparator()
        self.menuView.addAction(self.actionFont)
        self.menuMode.addAction(self.actionWatch)
        self.menuMode.addAction(self.actionAutorefresh)
        self.menuMode.addAction(self.actionReload)
        self.menuSearch.addAction(self.actionUseRegEx)
        self.menuSearch.addAction(self.actionCaseInsensitive)
        self.menuSearch.addAction(self.actionUnicode)
        self.menuSearch.addAction(self.actionWholeWords)
        self.menuSearch.addAction(self.actionClearFinds)
        self.menuSearch.addAction(self.actionListHighlights)
        self.menuSearch.addAction(self.actionFind_all)
        self.menubar.addAction(self.menuView.menuAction())
        self.menubar.addAction(self.menuMode.menuAction())
        self.menubar.addAction(self.menuSearch.menuAction())

        self.retranslateUi(QtTail)
        self.actionAdjust.triggered.connect(QtTail.actionAdjust) # type: ignore
        self.actionCount_lines.triggered.connect(QtTail.showsize) # type: ignore
        self.actionWrap_lines.triggered['bool'].connect(QtTail.wrapChanged) # type: ignore
        self.actionFont.triggered.connect(self.textBrowser.pickFont) # type: ignore
        self.actionAutorefresh.triggered.connect(QtTail.actionAutoRefresh) # type: ignore
        self.actionWatch.triggered.connect(QtTail.setButtonMode) # type: ignore
        self.actionClearFinds.triggered.connect(QtTail.clearFinds) # type: ignore
        self.actionShowToolbar.triggered['bool'].connect(self.statusbar.setVisible) # type: ignore
        self.searchTerm.textChanged['QString'].connect(QtTail.simpleFindNew) # type: ignore
        self.searchTerm.returnPressed.connect(QtTail.simpleFind2) # type: ignore
        self.followCheck.toggled['bool'].connect(self.textBrowser.jumpToEndMaybe) # type: ignore
        self.actionReload.triggered.connect(QtTail.reloadOrRerun) # type: ignore
        self.actionListHighlights.triggered.connect(QtTail.extraSelectionsToDock) # type: ignore
        self.actionFind_all.triggered.connect(QtTail.findAll) # type: ignore
        self.textBrowser.saveHighlight.connect(QtTail.saveHighlight) # type: ignore
        self.textBrowser.clearHighlights.connect(QtTail.clearFinds) # type: ignore
        QtCore.QMetaObject.connectSlotsByName(QtTail)

    def retranslateUi(self, QtTail):
        _translate = QtCore.QCoreApplication.translate
        QtTail.setWindowTitle(_translate("QtTail", "qtail"))
        self.followCheck.setText(_translate("QtTail", "Follow"))
        self.reloadButton.setText(_translate("QtTail", "Reload"))
        self.label.setText(_translate("QtTail", "Search:"))
        self.menuView.setTitle(_translate("QtTail", "View"))
        self.menuMode.setTitle(_translate("QtTail", "Watch"))
        self.menuSearch.setTitle(_translate("QtTail", "Search"))
        self.actionAdjust.setText(_translate("QtTail", "Adjust size"))
        self.actionAdjust.setToolTip(_translate("QtTail", "Adjust size"))
        self.actionCount_lines.setText(_translate("QtTail", "Count lines"))
        self.actionWrap_lines.setText(_translate("QtTail", "Wrap lines"))
        self.actionFont.setText(_translate("QtTail", "Pick font"))
        self.actionWatch.setText(_translate("QtTail", "Watch"))
        self.actionAutorefresh.setText(_translate("QtTail", "Autorefresh"))
        self.actionFontMono.setText(_translate("QtTail", "Pick monospace font"))
        self.actionFontMono_2.setText(_translate("QtTail", "Pick monospaced font"))
        self.actionClear_selections.setText(_translate("QtTail", "Clear finds"))
        self.actionClearFinds.setText(_translate("QtTail", "Clear highlights"))
        self.actionShowToolbar.setText(_translate("QtTail", "Show toolbar"))
        self.actionReload.setText(_translate("QtTail", "Refresh now"))
        self.actionUseRegEx.setText(_translate("QtTail", "Use RegEx"))
        self.actionCaseInsensitive.setText(_translate("QtTail", "Case insensitive"))
        self.actionUnicode.setText(_translate("QtTail", "Unicode"))
        self.actionWholeWords.setText(_translate("QtTail", "Whole words"))
        self.actionSaveExtra.setText(_translate("QtTail", "SaveExtra"))
        self.actionSetExtra.setText(_translate("QtTail", "List current highlights"))
        self.actionListHighlights.setText(_translate("QtTail", "List current highlights"))
        self.actionFind_all.setText(_translate("QtTail", "Find all"))
from lib.qtailbrowser import myBrowser
