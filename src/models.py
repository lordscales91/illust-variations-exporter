from typing import List, Dict

from psd_tools import PSDImage
from PIL.Image import Image

class ItemNode:
    def __init__(self, label:str='', visible:bool=False, node_path:str = None):
        self.label:str = label
        self.visible:bool = visible
        self.children:List['ItemNode'] = []
        self.node_path = node_path

    def addChild(self, child: 'ItemNode'):
        self.children.append(child)

class AppState:
    def __init__(self, psd:PSDImage=None, thumbnail:Image=None):
        self.psd:PSDImage = psd
        self.thumbnail:Image = thumbnail
    def __repr__(self) -> str:
        return '<AppState psd="{0}", thumbnail="{1}">'.format(repr(self.psd), repr(self.thumbnail))

class VariationMixin:
    def __init__(self):
        self.id:int = 0
        self.name:str = ''
        self.suffix:str = ''
        self.inclusions:List[str] = []
        self.exclusions:List[str] = []

    def load_dict(self, d:Dict):
        self.id = d.get('id', 0)
        self.name = d.get('name', '')
        self.suffix = d.get('suffix', '')
        self.inclusions = d.get('inclusions', [])
        self.exclusions = d.get('exclusions', [])
    
    def to_dict(self) -> Dict:
        return {"id": self.id, "name": self.name, "suffix": self.suffix,
                "inclusions": self.inclusions, "exclusions": self.exclusions}

class Modifier(VariationMixin):

    @classmethod
    def from_dict(cls, d:Dict) -> 'Modifier':
        inst = Modifier()
        inst.load_dict(d)
        return inst

class ModifierCombination:
    def __init__(self) -> None:
        self.name:str = ''
        self.bitflags:str = ''

    def load_dict(self, d:Dict):
        self.name = d.get('name', '')
        self.bitflags = d.get('bitflags', '')

    @classmethod
    def from_dict(cls, d:Dict) -> 'ModifierCombination':
        inst = ModifierCombination()
        inst.load_dict(d)
        return inst
    
    def to_dict(self) -> Dict:
        return {"name": self.name, "bitflags": self.bitflags}

class Variation(VariationMixin):
    def __init__(self):
        super().__init__()
        self.subfolder:str = ''
        self.modifiers:List[int] = [] # List of modifier IDs
        self.combinations:List[ModifierCombination] = []

    def load_dict(self, d:Dict):
        super().load_dict(d)
        self.subfolder = d.get('subfolder', '')
        self.modifiers = d.get('modifiers', [])
        self.combinations = [ModifierCombination.from_dict(x) for x in d.get('combinations', [])]
    
    def to_dict(self) -> Dict:
        d = super().to_dict()
        d['subfolder'] = self.subfolder
        d['modifiers'] = self.modifiers
        d['combinations'] = [x.to_dict() for x in self.combinations]
        return d
    
    @classmethod
    def from_dict(cls, d:Dict) -> 'Variation':
        inst = Variation()
        inst.load_dict(d)
        return inst