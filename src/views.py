import os
from typing import TYPE_CHECKING, List

from PyQt5.QtWidgets import QWidget, QMessageBox, QLineEdit, QListView, QPushButton, QDialog
from PyQt5.QtCore import pyqtSignal, Qt, QStringListModel, QModelIndex, QItemSelection, QItemSelectionModel
from PyQt5.QtGui import QPixmap, QIcon, QStandardItemModel, QStandardItem, QCloseEvent


from gui import Ui_VariationSettingsWindow, Ui_ModifierSettingsWindow, Ui_CombinationsDialog

import utils
from models import Modifier, ModifierCombination, Variation

if TYPE_CHECKING:
    from app import App
    from PyQt5.QtCore import PYQT_SIGNAL


class ModifierItem(QStandardItem):
    def __init__(self, text: str, modifierId: int):
        super(QStandardItem, self).__init__(text)
        self.modifierId = modifierId


class ModifierCombinationsDialog(QDialog, Ui_CombinationsDialog):
    def __init__(self, parent: QWidget, **kwargs) -> None:
        super(ModifierCombinationsDialog, self).__init__(
            parent, Qt.Dialog | Qt.WindowCloseButtonHint | Qt.WindowTitleHint)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.mainApp: 'App' = kwargs.pop('mApp')
        self.variationToEdit: Variation = kwargs.pop('variationToEdit', None)
        self.modifierCombinations: List[ModifierCombination] = []
        self.setupUi(self)
        self.setupExtraElements()
        self.initCombinationsData()
        self.setupEvents()

    def setupExtraElements(self):
        iconPath = os.path.join(utils.getResourcesPath(), 'icon.ico')
        icon = QIcon()
        icon.addPixmap(QPixmap(iconPath), QIcon.Normal, QIcon.Off)
        self.setWindowIcon(icon)
        self.combinationsModel = QStandardItemModel()
        self.tvCombinations.setModel(self.combinationsModel)

    def setupEvents(self):
        self.btnAdd.clicked.connect(self.onBtnAdd)
        self.btnRemove.clicked.connect(self.onBtnRemove)
        self.btnMoveUp.clicked.connect(self.onBtnMoveUp)
        self.btnMoveDown.clicked.connect(self.onBtnMoveDown)
        self.btnOk.clicked.connect(self.onBtnOk)
        self.btnCancel.clicked.connect(self.onBtnCancel)
        self.tvCombinations.selectionModel().currentRowChanged.connect(lambda _x, _y: self.updateButtonsState())
        
        

    def initCombinationsData(self):
        if self.variationToEdit.combinations is not None:
            # Create a copy of the combination list
            for c in self.variationToEdit.combinations:
                self.modifierCombinations.append(
                    ModifierCombination.from_dict(c.to_dict()))

        mods = self.mainApp.lookupVariationModifiers(self.variationToEdit)
        if len(self.modifierCombinations) == 0 and len(mods) > 0:
            self.modifierCombinations = utils.defaultCombinations(
                self.variationToEdit, mods)

        self.combinationsModel.insertColumns(0, len(mods) + 1)
        # Init the headers
        self.combinationsModel.setHeaderData(0, Qt.Horizontal, 'Combination')
        for i in range(len(mods)):
            self.combinationsModel.setHeaderData(i+1, Qt.Horizontal, mods[i].name)
        self.tvCombinations.header().setSectionsMovable(False)
        # Fill the data
        for c in self.modifierCombinations:
            row = self.combinationsModel.rowCount()
            self.combinationsModel.setItem(row, 0, QStandardItem(c.name))
            for i in range(len(c.bitflags)):
                checkItem = QStandardItem()
                checkItem.setCheckable(True)
                checkItem.setCheckState(Qt.Checked if c.bitflags[i] == '1' else Qt.Unchecked)
                self.combinationsModel.setItem(row, i+1, checkItem)

    def updateButtonsState(self):
        selected = self.tvCombinations.selectionModel().currentIndex()
        isSelected = selected and selected.row() >= 0
        if isSelected:
            print('Current row is: {0}'.format(selected.row()))
            lastRowIndex = self.combinationsModel.index(self.combinationsModel.rowCount() - 1, 0)
            print('Last row index is: {0}'.format(lastRowIndex.row()))
        self.btnRemove.setEnabled(isSelected)
        self.btnMoveUp.setEnabled(isSelected and selected.row() > 0)
        self.btnMoveDown.setEnabled(isSelected and selected.row() < self.combinationsModel.rowCount() - 1)

    def onBtnOk(self):
        combs = []
        for row in range(self.combinationsModel.rowCount()):
            combName = self.combinationsModel.item(row, 0).text()
            bitflags = ''
            for col in range(self.combinationsModel.columnCount()-1):
                item = self.combinationsModel.item(row, col+1)
                bitflags += ('1' if item.checkState() == Qt.Checked else '0')

            combs.append(ModifierCombination.from_dict(
                {'name': combName, 'bitflags': bitflags}))
        self.variationToEdit.combinations = combs
        self.accept()

    def onBtnCancel(self):
        self.reject()
    
    def onBtnAdd(self):
        row = self.combinationsModel.rowCount()
        self.combinationsModel.setItem(row, 0, QStandardItem('New comb'))
        for col in range(self.combinationsModel.columnCount() - 1):
            checkItem = QStandardItem()
            checkItem.setCheckable(True)
            checkItem.setCheckState(Qt.Unchecked)
            self.combinationsModel.setItem(row, col+1, checkItem)
    
    def onBtnRemove(self):
        selected = self.tvCombinations.selectionModel().currentIndex()
        if selected and selected.row() >= 0:
            self.combinationsModel.removeRow(selected.row())
            self.updateButtonsState()

    def onBtnMoveUp(self):
        selected = self.tvCombinations.selectionModel().currentIndex()
        if selected and selected.row() >= 0 and selected.row() > 0:
            row = selected.row()
            itemRow = self.combinationsModel.takeRow(row)
            self.combinationsModel.insertRow(row-1, itemRow)
            start = self.combinationsModel.index(row-1, 0)
            end = self.combinationsModel.index(
                row-1, self.combinationsModel.columnCount() - 1)
            newSelection = QItemSelection(start, end)
            self.tvCombinations.selectionModel().select(
                newSelection, QItemSelectionModel.ClearAndSelect)
            self.tvCombinations.selectionModel().setCurrentIndex(
                start, QItemSelectionModel.Current)
    
    def onBtnMoveDown(self):
        selected = self.tvCombinations.selectionModel().currentIndex()
        if (selected and selected.row() >= 0 
                and selected.row() < self.combinationsModel.rowCount()):
            row = selected.row()
            itemRow = self.combinationsModel.takeRow(row)
            self.combinationsModel.insertRow(row+1, itemRow)
            start = self.combinationsModel.index(row+1, 0)
            end = self.combinationsModel.index(
                row+1, self.combinationsModel.columnCount() - 1)
            newSelection = QItemSelection(start, end)
            self.tvCombinations.selectionModel().select(
                newSelection, QItemSelectionModel.ClearAndSelect)
            self.tvCombinations.selectionModel().setCurrentIndex(
                start, QItemSelectionModel.Current)


class VariationSettingsWindow(QWidget, Ui_VariationSettingsWindow):
    mClosed:'PYQT_SIGNAL' = pyqtSignal()
    def __init__(self, *args, **kwargs):
        super(VariationSettingsWindow, self).__init__()
        self.mainApp: 'App' = kwargs.pop('mApp')
        self.variationOriginal: Variation = kwargs.pop('variationToEdit', None)
        self.variationToEdit: Variation = None
        self.combinationsStale: bool = False
        self.setupUi(self)
        self.setupExtraElements()
        self.setupEvents()
        self.initVariationData()
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.show()

    def setupExtraElements(self):
        iconPath = os.path.join(utils.getResourcesPath(), 'icon.ico')
        icon = QIcon()
        icon.addPixmap(QPixmap(iconPath), QIcon.Normal, QIcon.Off)
        self.setWindowIcon(icon)
        self.inclusionsModel = QStringListModel()
        self.lvInclusions.setModel(self.inclusionsModel)
        self.exclusionsModel = QStringListModel()
        self.lvExclusions.setModel(self.exclusionsModel)
        self.availableModsModel = QStandardItemModel()
        self.tvAvailableModifiers.setModel(self.availableModsModel)
        self.linkedModsModel = QStandardItemModel()
        self.tvLinkedModifiers.setModel(self.linkedModsModel)

    def setupEvents(self):
        self.btnSave.clicked.connect(self.onBtnSave)
        self.btnConfigureCombinations.clicked.connect(self.onBtnConfigureCombinations)
        # Inclusion and exclusion pattern
        self.btnAddInclusion.clicked.connect(self.onBtnAddInclusion)
        self.btnRemoveInclusion.clicked.connect(
            lambda: self.onRemovePattern(self.lvInclusions))
        self.btnAddExclusion.clicked.connect(self.onBtnAddExclusion)
        self.btnRemoveExclusion.clicked.connect(
            lambda: self.onRemovePattern(self.lvExclusions))
        self.lvInclusions.selectionModel().currentRowChanged.connect(
            lambda selected, _d: self.updatePatternButtonsState())
        self.lvExclusions.selectionModel().currentRowChanged.connect(
            lambda selected, _d: self.updatePatternButtonsState())

        # Link and unlink modifiers
        self.tvAvailableModifiers.selectionModel().currentRowChanged.connect(
            lambda selected, _d: self.updateModButtonsState())
        self.tvLinkedModifiers.selectionModel().currentRowChanged.connect(
            lambda selected, _d: self.updateModButtonsState())
        self.btnLinkModifier.clicked.connect(self.onBtnLinkModifier)
        self.btnLinkAllModifiers.clicked.connect(self.onBtnLinkAllModifiers)
        self.btnUnlinkModifier.clicked.connect(self.onBtnUnlinkModifier)
        self.btnUnlinkAllModifiers.clicked.connect(
            self.onBtnUnlinkAllModifiers)
        self.btnMoveModUp.clicked.connect(self.onBtnMoveModUp)
        self.btnMoveModDown.clicked.connect(self.onBtnMoveModDown)

    def clearModifierLists(self):
        self.linkedModsModel.clear()
        self.availableModsModel.clear()
        self.initModifierHeaders()

    def initModifierHeaders(self):
        self.availableModsModel.insertColumns(0, 3)
        self.availableModsModel.setHeaderData(0, Qt.Horizontal, 'Name')
        self.availableModsModel.setHeaderData(1, Qt.Horizontal, 'Inclusions')
        self.availableModsModel.setHeaderData(2, Qt.Horizontal, 'Exclusions')
        self.linkedModsModel.insertColumns(0, 3)
        self.linkedModsModel.setHeaderData(0, Qt.Horizontal, 'Name')
        self.linkedModsModel.setHeaderData(1, Qt.Horizontal, 'Inclusions')
        self.linkedModsModel.setHeaderData(2, Qt.Horizontal, 'Exclusions')

    def initVariationData(self):
        if self.variationOriginal is None:
            self.variationToEdit = Variation.from_dict(
                {'id': self.mainApp.getNextVariationId()})
        else:
            # Work with a copy so we can rollback any changes if the user cancels
            self.variationToEdit = Variation.from_dict(
                self.variationOriginal.to_dict())
        self.txtName.setText(self.variationToEdit.name)
        self.txtSuffix.setText(self.variationToEdit.suffix)
        self.txtSubfolder.setText(self.variationToEdit.subfolder)
        self.inclusionsModel.setStringList(self.variationToEdit.inclusions)
        self.exclusionsModel.setStringList(self.variationToEdit.exclusions)
        self.clearModifierLists()
        mods = self.mainApp.lookupVariationModifiers(self.variationToEdit)
        availableMods = [x for x in self.mainApp.modifiers if x not in mods]
        for i in range(len(mods)):
            self.addModifierToModel(mods[i], self.linkedModsModel)

        for i in range(len(availableMods)):
            self.addModifierToModel(availableMods[i], self.availableModsModel)

        self.btnLinkAllModifiers.setEnabled(
            self.availableModsModel.rowCount() > 0)
        self.btnUnlinkAllModifiers.setEnabled(
            self.linkedModsModel.rowCount() > 0)
        self.btnConfigureCombinations.setEnabled(
            self.linkedModsModel.rowCount() > 0)

    def addModifierToModel(
            self, modifier: Modifier, model: QStandardItemModel):
        nameItem = ModifierItem(modifier.name, modifier.id)
        inclusionsItem = QStandardItem(
            '|'.join([x for x in modifier.inclusions]))
        exclusionsItem = QStandardItem(
            '|'.join([x for x in modifier.exclusions]))
        index = model.rowCount()
        model.setItem(index, 0, nameItem)
        model.setItem(index, 1, inclusionsItem)
        model.setItem(index, 2, exclusionsItem)

    def applyLinkedMods(self):
        linkedMods = []
        for i in range(self.linkedModsModel.rowCount()):
            modId = self.linkedModsModel.item(i, 0).modifierId
            linkedMods.append(modId)
        self.variationToEdit.modifiers = linkedMods

    def recalculateCombinations(self):
        """
        Recalculate the bitflags of existing combinations when the modifiers are added/removed/sorted
        """
        oldLinkedMods = [x for x in self.variationToEdit.modifiers]
        self.applyLinkedMods()
        if self.combinationsStale and len(self.variationToEdit.modifiers) > 0:
            for comb in self.variationToEdit.combinations:
                bitflags = ''
                for mod in self.variationToEdit.modifiers:
                    oldIndex = utils.findIndex(oldLinkedMods, mod)
                    if oldIndex == -1:
                        bitflags += '0'
                    else:
                        bitflags += comb.bitflags[oldIndex]
                # Set the recalculated flags
                comb.bitflags = bitflags
            self.combinationsStale = False
    
    def updatePatternButtonsState(self):
        selectedInclusion = self.lvInclusions.selectionModel().currentIndex()
        self.btnRemoveInclusion.setEnabled(selectedInclusion and selectedInclusion.row() >= 0)
        selectedExclusion = self.lvExclusions.selectionModel().currentIndex()
        self.btnRemoveExclusion.setEnabled(selectedExclusion and selectedExclusion.row() >= 0)
    
    def updateModButtonsState(self):
        linkedModSelected = self.tvLinkedModifiers.selectionModel().currentIndex()
        availableModSelected = self.tvAvailableModifiers.selectionModel().currentIndex()
        isLinkedModSelected = linkedModSelected and linkedModSelected.row() >= 0
        isAvailableModSelected = availableModSelected and availableModSelected.row() >= 0
        self.btnLinkAllModifiers.setEnabled(self.availableModsModel.rowCount() > 0)
        self.btnUnlinkAllModifiers.setEnabled(self.linkedModsModel.rowCount() > 0)
        self.btnLinkModifier.setEnabled(isAvailableModSelected)
        self.btnUnlinkModifier.setEnabled(isLinkedModSelected)
        self.btnMoveModUp.setEnabled(isLinkedModSelected and linkedModSelected.row() > 0)
        self.btnMoveModDown.setEnabled(isLinkedModSelected and linkedModSelected.row() < self.linkedModsModel.rowCount() - 1)


    def onBtnSave(self):
        if self.combinationsStale and len(self.variationToEdit.combinations) > 0:
            self.infoDialog = QMessageBox(self)
            self.infoDialog.setIcon(QMessageBox.Warning)
            self.infoDialog.setWindowTitle('Attention')
            self.infoDialog.setText('The combinations setup is not in sync with the modifiers.\n'
                + 'Please, click on "Configure combinations..." and confirm that the setup is correct.')
            self.infoDialog.setStandardButtons(QMessageBox.Ok)
            self.infoDialog.setDefaultButton(QMessageBox.Ok)
            self.infoDialog.setWindowModality(Qt.WindowModal)
            self.infoDialog.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
            self.infoDialog.setAttribute(Qt.WA_DeleteOnClose)
            self.infoDialog.open()
            return
        self.variationToEdit.name = self.txtName.text()
        self.variationToEdit.suffix = self.txtSuffix.text()
        self.variationToEdit.subfolder = self.txtSubfolder.text()
        self.variationToEdit.inclusions = self.inclusionsModel.stringList()
        self.variationToEdit.exclusions = self.exclusionsModel.stringList()
        self.applyLinkedMods()
        if self.variationOriginal is None:
            # Add the new variation
            self.mainApp.variations.append(self.variationToEdit)
            # Ask the user if they want to add another one
            self.addAnotherDialog = QMessageBox(self)
            self.addAnotherDialog.setIcon(QMessageBox.Question)
            self.addAnotherDialog.setWindowTitle('Confirmation')
            self.addAnotherDialog.setText('The variation has been added.\n')
            self.addAnotherDialog.setInformativeText('Do you want to add another one?')
            self.addAnotherDialog.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            self.addAnotherDialog.setDefaultButton(QMessageBox.No)
            self.addAnotherDialog.setWindowModality(Qt.WindowModal)
            self.addAnotherDialog.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
            self.addAnotherDialog.setAttribute(Qt.WA_DeleteOnClose)
            self.addAnotherDialog.finished.connect(self.onAddAnotherFinished)
            self.addAnotherDialog.open()
        else:
            # Apply the changes on the original
            self.variationOriginal.load_dict(self.variationToEdit.to_dict())
            self.close()

    def onAddAnotherFinished(self, result:int):
        if QMessageBox.Yes == result:
            self.initVariationData()
        else:
            self.close()

    def onBtnAddInclusion(self):
        if self.onAddPattern(
                self.txtInclusionPatt, self.cbInclusionPattType.currentIndex(),
                self.inclusionsModel):
            self.btnRemoveInclusion.setEnabled(False)

    def onBtnAddExclusion(self):
        if self.onAddPattern(
                self.txtExclusionPatt, self.cbExclusionPattType.currentIndex(),
                self.exclusionsModel):
            self.btnRemoveExclusion.setEnabled(False)

    def onAddPattern(
            self, textWidget: QLineEdit, pattTypeIndex: int,
            listModel: QStringListModel) -> bool:
        pattBody = textWidget.text()
        if not pattBody:
            QMessageBox.critical(self, 'Error', 'The pattern cannot be empty')
            return False
        pattType = 'glob'
        if pattTypeIndex == 1:
            pattType = 'regex'

        if pattType == 'regex' and not utils.isValidRegex(pattBody):
            QMessageBox.critical(
                self, 'Error', 'The pattern is not a valid Regular Expression')
            return False
        pattern = pattType + ':' + pattBody
        sl = listModel.stringList()
        sl.append(pattern)
        listModel.setStringList(sl)
        textWidget.clear()
        return True

    def onRemovePattern(self, listView: QListView):
        selected = listView.selectionModel().currentIndex().row()
        listView.model().removeRow(selected)
        self.updatePatternButtonsState()

    def onLinkModifier(self, index: int):
        self.linkedModsModel.appendRow(self.availableModsModel.takeRow(index))
        self.btnLinkAllModifiers.setEnabled(
            self.availableModsModel.rowCount() > 0)
        self.btnUnlinkAllModifiers.setEnabled(
            self.linkedModsModel.rowCount() > 0)
        self.btnConfigureCombinations.setEnabled(
            self.linkedModsModel.rowCount() > 0)
        self.updateModButtonsState()
        self.combinationsStale = True

    def onUnlinkModifier(self, index: int):
        self.availableModsModel.appendRow(self.linkedModsModel.takeRow(index))
        self.btnLinkAllModifiers.setEnabled(
            self.availableModsModel.rowCount() > 0)
        self.btnUnlinkAllModifiers.setEnabled(
            self.linkedModsModel.rowCount() > 0)
        self.btnConfigureCombinations.setEnabled(
            self.linkedModsModel.rowCount() > 0)
        self.updateModButtonsState()
        self.combinationsStale = True

    def onBtnLinkAllModifiers(self):
        while self.availableModsModel.rowCount() > 0:
            self.onLinkModifier(0)
        self.btnLinkModifier.setEnabled(False)
        self.btnLinkAllModifiers.setEnabled(False)

    def onBtnLinkModifier(self):
        selected = self.tvAvailableModifiers.selectionModel().currentIndex()
        if selected and selected.row() >= 0:
            self.onLinkModifier(selected.row())

    def onBtnUnlinkModifier(self):
        selected = self.tvLinkedModifiers.selectionModel().currentIndex()
        if selected and selected.row() >= 0:
            self.onUnlinkModifier(selected.row())
        if self.linkedModsModel.rowCount() == 0:
            self.btnUnlinkModifier.setEnabled(False)

    def onBtnUnlinkAllModifiers(self):
        while self.linkedModsModel.rowCount() > 0:
            self.onUnlinkModifier(0)
        self.btnUnlinkModifier.setEnabled(False)
        self.btnUnlinkAllModifiers.setEnabled(False)

    def onBtnMoveModUp(self):
        selected = self.tvLinkedModifiers.selectionModel().currentIndex()
        if selected and selected.row() >= 0 and selected.row() > 0:
            row = selected.row()
            itemRow = self.linkedModsModel.takeRow(row)
            self.linkedModsModel.insertRow(row-1, itemRow)
            start = self.linkedModsModel.index(row-1, 0)
            end = self.linkedModsModel.index(
                row-1, self.linkedModsModel.columnCount() - 1)
            newSelection = QItemSelection(start, end)
            self.tvLinkedModifiers.selectionModel().select(
                newSelection, QItemSelectionModel.ClearAndSelect)
            self.tvLinkedModifiers.selectionModel().setCurrentIndex(
                start, QItemSelectionModel.Current)
            self.combinationsStale = True
            

    def onBtnMoveModDown(self):
        selected = self.tvLinkedModifiers.selectionModel().currentIndex()
        if selected and isinstance(
                selected.row(),
                int) and selected.row() < self.linkedModsModel.rowCount():
            row = selected.row()
            itemRow = self.linkedModsModel.takeRow(row)
            self.linkedModsModel.insertRow(row+1, itemRow)
            start = self.linkedModsModel.index(row+1, 0)
            end = self.linkedModsModel.index(
                row+1, self.linkedModsModel.columnCount() - 1)
            newSelection = QItemSelection(start, end)
            self.tvLinkedModifiers.selectionModel().select(
                newSelection, QItemSelectionModel.ClearAndSelect)
            self.tvLinkedModifiers.selectionModel().setCurrentIndex(
                start, QItemSelectionModel.Current)
            selected = self.tvLinkedModifiers.selectionModel().currentIndex()
            self.combinationsStale = True

    def onBtnConfigureCombinations(self):
        self.recalculateCombinations()
        self.variationToEdit.name = self.txtName.text()
        self.combinationsDialog = ModifierCombinationsDialog(
            self, mApp=self.mainApp, variationToEdit=self.variationToEdit)
        self.combinationsDialog.open()

    def closeEvent(self, event: QCloseEvent):
        self.mClosed.emit()
        event.accept()


class ModifierSettingsWindow(QWidget, Ui_ModifierSettingsWindow):
    mClosed:'PYQT_SIGNAL' = pyqtSignal()
    def __init__(self, *args, **kwargs):
        super(ModifierSettingsWindow, self).__init__()
        self.mainApp: 'App' = kwargs.pop('mApp')
        self.modifierOriginal: Modifier = kwargs.pop('modifierToEdit', None)
        self.modifierToEdit: Modifier = None
        self.setupUi(self)
        self.setupExtraElements()
        self.setupEvents()
        self.initModifierData()
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.show()

    def setupExtraElements(self):
        iconPath = os.path.join(utils.getResourcesPath(), 'icon.ico')
        icon = QIcon()
        icon.addPixmap(QPixmap(iconPath), QIcon.Normal, QIcon.Off)
        self.setWindowIcon(icon)
        self.inclusionsModel = QStringListModel()
        self.lvInclusions.setModel(self.inclusionsModel)
        self.exclusionsModel = QStringListModel()
        self.lvExclusions.setModel(self.exclusionsModel)

    def setupEvents(self):
        self.btnSave.clicked.connect(self.onBtnSave)
        self.btnAddInclusion.clicked.connect(self.onBtnAddInclusion)
        self.btnRemoveInclusion.clicked.connect(
            lambda: self.onRemovePattern(
                self.btnRemoveInclusion, self.lvInclusions))
        self.btnAddExclusion.clicked.connect(self.onBtnAddExclusion)
        self.btnRemoveExclusion.clicked.connect(
            lambda: self.onRemovePattern(
                self.btnRemoveExclusion, self.lvExclusions))
        self.lvInclusions.selectionModel().currentRowChanged.connect(
            lambda selected, _d: self.btnRemoveInclusion.setEnabled(
                selected and isinstance(selected.row(),
                                        int)))
        self.lvExclusions.selectionModel().currentRowChanged.connect(
            lambda selected, _d: self.btnRemoveExclusion.setEnabled(
                selected and isinstance(selected.row(),
                                        int)))

    def initModifierData(self):
        if self.modifierOriginal is None:
            self.modifierToEdit = Modifier.from_dict(
                {'id': self.mainApp.getNextModifierId()})
        else:
            self.modifierToEdit = Modifier.from_dict(
                self.modifierOriginal.to_dict())
        self.txtName.setText(self.modifierToEdit.name)
        self.txtSuffix.setText(self.modifierToEdit.suffix)
        self.inclusionsModel.setStringList(self.modifierToEdit.inclusions)
        self.exclusionsModel.setStringList(self.modifierToEdit.exclusions)

    def onBtnSave(self):
        self.modifierToEdit.name = self.txtName.text()
        self.modifierToEdit.suffix = self.txtSuffix.text()
        self.modifierToEdit.inclusions = self.inclusionsModel.stringList()
        self.modifierToEdit.exclusions = self.exclusionsModel.stringList()
        if self.modifierOriginal is None:
            # Add the new modifier
            self.mainApp.modifiers.append(self.modifierToEdit)
            # Ask the user if they want to add another one
            self.addAnotherDialog = QMessageBox(self)
            self.addAnotherDialog.setIcon(QMessageBox.Question)
            self.addAnotherDialog.setWindowTitle('Confirmation')
            self.addAnotherDialog.setText('The modifier has been added.\n')
            self.addAnotherDialog.setInformativeText('Do you want to add another one?')
            self.addAnotherDialog.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            self.addAnotherDialog.setDefaultButton(QMessageBox.No)
            self.addAnotherDialog.setWindowModality(Qt.WindowModal)
            self.addAnotherDialog.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
            self.addAnotherDialog.setAttribute(Qt.WA_DeleteOnClose)
            self.addAnotherDialog.finished.connect(self.onAddAnotherFinished)
            self.addAnotherDialog.open()
        else:
            self.modifierOriginal.load_dict(self.modifierToEdit.to_dict())
            self.close()

    def onAddAnotherFinished(self, result:int):
        if QMessageBox.Yes == result:
            self.initModifierData()
        else:
            self.close()

    def onBtnAddInclusion(self):
        if self.onAddPattern(
                self.txtInclusionPatt, self.cbInclusionPattType.currentIndex(),
                self.inclusionsModel):
            self.btnRemoveInclusion.setEnabled(False)

    def onBtnAddExclusion(self):
        if self.onAddPattern(
                self.txtExclusionPatt, self.cbExclusionPattType.currentIndex(),
                self.exclusionsModel):
            self.btnRemoveExclusion.setEnabled(False)

    def onAddPattern(
            self, textWidget: QLineEdit, pattTypeIndex: int,
            listModel: QStringListModel) -> bool:
        pattBody = textWidget.text()
        if not pattBody:
            QMessageBox.critical(self, 'Error', 'The pattern cannot be empty')
            return False
        pattType = 'glob'
        if pattTypeIndex == 1:
            pattType = 'regex'

        if pattType == 'regex' and not utils.isValidRegex(pattBody):
            QMessageBox.critical(
                self, 'Error', 'The pattern is not a valid Regular Expression')
            return False
        pattern = pattType + ':' + pattBody
        sl = listModel.stringList()
        sl.append(pattern)
        listModel.setStringList(sl)
        textWidget.clear()
        return True

    def onRemovePattern(self, sender: QPushButton, listView: QListView):
        selected = listView.currentIndex().row()
        listView.model().removeRow(selected)
        if listView.model().rowCount() == 0:
            sender.setEnabled(False)

    def closeEvent(self, event: QCloseEvent):
        self.mClosed.emit()
        event.accept()
