import os
import sys
import time
import math
from typing import TYPE_CHECKING, List, Tuple

from PyQt5.QtWidgets import QMainWindow, QFileDialog, QApplication, QGraphicsScene, QProgressDialog, QAction, QMenu, QMessageBox
from PyQt5.QtCore import QObject, QThread, pyqtSignal, Qt
from PyQt5.QtGui import QPixmap, QImage, QStandardItemModel, QStandardItem, QIcon, QCloseEvent

from models import ItemNode, AppState, Modifier, ModifierCombination
import utils
from app import App
from gui import Ui_MainWindow
from views import ModifierSettingsWindow, VariationSettingsWindow

if TYPE_CHECKING:
    from PyQt5.QtCore import PYQT_SIGNAL

VARIATIONS_CONFIG_FILEPATH = os.path.join(utils.getBasedir(), 'variations_settings.json')

ACTION_APPLY = 'Apply'
BASE_WINDOW_TITLE = 'ILLustration Variations Exporter'

class PSDLoadWorker(QObject):

    finished = pyqtSignal()
    psdLoaded = pyqtSignal(AppState)

    def __init__(self, psdFile:str, mainApp: 'App'):
        super(PSDLoadWorker, self).__init__()
        self.psdFile = psdFile
        self.mainApp = mainApp

    def run(self):
        print('Loading started...')
        self.mainApp.loadPSD(self.psdFile)
        self.psdLoaded.emit(self.mainApp.getState())
        self.finished.emit()
        print('Loading finished')

class PSDRenderWorker(QObject):
    finished = pyqtSignal()
    psdRendered = pyqtSignal(AppState)

    def __init__(self, thumbnailSize:Tuple[int, int], mainApp: 'App', reloadPSD:bool = False):
        super(PSDRenderWorker, self).__init__()
        self.thumbnailSize = thumbnailSize
        self.mainApp = mainApp
        self.reloadPSD = reloadPSD
    
    def run(self):
        print('Rendering started...')
        startTs = time.time()
        self.mainApp.renderPSD(self.thumbnailSize, self.reloadPSD)
        self.psdRendered.emit(self.mainApp.getState())
        self.finished.emit()
        print('Rendering finished')
        diff = time.time() - startTs
        print('It took {0} seconds'.format(diff))

class PSDExportWorker(QObject):
    finished:'PYQT_SIGNAL' = pyqtSignal()
    imageExported:'PYQT_SIGNAL' = pyqtSignal(str)

    def __init__(self, mainApp: 'App', baseOutDir:str) -> None:
        super(PSDExportWorker, self).__init__()
        self.mainApp = mainApp
        self.baseOutDir = baseOutDir
    
    def run(self):
        totalStart = time.time()
        baseFileName = os.path.basename(self.mainApp.originalPSDFilePath)
        baseFileName = baseFileName[0:baseFileName.rfind('.')]
        for v in self.mainApp.variations:
            outDir = self.baseOutDir
            if len(v.subfolder) > 0:
                outDir = os.path.join(self.baseOutDir, v.subfolder)
            os.makedirs(outDir, exist_ok=True)
            nodes = self.mainApp.applyVariation(v)
            mods = self.mainApp.lookupVariationModifiers(v)
            combs = v.combinations
            if len(mods) == 0:
                # There are no modifiers, create an empty one with an empty combination
                mods.append(Modifier.from_dict({'id': -1, 'name': '<Empty>'}))
                combs.append(ModifierCombination.from_dict({'name': '<Empty>', 'bitflags': '0'}))
            if len(combs) == 0:
                combs = [ModifierCombination.from_dict({'name': utils.combinationName(mods, v.name, '{0:b}'.format(x)), 'bitflags': '{0:b}'.format(x)}) for x in range(int(math.pow(2, len(mods))))]
            for c in combs:
                imageStart = time.time()
                modsToApply = self.mainApp.modifiersToApply(mods, c.bitflags)
                suffix = utils.getSuffixFor(v, modsToApply)
                fname = utils.getUniqueFilename(outDir, baseFileName + suffix, '.png')
                self.mainApp.applyModifiers(mods, c.bitflags, True, nodes)
                im = self.mainApp.renderPSD(reloadPSD=True)
                im.save(fname)
                self.imageExported.emit(fname)
                imageEllapsed = time.time() - imageStart
                print('Image exported in {0} seconds'.format(imageEllapsed))
        self.finished.emit()
        totalEllapsed = time.time() - totalStart
        print('The process took {0} seconds'.format(totalEllapsed))



class TreeNodeItem(QStandardItem):
    def __init__(self, text:str, node_path:str):
        super(QStandardItem, self).__init__(text)
        self.node_path = node_path

class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__()
        self.mainApp: 'App' = kwargs.pop('mApp')
        self.variationActionMenus:List[QMenu] = []
        self.modifierActionMenus:List[QMenu] = []
        self.baseOutDir = None
        self.exportProgressDialog = None
        self.setupUi(self)
        self.setupExtraElements()
        self.loadSettings()
        self.setupEvents()
        self.setAttribute(Qt.WA_DeleteOnClose)

    def setupExtraElements(self):
        icon = QIcon()
        iconPath = os.path.join(utils.getResourcesPath(), 'icon.ico')
        icon.addPixmap(QPixmap(iconPath), QIcon.Normal, QIcon.Off)
        self.setWindowIcon(icon)
        self.gsImage = QGraphicsScene()
        self.treeLayersModel = QStandardItemModel()
        self.treeLayersModel.insertColumns(0, 2)
        self.treeLayersModel.setHeaderData(0, Qt.Horizontal, 'Layers')
        self.treeLayersModel.setHeaderData(1, Qt.Horizontal, 'Visible')
        self.treeLayers.setModel(self.treeLayersModel)

    def setupEvents(self):
        self.actionAddNewVariation.triggered.connect(self.onAddNewVariation)
        self.actionAddNewModifier.triggered.connect(self.onAddNewModifier)
        self.btnBrowseInput.clicked.connect(self.onBtnBrowseInputClicked)
        self.btnResetLayers.clicked.connect(self.onBtnReset)
        self.btnUpdatePreview.clicked.connect(self.onBtnUpdatePreviewClicked)
        self.btnBrowseOutputDir.clicked.connect(self.onBtnBrowseOutput)
        self.btnStart.clicked.connect(self.onBtnStart)
        
        
    def loadSettings(self):
        self.mainApp.loadVariationConfig(VARIATIONS_CONFIG_FILEPATH)
        self.updateMenus()

    def saveSettings(self):
        self.mainApp.saveVariationConfig(VARIATIONS_CONFIG_FILEPATH)

    def updateMenus(self):
        # Disconnect previous actions
        for men in self.variationActionMenus:
            for act in men.actions():
                act.disconnect()
        for men in self.modifierActionMenus:
            for act in men.actions():
                act.disconnect()
        # Reset the Window title
        self.setWindowTitle(BASE_WINDOW_TITLE)
        # Clear the action lists
        self.variationActionMenus = []
        self.modifierActionMenus = []
        # Clear menus
        self.menuVariations.clear()
        self.menuModifiers.clear()
        # Re-add the Add New actions
        self.menuVariations.addAction(self.actionAddNewVariation)
        self.menuModifiers.addAction(self.actionAddNewModifier)
        # Fill it up with the variations and modifiers created
        if len(self.mainApp.variations) > 0:
            self.menuVariations.addSeparator()
            for i in range(len(self.mainApp.variations)):
                editApplyMenu = QMenu(self.mainApp.variations[i].name, self)
                editAct = QAction('Edit', self)
                editAct.triggered.connect(lambda _chk, index=i: self.onEditVariation(index))
                applyAct = QAction(ACTION_APPLY, self)
                applyAct.setCheckable(True)
                applyAct.triggered.connect(lambda checked, index=i: self.onApplyVariation(checked, index))
                deleteAct = QAction('Delete', self)
                deleteAct.triggered.connect(lambda _chk, index=i: self.onDeleteVariation(index))
                editApplyMenu.addAction(editAct)
                editApplyMenu.addAction(applyAct)
                editApplyMenu.addAction(deleteAct)
                self.variationActionMenus.append(editApplyMenu)
                self.menuVariations.addAction(editApplyMenu.menuAction())
        if len(self.mainApp.modifiers) > 0:
            self.menuModifiers.addSeparator()
            for i in range(len(self.mainApp.modifiers)):
                editApplyMenu = QMenu(self.mainApp.modifiers[i].name, self)
                editAct = QAction('Edit', self)
                editAct.triggered.connect(lambda _chk, index=i: self.onEditModifier(index))
                applyAct = QAction(ACTION_APPLY, self)
                applyAct.setCheckable(True)
                applyAct.triggered.connect(lambda checked, index=i: self.onApplyModifier(checked, index))
                deleteAct = QAction('Delete', self)
                deleteAct.triggered.connect(lambda _chk, index=i: self.onDeleteModifier(index))
                editApplyMenu.addAction(editAct)
                editApplyMenu.addAction(applyAct)
                editApplyMenu.addAction(deleteAct)
                self.modifierActionMenus.append(editApplyMenu)
                self.menuModifiers.addAction(editApplyMenu.menuAction())


    def cleanWidgets(self):
        self.gsImage.clear()
        self.treeLayersModel.invisibleRootItem().setRowCount(0)

    def updateLayersVisibility(self):
        rootItem = self.treeLayersModel.invisibleRootItem()
        node_list = self.getChildrenRecursively(rootItem)
        self.mainApp.updateLayersVisibility(node_list)
    
    def getChildrenRecursively(self, item:QStandardItem):
        children = []
        for i in range(item.rowCount()):
            child = item.child(i, 0)
            node = ItemNode(item.text(), child.checkState() == Qt.Checked or child.checkState() == Qt.PartiallyChecked)
            node_path = getattr(child, 'node_path', '')
            if len(node_path) > 0:
                node.node_path = node_path
            children.append(node)
            if child.hasChildren():
                node.children = self.getChildrenRecursively(child)
        return children


    def prepareLoadingDialog(self, labelText:str):
        self.loadingInProgress = QProgressDialog(labelText, None, 0, 0, self)
        self.loadingInProgress.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        self.loadingInProgress.setWindowModality(Qt.WindowModal)

    def preparePSDLoad(self, psd_file:str):
        # Create thread and worker
        self.psdLoadThread = QThread()
        self.psdLoadWorker = PSDLoadWorker(psd_file, self.mainApp)
        # Move worker to thread
        self.psdLoadWorker.moveToThread(self.psdLoadThread)
        # Connect signals
        self.psdLoadThread.started.connect(self.psdLoadWorker.run)
        self.psdLoadWorker.finished.connect(self.psdLoadThread.quit)
        self.psdLoadWorker.finished.connect(self.psdLoadWorker.deleteLater)
        self.psdLoadThread.finished.connect(self.psdLoadThread.deleteLater)
        self.psdLoadWorker.psdLoaded.connect(self.onPSDFileLoaded)

    def startPSDLoad(self):
        self.psdLoadThread.start()
    
    def preparePSDRender(self, reloadPSD:bool = False):
        max_width = self.gvLoadedImage.width()
        max_height = 10000
        # Create thread and worker
        self.psdRenderThread = QThread()
        self.psdRenderWorker = PSDRenderWorker((max_width, max_height), self.mainApp, reloadPSD)
        # Move worker to thread
        self.psdRenderWorker.moveToThread(self.psdRenderThread)
        # Connect signals
        self.psdRenderThread.started.connect(self.psdRenderWorker.run)
        self.psdRenderWorker.finished.connect(self.psdRenderThread.quit)
        self.psdRenderWorker.finished.connect(self.psdRenderWorker.deleteLater)
        self.psdRenderThread.finished.connect(self.psdRenderThread.deleteLater)
        self.psdRenderWorker.psdRendered.connect(self.onPSDRendered)
        self.psdRenderWorker.finished.connect(self.onPSDRenderFinished)
    
    def startPSDRender(self):
        self.psdRenderThread.start()
    
    def prepareExportWorker(self):
        # Create thread and worker
        self.exportWorkerThread = QThread()
        self.exportWorker = PSDExportWorker(self.mainApp, self.baseOutDir)
        # Move worker to thread
        self.exportWorker.moveToThread(self.exportWorkerThread)
        # Connect signals
        self.exportWorkerThread.started.connect(self.exportWorker.run)
        self.exportWorker.finished.connect(self.exportWorkerThread.quit)
        self.exportWorker.finished.connect(self.exportWorker.deleteLater)
        self.exportWorkerThread.finished.connect(self.exportWorkerThread.deleteLater)
        self.exportWorker.imageExported.connect(self.onImageExported)
        self.exportWorker.finished.connect(self.exportProgressDialog.deleteLater)
        self.exportWorker.finished.connect(lambda: self.toggleAllButtons(True))
    
    def startExportWorker(self):
        self.exportWorkerThread.start()
    
    def prepareExportProgress(self):
        self.totalImagesToExport = 0
        self.currentImagesExported = 0
        for v in self.mainApp.variations:
            if len(v.modifiers) == 0:
                self.totalImagesToExport += 1
            elif len(v.combinations) > 0:
                self.totalImagesToExport += len(v.combinations)
            else:
                self.totalImagesToExport += int(math.pow(2, len(v.modifiers)))
        self.exportProgressDialog = QProgressDialog('Exporting...', 'Cancel', 0, self.totalImagesToExport, self)
        self.exportProgressDialog.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        self.exportProgressDialog.setWindowModality(Qt.WindowModal)

    def loadLayersTreeview(self, original:bool = False):
        layers = list(reversed(self.mainApp.layerHierarchy(original)))
        rootItem = self.treeLayersModel.invisibleRootItem()
        rootItem.setRowCount(0)
        for i in range(len(layers)):
            lay = layers[i]
            self.loadChildrenRecursive(lay, rootItem, i)

    def loadChildrenRecursive(self, nodeLayer:ItemNode, parentItem:QStandardItem, index:int):
        layerItem = TreeNodeItem(nodeLayer.label, nodeLayer.node_path)
        layerItem.setCheckable(True)
        layerItem.setCheckState(Qt.Checked if nodeLayer.visible else Qt.Unchecked)
        visibilityItem = QStandardItem('Yes' if nodeLayer.visible else 'No')
        parentItem.setChild(index, 0, layerItem)
        parentItem.setChild(index, 1, visibilityItem)
        if len(nodeLayer.children) > 0:
            childrenReverse = list(reversed(nodeLayer.children))
            for i in range(len(childrenReverse)):
                child = childrenReverse[i]
                self.loadChildrenRecursive(child, layerItem, i)
    
    def refreshLayersTreeview(self, original:bool = False, refreshVisibility:bool = False):
        layers = list(reversed(self.mainApp.layerHierarchy(original)))
        rootItem = self.treeLayersModel.invisibleRootItem()
        for i in range(len(layers)):
            lay = layers[i]
            self.refreshChildrenRecursive(lay, rootItem, i, refreshVisibility)
    
    def refreshChildrenRecursive(self, nodeLayer:ItemNode, parentItem:QStandardItem, index:int, refreshVisibility:bool):
        layerItem = parentItem.child(index, 0)
        layerItem.setCheckState(Qt.Checked if nodeLayer.visible else Qt.Unchecked)
        if refreshVisibility:
            visibilityItem = parentItem.child(index, 1)
            visibilityItem.setText('Yes' if nodeLayer.visible else 'No')
        if len(nodeLayer.children) > 0:
            childrenReverse = list(reversed(nodeLayer.children))
            for i in range(len(childrenReverse)):
                child = childrenReverse[i]
                self.refreshChildrenRecursive(child, layerItem, i, refreshVisibility)
    
    def resetLayersState(self):
        if self.mainApp.psd is not None:
            self.refreshLayersTreeview(True)
        # Reload the menus to clear all the checked items
        self.updateMenus()

    def checkBtnStart(self):
        self.btnStart.setEnabled(self.mainApp.psd is not None and self.baseOutDir is not None)

    def toggleAllButtons(self, enabled:bool):
        self.btnBrowseInput.setEnabled(enabled)
        self.btnBrowseOutputDir.setEnabled(enabled)
        self.btnResetLayers.setEnabled(enabled)
        self.btnUpdatePreview.setEnabled(enabled)
        self.btnStart.setEnabled(enabled)

    def onPSDRenderFinished(self):
        self.btnBrowseInput.setEnabled(True)
        self.loadingInProgress.setRange(0,1)
        self.loadingInProgress.setValue(1)
        self.loadingInProgress.deleteLater()

    def onPSDFileLoaded(self, appState:AppState):
        print('onPSDFileLoaded slot')
        print(appState)
        self.mainApp.refreshState(appState)
        self.btnBrowseInput.setEnabled(True)
        self.loadingInProgress.setRange(0,1)
        self.loadingInProgress.setValue(1)
        self.loadingInProgress.deleteLater()
        self.loadLayersTreeview()
        self.btnResetLayers.setEnabled(True)
        self.btnUpdatePreview.setEnabled(True)
        self.checkBtnStart()
        # Reload the menu
        self.updateMenus()
    
    def onPSDRendered(self, appState:AppState):
        print('onPSDRendered slot')
        self.mainApp.refreshState(appState)
        print('loading image into Qt')
        im = appState.thumbnail.convert("RGBA")
        im_data = im.tobytes("raw", "RGBA")
        qim = QImage(im_data, im.size[0], im.size[1], QImage.Format_RGBA8888)
        self.loadedImage = QPixmap.fromImage(qim)
        print('image loaded')
        self.gsImage.clear()
        self.gsImage.addPixmap(self.loadedImage)
        self.gvLoadedImage.setScene(self.gsImage)
        print('psdFileLoaded slot end')
        self.refreshLayersTreeview(refreshVisibility = True)
        self.btnResetLayers.setEnabled(True)
        self.btnUpdatePreview.setEnabled(True)

    def onBtnBrowseInputClicked(self):
        psd_file, _ign = QFileDialog.getOpenFileName(self, 'Open PSD file', filter='PhotoShop File (*.psd)')
        if psd_file:
            # Clean old data
            self.cleanWidgets()
            self.txtInputFile.setText(psd_file)
            self.btnBrowseInput.setEnabled(False)
            self.preparePSDLoad(psd_file)
            self.startPSDLoad()
            # Prepare the progress dialog
            self.prepareLoadingDialog('Loading PSD...')
    
    def onBtnUpdatePreviewClicked(self):
        if self.mainApp.psd is not None:
            self.updateLayersVisibility()
            self.gsImage.clear()
            self.btnUpdatePreview.setEnabled(False)
            self.btnResetLayers.setEnabled(False)
            self.preparePSDRender(True)
            self.startPSDRender()
            self.prepareLoadingDialog('Rendering PSD...')

    def onBtnReset(self):
        self.resetLayersState()

    def onAddNewVariation(self):
        self.variationSettings = VariationSettingsWindow(mApp = self.mainApp)
        self.variationSettings.mClosed.connect(self.resetLayersState)
    
    def onAddNewModifier(self):
        self.modifierSettings = ModifierSettingsWindow(mApp = self.mainApp)
        self.modifierSettings.mClosed.connect(self.resetLayersState)
    
    def onEditVariation(self, index:int):
        variation = self.mainApp.variations[index]
        self.variationSettings = VariationSettingsWindow(mApp = self.mainApp, variationToEdit=variation)
        self.variationSettings.mClosed.connect(self.resetLayersState)
    
    def onEditModifier(self, index:int):
        modifier = self.mainApp.modifiers[index]
        self.modifierSettings = ModifierSettingsWindow(mApp = self.mainApp, modifierToEdit=modifier)
        self.modifierSettings.mClosed.connect(self.resetLayersState)

    def onApplyVariation(self, apply:bool, index:int):
        if self.mainApp.psd is None:
            QMessageBox.critical(self, 'Error', 'Load a PSD file first')
            applyAct = [x for x in self.variationActionMenus[index].actions() if x.text() == ACTION_APPLY][0]
            applyAct.setChecked(False)
            return
        winTitle = BASE_WINDOW_TITLE
        if apply:
            # Uncheck the other variations
            for i in range(len(self.variationActionMenus)):
                if i != index:
                    applyAct = [x for x in self.variationActionMenus[i].actions() if x.text() == ACTION_APPLY][0]
                    applyAct.setChecked(False)
            # Uncheck all the modifiers
            for m in self.modifierActionMenus:
                for act in m.actions():
                    if act.text() == ACTION_APPLY:
                        act.setChecked(False)
            # Finally apply the variation
            variation = self.mainApp.variations[index]
            self.mainApp.applyVariation(variation, True)
            self.refreshLayersTreeview()
            winTitle += ' - ' + variation.name
        
        self.setWindowTitle(winTitle)
    
    def onApplyModifier(self, apply:bool, index:int):
        checkedAct = [x for x in self.modifierActionMenus[index].actions() if x.text() == ACTION_APPLY][0]
        if self.mainApp.psd is None:
            QMessageBox.critical(self, 'Error', 'Load a PSD file first')
            checkedAct.setChecked(False)
            return
        activeVariation = None
        for i in range(len(self.variationActionMenus)):
            for act in self.variationActionMenus[i].actions():
                if act.text() == ACTION_APPLY and act.isChecked():
                    activeVariation = self.mainApp.variations[i]
        if activeVariation is None:
            QMessageBox.critical(self, 'Error', 'Apply a variation first')
            checkedAct.setChecked(False)
            return
        mods = self.mainApp.lookupVariationModifiers(activeVariation)
        checkedMod = self.mainApp.modifiers[index]
        if checkedMod not in mods:
            QMessageBox.warning(self, 'Warning', 'This modifier is not linked to the active variation')
            checkedAct.setChecked(False)
            return
        nodes = self.mainApp.applyVariation(activeVariation)
        bitflags = ''
        for m in mods:
            idx = utils.findIndex(self.mainApp.modifiers, m)
            if idx == index:
                bitflags += '1' if apply else '0'
            elif idx >= 0 and idx < len(self.modifierActionMenus):
                applyAct = [x for x in self.modifierActionMenus[idx].actions() if x.text() == ACTION_APPLY][0]
                bitflags += '1' if applyAct.isChecked() else '0'
        activeMods = self.mainApp.modifiersToApply(mods, bitflags)
        winTitle = BASE_WINDOW_TITLE + ' - ' + activeVariation.name
        if len(activeMods) > 0:
            winTitle += ' ['
            winTitle += '|'.join([m.name for m in activeMods])
            winTitle += ']'
        self.setWindowTitle(winTitle)
        self.mainApp.applyModifiers(mods, bitflags, True, nodes)
        self.refreshLayersTreeview()
    
    def onDeleteVariation(self, index:int):
        variation = self.mainApp.variations[index]
        ret = QMessageBox.question(self, 'Confirmation', 
            'Are you sure you want to delete the variation {0}?'.format(variation.name),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if QMessageBox.Yes == ret:
            self.mainApp.variations.pop(index)
            self.resetLayersState()
    
    def onDeleteModifier(self, index:int):
        modifier = self.mainApp.modifiers[index]
        linkedVariations = []
        for v in self.mainApp.variations:
            if utils.findIndex(v.modifiers, modifier.id) != -1:
                linkedVariations.append(v)
        variationName = ''
        if len(linkedVariations) > 0:
            variationName += linkedVariations[0].name
            additional = len(linkedVariations) - 1
            if additional > 0:
                variationName += ' and {0} more'.format(additional)
            QMessageBox.critical(self, 'Error', 'This modifier cannot be deleted because it is linked to {0}'.format(variationName))
            return
        # if we get here confirm before deletion
        ret = QMessageBox.question(self, 'Confirm', 
            'Are you sure you want to delete the modifier {0}?'.format(modifier.name),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if QMessageBox.Yes == ret:
            self.mainApp.modifiers.pop(index)
            self.resetLayersState()
    
    def onBtnBrowseOutput(self):
        self.baseOutDir = QFileDialog.getExistingDirectory(self, 'Select the output directory')
        self.txtOutputDir.setText(self.baseOutDir)
        self.checkBtnStart()

    def onBtnStart(self):
        if len(os.listdir(self.baseOutDir)) > 0:
            ret = QMessageBox.question(self, 'Confirmation', 
                'The output directory is not empty.\nAre you sure your want to use it?',
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if QMessageBox.No == ret:
                return
        self.prepareExportProgress()
        self.prepareExportWorker()
        self.startExportWorker()
        self.toggleAllButtons(False)
    
    def onImageExported(self, imgPath:str):
        print('Image exported to {0}'.format(imgPath))
        self.currentImagesExported += 1
        self.exportProgressDialog.setValue(self.currentImagesExported)

    def onClosed(self, targetName: str):
        print(targetName + " was closed")

    def closeEvent(self, event: QCloseEvent):
        self.saveSettings()
        event.accept()

def main(app: 'App'):
    qtApp = QApplication(sys.argv)
    window = MainWindow(mApp=app)
    window.show()
    ret = qtApp.exec()
    print('Qt Event Loop ended')
    sys.exit(ret)

if __name__ == '__main__':
    main(App())