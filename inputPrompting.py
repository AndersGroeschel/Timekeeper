from datetime import datetime
from typing import Dict, Callable, Any, Optional, Union

class ChoiceObject:

    def __init__(self, description: str, action: Callable[[Any],None], choiceAvailable: Callable[[Any],bool], preferredKey: Optional[str] = None):
        self.description = description
        self.action = action 
        self.preferredKey = preferredKey
        self.choiceAvailable = choiceAvailable

def doChoiceInteraction(item: Any, choices: list[ChoiceObject], headerString: Optional[Callable[[Any],str]] = None):
    availableChoices = choices

    while len(availableChoices) > 0:

        print(headerString(item))
        availableChoices = [choice for choice in choices if choice.choiceAvailable(item)]

        promptChoiceDynamic("What would you like to do?", availableChoices, item)






def formatStrList(items: list[str], conjunction:str = "and") -> str:
    if len(items) == 0:
        return ""
    elif len(items) == 1:
        return f"{items[0]}"
    elif len(items) == 2:
        return f"{items[0]} {conjunction} {items[1]}"
    else:
        prev = " ".join([f"{elem}," for elem in items[:-1]])
        return f"{prev} {conjunction} {items[-1]}"



def promptInput(msg: str, acceptedAnswers: list[str]) -> str:

    acceptedAnswers = [string.lower().strip() for string in acceptedAnswers]
    msg = msg + "\n"

    ans = input(msg).lower().strip()
    while not (ans in acceptedAnswers):
        print("Please Choose: " + formatStrList(acceptedAnswers, "or") + "\n")
        ans = input(msg).lower().strip()
    return ans

def promptChoiceList(msg: str, choices: Union[dict[str,str],list[dict[str,str]]]) -> str:
    msg += "\n"

    choiceList = []
    keys = []

    if choices is dict:
        for key, description in choices.items():
            key = key.lower().strip()
            keys.append(key)
            choiceList.append(f"  - {key.lower().strip()}: {description}")

        msg += "\n".join(choiceList)
    else:
        for choiceBlock in choices:
            if len(choiceBlock) == 0:
                continue
            
            blockChoices = []
            for key, description in choiceBlock.items():
                key = key.lower().strip()
                keys.append(key)
                blockChoices.append(f"  - {key.lower().strip()}: {description}")
            choiceList.append("\n".join(blockChoices))
        msg += "\n\n".join(choiceList)

    msg += "\n"

    ans = input(msg).lower().strip()
    while not (ans in keys):
        print("Please Choose: " + formatStrList(keys, "or") + "\n")
        ans = input(msg).lower().strip()
    return ans







def promptChoiceDynamic(msg: str, choices: list[ChoiceObject], document) -> None:

    choiceOptions = [*"abcdefghijklmnopqrstuvwxyz"]
    choiceOptions.reverse()

    allKeys = []

    autoCreatedKeyMsg = []
    otherKeyMsg = []    

    choiceMap = {}

    for choice in choices:
        
        key = choice.preferredKey

        isAutoCreated = False

        while (key is None) or (key.strip().lower() in allKeys):
            key = choiceOptions.pop()
            isAutoCreated = True

        if isAutoCreated:
            autoCreatedKeyMsg.append(
                f"  - {key}: {choice.description}"
            )
        else:
            otherKeyMsg.append(
                f"  - {key}: {choice.description}"
            )

        key = key.strip().lower()
        choiceMap[key] = choice
        allKeys.append(key)
        
    msg = "\n" + msg + "\n\n"

    if len(autoCreatedKeyMsg) > 0:
        msg = msg + "\n".join(autoCreatedKeyMsg) + "\n\n"

    if len(otherKeyMsg) > 0:
        msg = msg + "\n".join(otherKeyMsg)

    userChoice = choiceMap[promptInput(msg,allKeys)]
    userChoice.action(document)


def promptManualTime(msg: str = "enter a time: "):
    now = datetime.now()
    ans = input(msg)
    while True:
        try:
            time = datetime.strptime(ans, "%H:%M")
            return str(datetime(now.year, now.month, now.day, time.hour, time.minute))
        except:
            ans = input(msg)
  
def promptTime() -> str:
    now = datetime.now()
    if promptBoolInput("Use current time? (y/n)"):
        return str(datetime(now.year, now.month, now.day, now.hour, now.minute))

    return promptManualTime()

def promptBoolInput(msg: str = "(y/n): ") -> bool:
    positiveAns = ["y", "yes", "t", "true"]
    negativeAns = ["n", "no", "f", "false"]

    ans = promptInput(msg, positiveAns + negativeAns)

    if ans in positiveAns:
        return True

    if ans in negativeAns:
        return False
    
def promptIntInput(msg: str = "enter an integer: ") -> int:
    
    num = input(msg)
    while True:
        try:
            num = int(num)
            return num
        except:
            num = input(msg)

def promptNonemptyString(msg: str = "enter a value: ") -> str:

    string = input(msg).strip()

    while string == "":
        string = input(msg).strip()
    
    return string



