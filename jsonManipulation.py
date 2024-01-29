from datetime import datetime
from typing import Dict, Callable, Any, Optional

from inputPrompting import *

 
Json = Union[dict[str,'Json'], list['Json'], bool,int,float,str,None]

JsonExtended = Union[dict[str,'JsonExtended'], list['JsonExtended'], bool,int,float,str,datetime,None]

def copyJsonWithParsedTypes(document: Json) -> JsonExtended:

    if type(document) is dict:
        doc = {}
        for key in document.keys():
            doc[key] = copyJsonWithParsedTypes(document[key])
        return doc
    
    if type(document) is list:
        doc = []
        for item in document:
            doc.append(copyJsonWithParsedTypes(item))
        return doc
    
    if type(document) is str:

        # try to parse date time
        try:
            doc = datetime.strptime(document, "%Y-%m-%d %H:%M:%S")
            return doc
        except:
            return document
        
    return document


def getValue(document: Json, keys: list[Union[str,int]], default: Json = None):
    value = document
    for key in keys:
        value = value.get(key)
        if value is None: 
            return default
    return value

def setValue(document:Json, keys: list[Union[str,int]], newVal):
    if len(keys) == 1:
        document[keys[0]] = newVal
        return document
    
    value = document.get(keys[0])
    if value == None:
        if type(keys[1]) is str:
            value = {}
        elif type(keys[1]) is int:
            value = []

    document[keys[0]] = setValue(value, keys[1:], newVal)

    return document


def editJsonDoc(document:Json):

    placeholderKeys = [*"abcdfghijkmnopqrstuvwxyz"]
    
    baseChoices = {
        ".." : "back",
        "/" : "start",
        "l" : "leave"
    }
    keyList = []

    while True:
        print("")
        curr = getValue(document, keyList)

        if len(keyList) > 0:
            actionChoices = baseChoices.copy()
        else:
            actionChoices = {"l" : "leave"}

        navChoices = {}
        if type(curr) is dict:
            for index, key in enumerate(curr.keys()):
                navChoices[placeholderKeys[index]] = key

        elif type(curr) is list:
            for index, item in enumerate(curr):
                stringified = str(item)
                if(len(stringified) > 32):
                    stringified = stringified[:29] + "..."
                navChoices[f"{index}"] = stringified

        else:
            actionChoices["e"] = f"edit {keyList[-1]}, current value: {curr}"

        choice = promptChoiceList("choose an option", [actionChoices, navChoices])

        if choice == "..":
            keyList.pop()
        elif choice == "/":
            keyList = []
        elif choice == "l": # l for leave
            return
        elif choice == "e": # e for edit
            newVal = None
            if type(curr) is int:
                newVal = promptIntInput()
            elif type(curr) is str:
                try:
                    datetime.strptime(curr, "%Y-%m-%d %H:%M:%S")
                    newVal = promptManualTime()
                except:
                    newVal = input("enter a value: ")
            elif type(curr) is bool:
                newVal = promptBoolInput()

            setValue(document,keyList,newVal)

        elif type(curr) is dict:
            keyList.append(navChoices[choice])
        elif type(curr) is list:
            keyList.append(int(choice))
        else:
            print(curr)
