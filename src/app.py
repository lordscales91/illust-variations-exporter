
import os
import json
import tempfile
import fnmatch
import re
import shutil

from typing import Tuple, List, Dict

from psd_tools import PSDImage
from PIL import Image

from models import ItemNode, AppState, Variation, Modifier

CLIP_LAYER_PATH = 'clp'

class App:
    """
    Main class to hold all the application state and main logic.
    """

    def __init__(self):
        self.psd:PSDImage = None
        self.thumbnail: Image.Image = None
        self.originalLayerHierarchy: List[ItemNode] = None
        self.originalPSDFilePath: str = None
        self.variations:List[Variation] = []
        self.modifiers:List[Modifier] = []

    def loadPSD(self, fpath: str):
        self.psd = PSDImage.open(fpath)
        self.originalPSDFilePath = fpath
        # Clean up old state when loading a new PSD file
        self.thumbnail = None
        self.originalLayerHierarchy = None

    def renderPSD(self, target_size: Tuple[int, int] = None, reloadPSD:bool = False) -> Image.Image:
        if reloadPSD:
            with tempfile.TemporaryDirectory() as tmpdir:
                fpath = os.path.join(tmpdir, 'file.psd')
                self.psd.save(fpath)
                self.psd = PSDImage.open(fpath)
        self.thumbnail = self.psd.composite(ignore_preview=True, force=True)
        if target_size is not None:
            self.thumbnail.thumbnail(target_size, Image.ANTIALIAS)
        return self.thumbnail

    def refreshState(self, state: AppState):
        self.psd = state.psd

    def getState(self) -> AppState:
        return AppState(self.psd, self.thumbnail)

    def layerHierarchy(self, original:bool = False) -> List[ItemNode]:
        if original and self.originalLayerHierarchy is not None:
            # The original hierarchy was requested, and we have it. Return it directly
            return self.originalLayerHierarchy

        node_list = []
        for i in range(len(list(self.psd))):
            layer = self.psd[i]
            node_path = str(i)
            node = ItemNode(layer.name, layer.visible, node_path)
            node_list.append(node)
            node_list.extend(self.getClipLayers(layer, node_path))
            node.children = self.getChildrenRecursive(layer, node_path)

        if self.originalLayerHierarchy is None:
            self.originalLayerHierarchy = node_list
        return node_list
    
    def getClipLayers(self, layer, node_path:str):
        clip_layers = []
        if hasattr(layer, 'clip_layers'):
            for i in range(len(list(layer.clip_layers))):
                clip = layer.clip_layers[i]
                node = ItemNode(clip.name, clip.visible, node_path + '.' + CLIP_LAYER_PATH + '.' + str(i))
                clip_layers.append(node)
        return clip_layers

    def getChildrenRecursive(self, parentLayer, parent_path:str):
        children = []
        if parentLayer.is_group():
            for i in range(len(list(parentLayer))):
                childLayer = parentLayer[i]
                node_path = parent_path + '.' + str(i)
                child = ItemNode(childLayer.name, childLayer.visible, node_path)
                children.append(child)
                children.extend(self.getClipLayers(childLayer, node_path))
                child.children = self.getChildrenRecursive(childLayer, node_path)
        return children
    
    def getLayerByNodePath(self, node_path:str):
        layer = None
        parts = node_path.split('.')
        parent = self.psd
        for p in parts:
            if p.isdigit():
                layer = parent[int(p)]
                parent = layer
            elif p == CLIP_LAYER_PATH and hasattr(parent, 'clip_layers'):
                parent = list(parent.clip_layers)
        return layer

    def updateLayersVisibility(self, layersTree:List[ItemNode]):
        for i in range(len(layersTree)):
            item = layersTree[i]
            layer = self.getLayerByNodePath(item.node_path)
            layer.visible = item.visible
            if layer.is_group():
                self.updateLayersVisibility(item.children)

    def loadVariationConfig(self, confFile:str) -> Tuple[List[Variation], List[Modifier]]:
        self.variations = []
        self.modifiers = []
        if os.path.isfile(confFile):
            with open(confFile, 'rt') as fp:
                data:Dict = json.load(fp)
                self.variations =  [Variation.from_dict(x) for x in data.get('variations', [])]
                self.modifiers = [Modifier.from_dict(x) for x in data.get('modifiers', [])]

        return (self.variations, self.modifiers)
    
    def saveVariationConfig(self, confFile:str) -> None:
        varDicts = [x.to_dict() for x in self.variations]
        modDicts = [m.to_dict() for m in self.modifiers]
        data = {'variations': varDicts, 'modifiers': modDicts}
        if os.path.exists(confFile):
            # Make a backup of the previous config file
            shutil.copyfile(confFile, confFile+'.bak')
        with open(confFile, 'wt') as fp:
            json.dump(data, fp)
    
    def getNextVariationId(self) -> int:
        id = 1
        if len(self.variations) > 0:
            id = max([x.id for x in self.variations]) + 1
        return id
    
    def getNextModifierId(self) -> int:
        id = 1
        if len(self.modifiers) > 0:
            id = max([x.id for x in self.modifiers]) + 1
        return id
    
    def _applyPatterns(self, item:ItemNode, patterns:List[str], visibility:bool = False) -> bool:
        was_pattern_applied = False
        # If a pattern matches, set the visibility, otherwise leave the node untouched
        for patt in patterns:
            # Apply the inclusions. Set it visible if it matches, leave it untouched otherwise
            patt_type = patt[0:patt.find(':')]
            patt_body = patt[patt.find(':')+1:]
            if patt_type == 'blob' and fnmatch.fnmatch(item.label, patt_body):
                item.visible = visibility
                was_pattern_applied = True
            else:
                # Apply a regex
                m = re.match(patt_body, item.label)
                if m is not None:
                    item.visible = visibility
                    was_pattern_applied = True
        return was_pattern_applied

    def _applyVariationRecursive(self, variation:Variation, nodes:List[ItemNode]):
        layersVisibility = []
        for n in nodes:
            item = ItemNode(n.label, n.visible, n.node_path)
            self._applyPatterns(item, variation.inclusions, True)
            self._applyPatterns(item, variation.exclusions)
            layersVisibility.append(item)
            if len(n.children) > 0:
                item.children = self._applyVariationRecursive(variation, n.children)
        return layersVisibility

    def applyVariation(self, variation:Variation, updateLayers:bool = False, nodes:List[ItemNode] = None) -> List[ItemNode]:
        """
        Apply the inclusion and exclusion patterns of the specified variation and return a 
        node tree representing the final state. Optionally apply the state on the actual layers
        """
        if nodes is None:
            nodes = self.layerHierarchy(True)
        layersVisibility = self._applyVariationRecursive(variation, nodes)
        if updateLayers:
            self.updateLayersVisibility(layersVisibility)
        return layersVisibility
    
    def lookupVariationModifiers(self, variation:Variation) -> List[Modifier]:
        """
        Lookup the modifiers by the IDs specified in the variation
        """
        mods = []
        for k in variation.modifiers:
            mods.extend([x for x in self.modifiers if x.id == k])
        return mods
    
    def _applyModifiersRecursive(self, modifiers:List[Modifier], nodes:List[ItemNode]) -> List[ItemNode]:
        layersVisibility = []
        for n in nodes:
            item = ItemNode(n.label, n.visible, n.node_path)
            for i in range(len(modifiers)):
                self._applyPatterns(item, modifiers[i].inclusions, True)
                self._applyPatterns(item, modifiers[i].exclusions)
            layersVisibility.append(item)
            if len(n.children) > 0:
                item.children = self._applyModifiersRecursive(modifiers, n.children)
        return layersVisibility

    def modifiersToApply(self, modifiers:List[Modifier], bitflags:str) -> List[Modifier]:
        """
        Takes the list of modifiers and returns a filtered copy with the
        modifiers that are enabled by the flags
        """
        flags = int(bitflags, 2)
        mods = []
        for i in range(len(modifiers)):
            weight = len(modifiers) - 1 - i
            fl = 1 << weight
            if (flags & fl) != 0:
                mods.append(modifiers[i])
        return mods

    def applyModifiers(self, modifiers:List[Modifier], bitflags:str, updateLayers:bool = False, nodes:List[ItemNode] = None):
        """
        Apply the corresponding modifiers based on the bitflags string and return a 
        node tree representing the final state. Optionally apply the state on the actual layers
        """
        if nodes is None:
            nodes = self.layerHierarchy()
        layersVisibility = self._applyModifiersRecursive(self.modifiersToApply(modifiers, bitflags), nodes)
        if updateLayers:
            self.updateLayersVisibility(layersVisibility)
        return layersVisibility
