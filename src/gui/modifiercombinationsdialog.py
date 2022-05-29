# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'src\gui\modifiercombinationsdialog.ui'
#
# Created by: PyQt5 UI code generator 5.9.2
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_CombinationsDialog(object):
    def setupUi(self, CombinationsDialog):
        CombinationsDialog.setObjectName("CombinationsDialog")
        CombinationsDialog.setWindowModality(QtCore.Qt.WindowModal)
        CombinationsDialog.resize(492, 253)
        self.verticalLayout = QtWidgets.QVBoxLayout(CombinationsDialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.tvCombinations = QtWidgets.QTreeView(CombinationsDialog)
        self.tvCombinations.setObjectName("tvCombinations")
        self.verticalLayout.addWidget(self.tvCombinations)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.btnAdd = QtWidgets.QPushButton(CombinationsDialog)
        self.btnAdd.setMaximumSize(QtCore.QSize(30, 16777215))
        self.btnAdd.setObjectName("btnAdd")
        self.horizontalLayout.addWidget(self.btnAdd)
        self.btnRemove = QtWidgets.QPushButton(CombinationsDialog)
        self.btnRemove.setEnabled(False)
        self.btnRemove.setMaximumSize(QtCore.QSize(30, 16777215))
        self.btnRemove.setObjectName("btnRemove")
        self.horizontalLayout.addWidget(self.btnRemove)
        self.btnMoveUp = QtWidgets.QPushButton(CombinationsDialog)
        self.btnMoveUp.setEnabled(False)
        self.btnMoveUp.setMaximumSize(QtCore.QSize(30, 16777215))
        self.btnMoveUp.setObjectName("btnMoveUp")
        self.horizontalLayout.addWidget(self.btnMoveUp)
        self.btnMoveDown = QtWidgets.QPushButton(CombinationsDialog)
        self.btnMoveDown.setEnabled(False)
        self.btnMoveDown.setMaximumSize(QtCore.QSize(30, 16777215))
        self.btnMoveDown.setObjectName("btnMoveDown")
        self.horizontalLayout.addWidget(self.btnMoveDown)
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.btnOk = QtWidgets.QPushButton(CombinationsDialog)
        self.btnOk.setObjectName("btnOk")
        self.horizontalLayout.addWidget(self.btnOk)
        self.btnCancel = QtWidgets.QPushButton(CombinationsDialog)
        self.btnCancel.setObjectName("btnCancel")
        self.horizontalLayout.addWidget(self.btnCancel)
        self.verticalLayout.addLayout(self.horizontalLayout)

        self.retranslateUi(CombinationsDialog)
        QtCore.QMetaObject.connectSlotsByName(CombinationsDialog)

    def retranslateUi(self, CombinationsDialog):
        _translate = QtCore.QCoreApplication.translate
        CombinationsDialog.setWindowTitle(_translate("CombinationsDialog", "Customize Modifer Combinations"))
        self.btnAdd.setText(_translate("CombinationsDialog", "+"))
        self.btnRemove.setText(_translate("CombinationsDialog", "-"))
        self.btnMoveUp.setText(_translate("CombinationsDialog", "˄"))
        self.btnMoveDown.setText(_translate("CombinationsDialog", "˅"))
        self.btnOk.setText(_translate("CombinationsDialog", "OK"))
        self.btnCancel.setText(_translate("CombinationsDialog", "Cancel"))

