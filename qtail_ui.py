# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'qtail_ui.ui'
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
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setSizeConstraint(QtWidgets.QLayout.SetDefaultConstraint)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.followCheck = QtWidgets.QCheckBox(self.centralwidget)
        self.followCheck.setObjectName("followCheck")
        self.horizontalLayout.addWidget(self.followCheck)
        self.wrapCheck = QtWidgets.QCheckBox(self.centralwidget)
        self.wrapCheck.setChecked(True)
        self.wrapCheck.setObjectName("wrapCheck")
        self.horizontalLayout.addWidget(self.wrapCheck)
        self.reloadButton = QtWidgets.QPushButton(self.centralwidget)
        self.reloadButton.setObjectName("reloadButton")
        self.horizontalLayout.addWidget(self.reloadButton)
        self.label = QtWidgets.QLabel(self.centralwidget)
        self.label.setObjectName("label")
        self.horizontalLayout.addWidget(self.label)
        self.searchTerm = QtWidgets.QLineEdit(self.centralwidget)
        self.searchTerm.setClearButtonEnabled(True)
        self.searchTerm.setObjectName("searchTerm")
        self.horizontalLayout.addWidget(self.searchTerm)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.textBrowser = myBrowser(self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(self.textBrowser.sizePolicy().hasHeightForWidth())
        self.textBrowser.setSizePolicy(sizePolicy)
        self.textBrowser.setMinimumSize(QtCore.QSize(100, 100))
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
        QtTail.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(QtTail)
        self.statusbar.setObjectName("statusbar")
        QtTail.setStatusBar(self.statusbar)
        self.actionAdjust = QtWidgets.QAction(QtTail)
        self.actionAdjust.setObjectName("actionAdjust")
        self.menuView.addAction(self.actionAdjust)
        self.menubar.addAction(self.menuView.menuAction())
        self.label.setBuddy(self.searchTerm)

        self.retranslateUi(QtTail)
        self.searchTerm.textChanged['QString'].connect(QtTail.simpleFindNew) # type: ignore
        self.reloadButton.clicked.connect(QtTail.reload) # type: ignore
        self.wrapCheck.stateChanged['int'].connect(QtTail.wrapChanged) # type: ignore
        self.searchTerm.returnPressed.connect(QtTail.simpleFind2) # type: ignore
        self.actionAdjust.triggered.connect(QtTail.actionAdjust) # type: ignore
        QtCore.QMetaObject.connectSlotsByName(QtTail)

    def retranslateUi(self, QtTail):
        _translate = QtCore.QCoreApplication.translate
        QtTail.setWindowTitle(_translate("QtTail", "qtail"))
        self.followCheck.setText(_translate("QtTail", "Follow"))
        self.wrapCheck.setText(_translate("QtTail", "Wrap"))
        self.reloadButton.setText(_translate("QtTail", "Reload"))
        self.label.setText(_translate("QtTail", "Search:"))
        self.menuView.setTitle(_translate("QtTail", "View"))
        self.actionAdjust.setText(_translate("QtTail", "Adjust"))
        self.actionAdjust.setToolTip(_translate("QtTail", "Adjust size"))
from qtailbrowser import myBrowser
