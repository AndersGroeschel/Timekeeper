from datetime import datetime
import os
import sys
import json
from typing import Dict, Callable, Any, Optional

from inputPrompting import *
from jsonManipulation import *
from exactIntegration import *



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
persistentFileDir = os.path.join(scriptPath,"timekeeping/persistent_files")
if not os.path.exists(fileDir):
    os.makedirs(fileDir)

if not os.path.exists(persistentFileDir):
    os.makedirs(persistentFileDir)

filePath = os.path.join(fileDir, f"{today.day}.json")

exactInterface = ExactOnlineInterface()


def getHourStrFromSec(seconds:int) -> str:
    return "{:.2f}".format((seconds/(60*60)))

def save(document):

    persistentFiles = document.get("persistent files")

    if persistentFiles != None:
        for fileName, content in persistentFiles.items():
             with open(os.path.join(persistentFileDir,fileName + ".json"),"w", encoding='utf-8') as persistentFile:
                json.dump(content, persistentFile, ensure_ascii=False, indent=4)
        del document["persistent files"]
    with open(filePath,"w", encoding='utf-8') as scheduleFile:
        json.dump(document, scheduleFile, ensure_ascii=False, indent=4)

    if persistentFiles != None:
        document["persistent files"] = persistentFiles


def loadDocument():
    scheduleDocument = {}
    try: 
        with open(filePath,"r", encoding='utf-8') as scheduleFile:
            scheduleDocument = json.loads(scheduleFile.read())
    except OSError:
        pass

    for fileName in os.listdir(persistentFileDir):
        persistentFilePath = os.path.join(persistentFileDir, fileName)

        try: 
            with open(persistentFilePath, "r", encoding='utf-8') as persistentFile:
                setValue(scheduleDocument,["persistent files",fileName.removesuffix(".json")], json.loads(persistentFile.read()))
        except OSError:
            pass
    return scheduleDocument



def exit(document):
    save(document)
    print("Ok Bye!")
    sys.exit()

def hasUnfinishedActivity(document) -> bool:
    activities = document.get("activities")
    if activities is None or len(activities) == 0:
        return False
    
    for activity in activities:
        if activity.get("end") == None:
            return True
    return False


def endUnfinishedActivity(activity: Optional[dict], time: datetime):
    if activity is None:
        return 
    
    activity["end"] = time
    if promptBoolInput("Just ended last activity with description: " + activity["description"] + "\n\nWould you like to change it? (y/n)"):
        activity["description"] = input("Enter New Description:\n")
            
def getSuggestedTypes(document):
    settings = document.get("persistent files")
    if settings == None:
        return []
    settings = settings.get("settings")
    if settings == None:
        return []
    suggestedTypes = settings.get("suggested activity types")
    if suggestedTypes == None:
        return []
    return suggestedTypes

def updateSuggestedTypes(document, suggestedTypes: list[str], chosenType: str):
    try: 
        suggestedTypes.remove(chosenType)
    except:
        pass
    suggestedTypes.insert(0,chosenType)

    suggestedTypes = suggestedTypes[:10]
    setValue(document,["persistent files","settings","suggested activity types"],suggestedTypes)



def chooseActivityType(document) -> str:

    suggestedTypes = getSuggestedTypes(document)

    if suggestedTypes == None or len(suggestedTypes) == 0:
        newType = promptNonemptyString("what is the type of the activity?: \n").capitalize()
        updateSuggestedTypes(document,suggestedTypes,newType)
        return newType
    
    keys = [*"abcdefghijklmnopqrstuvwxyz"]

    typeChoices = {}
    for index, suggestedType in enumerate(suggestedTypes[:len(keys)]):
        typeChoices[keys[index]] = suggestedType

    choice = promptChoiceList("choose an option", [typeChoices, {"new":"Create a new type"}])

    if choice in typeChoices.keys():
        updateSuggestedTypes(document,suggestedTypes,typeChoices[choice])
        return typeChoices[choice]
    
    if choice == "new":
        newType = promptNonemptyString("what is the type of the new activity?: \n").capitalize()
        updateSuggestedTypes(document,suggestedTypes,newType)
        return newType
    
    return ""

def getCurrentUnfinishedActivity(document, maxPriority:int = 0) -> Optional[dict]:
    activities = document.get("activities")
    if activities is None:
        return None
    
    if len(activities) > 0:
        i = 0
        while(i < len(activities)):
            curr = activities[-(i+1)]
            if curr.get("end") == None and curr["priority"] <= maxPriority:
                return curr
            
            i += 1

        return None


def endActivity(document):
    endTime = promptTime()

    lastActivity= getCurrentUnfinishedActivity(document)

    endUnfinishedActivity(lastActivity, endTime)

def startActivity(document):
    activities = document.get("activities")
    if activities is None:
        activities = []

    startTime = promptTime()

    lastActivity = getCurrentUnfinishedActivity(document)
    endUnfinishedActivity(lastActivity,startTime)

    activityType = chooseActivityType(document) 
    activityDescription = input("description: ")

    activities.append({
        "start": startTime,
        "type": activityType,
        "priority": 0 if lastActivity == None else lastActivity["priority"], # manually entered take it as ground truth
        "description": activityDescription
    })
    
    document["activities"] = activities


def interruptActivity(document):
    lastActivity = getCurrentUnfinishedActivity(document)
    if lastActivity == None:
        return

    startTime = promptTime()
    activityType = chooseActivityType(document) 
    activityDescription = input("description: ")

    document["activities"].append({
        "start": startTime,
        "type": activityType,
        "priority": lastActivity["priority"] - 1, # decrease priority number so it is considered more important
        "description": activityDescription
    })


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

    workTimes.append({"log on" : promptTime(), "sent": False})

    document["work times"] = workTimes

def logOff(document):
    workTimes = document.get("work times")
    last = workTimes[-1]

    time = promptTime()

    last["log off"] = time

    if getValue(document,["persistent files","settings","generate report on log off"], False):
        generateReport(document)



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

    def __init__(self, logOn, logOff, sent):
        self.logOn: datetime = logOn
        self.logOff: datetime = logOff

        self.sent = sent or False

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

        self.timeSlices.sort(key= lambda slice: slice[0])


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
        sent = workTime.get("sent") or False

        if startWork == None or endWork == None:
            continue

        workPeriod = WorkPeriod(startWork, endWork, sent)
        for activity in activityList:
            workPeriod.addActivityIfInPeriod(activity)
        workPeriods.append(workPeriod)

    for workPeriod in workPeriods:
        workPeriod.updateTimeSlices()

    if not getValue(document,["persistent files", "exactOnline", "send report after generated"],False):
        periodStrings = []
        for workPeriod in workPeriods:
            periodStrings.append(workPeriod.reportString())

        print("\n" + ("\n\n".join(periodStrings)) + "\n")
        return 
    
    timeSlicesToSend = []
    workTimesToUpdate = []
    for (index,workPeriod) in [(index,period) for (index,period) in enumerate(workPeriods) if not period.sent]:
        print("\n"+workPeriod.reportString() + "\n")
        if promptBoolInput("send report to Exact Online? (y/n)"):
            timeSlicesToSend += workPeriod.timeSlices
            workTimesToUpdate.append(index)
            

    if len(timeSlicesToSend) > 0:
        if exactInterface.enterTimes(document, timeSlicesToSend):
            for i in workTimesToUpdate:
                setValue(document,["work times",i,"sent"], True)
        

def hasFile(document: Json, fileName: str) -> bool:
    files = document.get("persistent files")

    if files == None:
        return False
    
    return files.get(fileName) != None

# set up choice objects
exitChoice = ChoiceObject("exit", exit, lambda doc: True, "x")
logOnChoice = ChoiceObject("Log On", logOn, isLoggedOff, "log")
logOffChoice = ChoiceObject("Log Off", logOff, lambda doc: (not isLoggedOff(doc)), "log")
editChoice = ChoiceObject("edit", editJsonDoc, lambda doc: True, "e")
generateReportChoice = ChoiceObject("Generate Report",generateReport, isLoggedOff, "gen")

startActivityChoice = ChoiceObject("start activity", startActivity, lambda doc: (not isLoggedOff(doc)))
endActivityChoice = ChoiceObject("end last activity", endActivity, lambda doc: (not isLoggedOff(doc) and hasUnfinishedActivity(doc)))
interruptActivityChoice = ChoiceObject("interrupt activity", interruptActivity, lambda doc: (not isLoggedOff(doc) and hasUnfinishedActivity(doc)))

addExactOnlineChoice = ChoiceObject("add exact online integration", addExactIntegration, lambda doc: not hasFile(doc, "exactOnline"))

document = loadDocument()


if isLoggedOff(document):
    if promptBoolInput("You aren't logged in. Would you like to log in? (y/n)"):
        logOnChoice.action(document)


def header(document):
    unfinishedActivity = getCurrentUnfinishedActivity(document)

    string = "\n"
    string += "="*50 + "\n"
    if unfinishedActivity != None:
        string += "Working on activity with\n"
        string += "       type: " + unfinishedActivity["type"] + "\n"
        string += "description: " + unfinishedActivity["description"] + "\n"
    return string

doChoiceInteraction(
    document,
    [exitChoice, logOnChoice, logOffChoice, editChoice, generateReportChoice, startActivityChoice, endActivityChoice, interruptActivityChoice, addExactOnlineChoice],
    header
)

