import re
import sys
import os
import math
from typing import List

from models import Modifier, ModifierCombination, Variation

def combinationName(mods:List[Modifier], variationName:str, bitflags:str) -> str:
    flags = int(bitflags, 2)
    name = variationName
    for i in range(len(mods)):
        weight = len(mods) - 1 - i
        fl = 1 << weight
        if (flags & fl) != 0:
            name += mods[i].name
    if len(name) == 0:
        name = '<Empty>'
    return name

def defaultCombinations(variation:Variation, mods:List[Modifier]) -> List[ModifierCombination]:
    combs:List[ModifierCombination] = []
    if len(mods) > 0:
        formatPatt = "{0:0" + str(len(mods)) + "b}"
        combs = [ModifierCombination.from_dict({'name': combinationName(mods, variation.name, formatPatt.format(x)), 'bitflags': formatPatt.format(x)}) for x in range(int(math.pow(2, len(mods))))]
    return combs

def getSuffixFor(variation:Variation, mods:List[Modifier]) -> str:
    suffix = variation.suffix
    if len(mods) > 0:
        for m in mods:
            suffix += m.suffix
    return suffix

def getUniqueFilename(destFolder:str, baseFileName:str, ext:str) -> str:
    fname = os.path.join(destFolder, baseFileName + ext)
    i = 1
    while os.path.exists(fname):
        print('WARN: File name clash detected on '+ fname)
        fname = os.path.join(destFolder, baseFileName + str(i) + ext)
        i += 1
    return fname

def isValidRegex(s:str) -> bool:
    valid = True
    try:
        re.compile(s)
    except re.error:
        valid = False
    return valid

def getBasedir() -> str:
    """
    Returns the base directory. Checks for PyInstaller Runtime information to 
    check if we are running in a bundle and return the approriate path
    """
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # _MEIPASS will be the folder to the "bin" folder, 
        # we want one directory up, where the shim executable is located
        return os.path.dirname(sys._MEIPASS)
    else:
        return os.path.dirname(os.path.dirname(__file__))

def getResourcesPath() -> str:
    """
    Returns the path to the resources. Checks for PyInstaller runtime information to
    check if we are running in a bundle and return the approriate path
    """
    return os.path.join(getBasedir(), 'res')

def findIndex(l:List, val) -> int:
    idx = -1
    try:
        idx = l.index(val)
    except ValueError:
        pass
    return idx