from datetime import datetime
import os
import sys
import json
from typing import Dict, Callable, Any, Optional

from inputPrompting import *


def copyJsonWithParsedTypes(document):

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


def applyKeys(keys:list, document):
    value = document
    for key in keys:
        value = value[key]
    return value

def setValue(keys: list, document, newVal):
    value = document
    for key in keys[:-1]: # traverse document until last key
        value = value[key]
    
    value[keys[-1]] = newVal # set new value at last entry

def editJsonDoc(document):

    placeholderKeys = [*"abcdfghijkmnopqrstuvwxyz"]
    
    baseChoices = {
        ".." : "back",
        "/" : "start",
        "l" : "leave"
    }
    keyList = []

    while True:
        print("")
        curr = applyKeys(keyList, document)

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

            setValue(keyList,document,newVal)

        elif type(curr) is dict:
            keyList.append(navChoices[choice])
        elif type(curr) is list:
            keyList.append(int(choice))
        else:
            print(curr)



def getTableString(rows: list, columnLabels: list[str], formatter: Callable[[Any],list[str]]) -> str:

    maxColEntryLen = []
    

    for column in columnLabels:
        maxColEntryLen.append(len(column))


    formattedRows: list[str] = []
    for row in rows:
        formattedRow = formatter(row)
        formattedRows.append(formattedRow)
        for index, entry in enumerate(formattedRow):
            if(len(entry) > maxColEntryLen[index]):
                maxColEntryLen[index] = len(entry)

    maxColEntryLen = [i + 1 for i in maxColEntryLen]


    rowStrings = []
    colStr = ""
    for index, column in enumerate(columnLabels):
        colStr += "| " + column.capitalize().ljust(maxColEntryLen[index]," ")
    rowStrings = [colStr + "|" , "|" + "|".join([ "-"*(i + 1) for i in maxColEntryLen]) + "|" ]

    for row in formattedRows:
        rowStr = ""
        for index, entry in enumerate(row):
            rowStr += "| " + entry.ljust(maxColEntryLen[index]," ")

        rowStrings.append(rowStr +"|")

    return "\n".join(rowStrings)

    
        







today = datetime.today()

scriptPath = os.path.dirname(__file__)

fileDir = os.path.join(scriptPath, f"timekeeping/{today.year}/{today.month}")
if not os.path.exists(fileDir):
    os.makedirs(fileDir)

filePath = os.path.join(fileDir, f"{today.day}.json")


def getHourStrFromSec(seconds:int) -> str:
    return "{:.2f}".format((seconds/(60*60)))

def save(document):

    with open(filePath,"w", encoding='utf-8') as scheduleFile:
        json.dump(document, scheduleFile, ensure_ascii=False, indent=4)

def exit(document):
    save(document)
    print("Ok Bye!")
    sys.exit()

def hasUnfinishedActivity(document):
    activities = document.get("activities")
    if activities is None:
        return False
    
    if len(activities) > 0:
        last = activities[-1]
        return last.get("end") == None
    
    return False


def endLastActivity(activities: list, time: datetime):
    if len(activities) > 0:
        last = activities[-1]
        if last.get("end") == None:
            last["end"] = time

            if promptBoolInput("Just ended last activity with description: " + last["description"] + "\n\nWould you like to change it? (y/n)"):
                last["description"] = input("Enter New Description:\n")


def chooseActivityType(document) -> str:
    suggestedTypes:list = document.get("suggested activity types")

    if suggestedTypes == None or len(suggestedTypes) == 0:
        newType = promptNonemptyString("what is the type of the new activity?: \n").capitalize()
        document["suggested activity types"] = [newType]
        return newType
    
    keys = [*"abcdefghijklmnopqrstuvwxyz"]

    typeChoices = {}
    for index, suggestedType in enumerate(suggestedTypes[:len(keys)]):
        typeChoices[keys[index]] = suggestedType

    choice = promptChoiceList("choose an option", [typeChoices, {"new":"Create a new type"}])

    if choice in typeChoices.keys():
        return typeChoices[choice]
    
    if choice == "new":
        newType = promptNonemptyString("what is the type of the new activity?: \n").capitalize()
        suggestedTypes.append(newType)
        document["suggested activity types"] = suggestedTypes

        return newType
    
    return ""




def endActivity(document):
    activities = document.get("activities")
    if activities is None:
        activities = []

    endTime = promptTime()

    endLastActivity(activities, endTime)

def startActivity(document):
    activities = document.get("activities")
    if activities is None:
        activities = []

    startTime = promptTime()
    endLastActivity(activities,startTime)

    activityType = chooseActivityType(document) 
    activityDescription = input("description: ")

    activities.append({
        "start": startTime,
        "type": activityType,
        "priority": 0, # manually entered take it as ground truth
        "description": activityDescription
    })
    
    document["activities"] = activities


def isLoggedOff(document):
    workTimes = document.get("work times")
    if workTimes == None or len(workTimes) == 0:
        return True
    
    last = workTimes[-1]

    return last.get("log off") != None

def logOn(document):

    workTimes = document.get("work times")
    if workTimes == None:
        workTimes = []

    workTimes.append({"log on" : promptTime()})

    document["work times"] = workTimes

def logOff(document):
    workTimes = document.get("work times")
    last = workTimes[-1]

    time = promptTime()

    last["log off"] = time



def timesIntersect(s1: datetime, e1:datetime, s2:datetime, e2: Optional[datetime] = None):
    if s1 < s2:
        return s2 < e1
    elif e2 == None:
        return True # if there is no end time for the second time it is assumed to be infinite
    else:
        return s1 < e2
    

def timeSliceEntries(timeSlice:tuple[datetime,datetime,str,str]):
    start,end,sliceType,description = timeSlice

    totalTimeHours = getHourStrFromSec((end - start).seconds)

    return [
        str(start),
        str(end),
        totalTimeHours,
        sliceType,
        description
    ]



class WorkPeriod:

    def __init__(self, logOn, logOff):
        self.logOn: datetime = logOn
        self.logOff: datetime = logOff

        self.activities: list[dict[str,Any]] = []

        self.timeSlices: list[tuple[datetime,datetime,str,str]] = []

    def addActivityIfInPeriod(self,activity):
        activityStart = activity.get("start")
        activityEnd = activity.get("end")

        if timesIntersect(self.logOn, self.logOff, activityStart, activityEnd):
            self.activities.append(activity)

    def updateTimeSlices(self):
         # sort by priority, then by start time
        self.activities.sort(key = lambda a: a["start"])
        self.activities.sort(key = lambda a: a["priority"])

        timeSlices = []

        for activity in self.activities:

            start = activity["start"]
            end = activity.get("end")

            activityType = activity["type"]
            activityDescription = activity["description"]

            if start < self.logOn:
                start = self.logOn

            if end == None or end > self.logOff:
                end = self.logOff

            intersectingSlices = [(sliceStart, sliceEnd) 
                                  for (sliceStart, sliceEnd, _, _) in timeSlices
                                  if timesIntersect(sliceStart, sliceEnd, start, end) 
                                ]
            
            intersectingSlices.sort(key= lambda slice: slice[0]) #sort slices by start time

            activitySlices = [(start,end,activityType,activityDescription)]

            for (sliceStart,sliceEnd) in intersectingSlices:

                (activityStart, activityEnd, _, _) = activitySlices.pop()

                if activityStart < sliceStart:
                    activitySlices.append((activityStart,sliceStart,activityType,activityDescription))

                if sliceEnd < activityEnd :
                    activitySlices.append((sliceEnd, activityEnd,activityType,activityDescription))
                else:
                    break

            timeSlices += activitySlices

        self.timeSlices = timeSlices




    def getUndocumentedTimeSec(self) -> int:
        totalTimeSec = (self.logOff - self.logOn).seconds
        documentedTimeSec = 0
        for timeSlice in self.timeSlices:
            (start,end, _, _) = timeSlice
            documentedTimeSec += (end - start).seconds

        return totalTimeSec - documentedTimeSec

    def reportString(self) -> str:
        string = f"Work Period: {self.logOn} - {self.logOff}\n"

        undocumentedTimeHours = getHourStrFromSec(self.getUndocumentedTimeSec())

        string += f"Undocumented Hours: {undocumentedTimeHours}\n\n"

        string += getTableString(self.timeSlices, ["start", "end", "total hours", "type", "description"], timeSliceEntries)
        return string



def generateReport(document):

    doc = copyJsonWithParsedTypes(document)

    workTimes = doc["work times"]

    activityList = doc["activities"]

    workPeriods: list[WorkPeriod] = []

    for workTime in workTimes:
        startWork = workTime.get("log on")
        endWork = workTime.get("log off")

        if startWork == None or endWork == None:
            continue

        workPeriod = WorkPeriod(startWork, endWork)
        for activity in activityList:
            workPeriod.addActivityIfInPeriod(activity)
        workPeriods.append(workPeriod)

    for workPeriod in workPeriods:
        workPeriod.updateTimeSlices()

    periodStrings = []
    for workPeriod in workPeriods:
        periodStrings.append(workPeriod.reportString())

    print("\n" + ("\n\n".join(periodStrings)) + "\n")
        

        



# set up choice objects
exitChoice = ChoiceObject("exit", exit, "x")
logOnChoice = ChoiceObject("Log On", logOn, "log")
logOffChoice = ChoiceObject("Log Off", logOff, "log")
editChoice = ChoiceObject("edit", editJsonDoc, "e")
generateReportChoice = ChoiceObject("Generate Report",generateReport, "gen")

startActivityChoice = ChoiceObject("start activity", startActivity)
endActivityChoice = ChoiceObject("end last activity", endActivity)

# define choice flow
def getNextChoices(document):

    choices = [
        exitChoice,
        editChoice
    ]

    loggedOn = not isLoggedOff(document)

    unfinishedActivity = hasUnfinishedActivity(document)

    if loggedOn:
        choices.append(logOffChoice)
    
    if not loggedOn:
        choices.append(logOnChoice)


    if loggedOn:
        choices.append(startActivityChoice)

    if loggedOn and unfinishedActivity:
        choices.append(endActivityChoice)

    if not loggedOn:
        choices.append(generateReportChoice)

    return choices








scheduleDocument = None
try: 
    with open(filePath,"r", encoding='utf-8') as scheduleFile:
        scheduleDocument = json.loads(scheduleFile.read())
except OSError:
    scheduleDocument = {}

if isLoggedOff(scheduleDocument):
    if promptBoolInput("You aren't logged in. Would you like to log in? (y/n)"):
        logOnChoice.action(scheduleDocument)

choices = getNextChoices(scheduleDocument)



while len(choices) > 0:

    promptChoiceDynamic("What would you like to do?", choices, scheduleDocument)

    choices = getNextChoices(scheduleDocument)

