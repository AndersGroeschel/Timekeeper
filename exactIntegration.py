from inputPrompting import *
from jsonManipulation import *

from typing import Dict, Callable, Any, Optional

from selenium import webdriver
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from selenium.webdriver.common.keys import Keys



def addExactIntegration(document: Json):
    setExactUsername(document)
    setExactPassword(document)
    setExactUrl(document)
    setAutoSendAfterGenerate(document)
    setAutoSubmit(document)

def setAutoSendAfterGenerate(document):
    setValue(document,["persistent files", "exactOnline", "send report after generated"], promptBoolInput( "send report after generated? (y/n) \n"))

def setAutoSubmit(document):
    setValue(document,["persistent files", "exactOnline", "auto submit"], promptBoolInput( "automatically submit time sheet after entry? (y/n) \n"))

def setExactUrl(document:Json):
    url = promptNonemptyString("Exact Url: ")

    if url[-1] == "/":
        url = url[:-1]

    setValue(document,["persistent files", "exactOnline", "base url"], url)

def setExactUsername(document:Json):
    username = promptNonemptyString("Exact Username: ")
    setValue(document,["persistent files", "exactOnline", "username"], username)

def setExactPassword(document:Json):
    password = promptNonemptyString("Exact Password: ")
    setValue(document,["persistent files", "exactOnline", "password"], password)

def waitForElement(driver: WebDriver, by: str, value) -> Optional[WebElement]:
    try:
        element = WebDriverWait(driver, 10).until(
            lambda x: x.find_element(by,value)
        )
        return element
    except:
        return None
    
def waitForElementVisibility(driver: WebDriver, by: str, value: str) -> Optional[WebElement]:
    try:
        element = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((by, value))
        )
        return element
    except:
        return None
    

def setElementValue(driver:WebDriver,elemId:str, value: str):
    driver.execute_script(f"""
        document.getElementById('{elemId}').setAttribute('value', '{value}')
    """)

def scrollIntoView(driver:WebDriver, elemId:str):
    driver.execute_script(f"""
        document.getElementById('{elemId}').scrollIntoView()
    """)




class ExactOnlineInterface:

    def __init__(self):
        self.driver: Optional[WebDriver] = None

    def getDriver(self) ->  WebDriver:
        if self.driver != None:
            return self.driver
        
        self.driver = webdriver.Chrome()
        return self.driver


    def exactOnlineLogIn(self,document: Json):
        driver = self.getDriver()
        driver.get(getValue(document,["persistent files", "exactOnline", "base url"]))

        loginForm = waitForElementVisibility(driver,By.TAG_NAME,"form")
        if(loginForm == None):
            print("Failed to log in to Exact Online")
            return
            

        userNameInput = loginForm.find_element(By.ID,"LoginForm$UserName")
        userNameInput.send_keys(getValue(document,["persistent files", "exactOnline", "username"]))
        loginForm.submit()

        loginForm = waitForElementVisibility(driver,By.ID,"localAccountForm")
        if(loginForm == None):
            print("Failed to log in to Exact Online")
            return
        
        userNameInput = loginForm.find_element(By.ID,"signInName")
        passwordInput = loginForm.find_element(By.ID,"password")
        submitButton = loginForm.find_element(By.ID,"next")

        userNameInput.clear()
        passwordInput.clear()

        userNameInput.send_keys(getValue(document,["persistent files", "exactOnline", "username"]))
        passwordInput.send_keys(getValue(document,["persistent files", "exactOnline", "password"]))
        
        submitButton.click()


    def logInIfNeeded(self,document: Json):
        driver = self.getDriver()
        baseUrl = getValue(document,["persistent files", "exactOnline", "base url"])
        if driver.current_url == baseUrl or driver.current_url.startswith(baseUrl + "/?"):
            self.exactOnlineLogIn(document)

    def exactOnlineNavigateToPage(self,document: Json, relativeUrl: str, elementSelector: tuple[str,str]) -> Optional[WebElement]:
        driver = self.getDriver()
        baseUrl = getValue(document,["persistent files", "exactOnline", "base url"])
        url = baseUrl + relativeUrl

        driver.get(url)

        self.logInIfNeeded(document)

        if driver == None:
            print("Failed to Navigate to Page due to driver not being prepared")
            return
        
        (by,value) = elementSelector

        return waitForElementVisibility(driver,by,value)


    def enterExactOnlineType(self,document: Json, type:str, rowId: str, returnFrame: WebElement):
        driver = self.getDriver()
        exactOnlineType = getValue(document,["persistent files", "exactOnline", "type mapping", type], {})

        def selectFromContextMenu(storageKey:str, elemId:str,prompt:str):

            guidValue = exactOnlineType.get(storageKey + " internal id")

            if guidValue != None:
                setElementValue(driver,elemId,guidValue)
                setElementValue(driver,elemId+ "_alt",exactOnlineType[storageKey])
                return

            if exactOnlineType.get(storageKey) == None:
                exactOnlineType[storageKey] = "".join([string.capitalize() for string in (input(prompt).split(" "))])

            value = exactOnlineType[storageKey]

            if value != "":
                inputElem = waitForElementVisibility(driver,By.ID,elemId + "_alt")
                inputElem.clear()
                inputElem.send_keys(value)
                projectPopup = waitForElementVisibility(driver,By.ID,f"cntPopupSearch")
                popupItems = projectPopup.find_elements(By.CLASS_NAME,"ContextMenuItems")
                if len(popupItems) == 1:
                    popupItems[0].click()
                elif len(popupItems) > 1:
                    # TODO display list of items as choices (for now take first)
                    popupItems[0].click()

            hiddenInput = driver.find_element(By.ID, elemId)
            exactOnlineType[storageKey + " internal id"] = hiddenInput.get_attribute("value")

            inputElem = waitForElementVisibility(driver,By.ID,elemId + "_alt")
            exactOnlineType[storageKey] = inputElem.get_attribute("value")

        def getNextFormattedNodes(currNode: WebElement) -> list[tuple[str,bool,WebElement]]:

            id = "r" + currNode.get_attribute("id").lstrip("_")
            currentChildren = driver.find_element(By.ID,id)
            if not currentChildren.is_displayed():
                scrollIntoView(driver,currNode.get_attribute("id"))
                currNode.find_element(By.TAG_NAME,"button").click()
            
            tableNode = waitForElementVisibility(driver,By.CSS_SELECTOR,f"#{id} table.TreeView")
            nextNodes = tableNode.find_elements(By.XPATH, "./tbody/*")

            nodeIdToNode: dict[str,WebElement] = {}
            nodeIdToIsLeaf: dict[str,bool] = {}
            nodeIdToText: dict[str,str] = {}

            for node in nextNodes:
                id = node.get_attribute("id")
                if id.startswith("_"):
                    nodeIdToNode[id] = node
                    nodeIdToText[id] = node.find_element(By.TAG_NAME,"a").text
                    if nodeIdToIsLeaf.get(id) == None:
                        nodeIdToIsLeaf[id] = True
                elif id.startswith("r"):
                    optionNodeId = "_" + id[1:]
                    nodeIdToIsLeaf[optionNodeId] = False

            lst = []
            for k,v in nodeIdToNode.items():
                lst.append((nodeIdToText[k],nodeIdToIsLeaf[k],v))

            return lst

            
        # set Account
        selectFromContextMenu("account", f"{rowId}_Account",f"enter account number for {type}: ")

        # set project
        selectFromContextMenu("project", f"{rowId}_Project",f"enter a project name for {type}: ")
        setElementValue(driver,f"{rowId}_ProjectId",exactOnlineType["project internal id"])

        if exactOnlineType.get("activity internal id") == None:


            waitForElementVisibility(driver,By.ID,f"p{rowId}_ProjectWBS").click()
            driver.switch_to.default_content()

            dialogElement = waitForElementVisibility(driver,By.CSS_SELECTOR,"div.ui-dialog[role='dialog']")
            describedBy = dialogElement.get_attribute("aria-describedby")

            activityTreeFrame = waitForElementVisibility(driver,By.CSS_SELECTOR,f"#{describedBy} iframe")
            driver.switch_to.frame(activityTreeFrame)

            # Tree is structured as such: 
            #   #_TreeList_Tree
            #       #_0 (hidden true root)
            #       #r0 (expandable content of root)
            #           ...
            #
            # To avoid clicking on an element that is not visible start search for #_1

            activityTree = waitForElementVisibility(driver,By.ID,"_0")

            selectedTypeWebElement = promptTreeSearch(activityTree, getNextFormattedNodes)
            scrollIntoView(driver,selectedTypeWebElement.get_attribute("id"))

            selectedTypeWebElement.find_element(By.TAG_NAME,"a").click()


            driver.switch_to.default_content()
            driver.switch_to.frame(returnFrame)
            
            
            activityHiddenInput = driver.find_element(By.ID,f"{rowId}_ProjectWBS")
            exactOnlineType["activity internal id"] = activityHiddenInput.get_attribute("value")
            setElementValue(driver,f"{rowId}_ProjectWBSExists","-1")

        else:
            guidValue = exactOnlineType["activity internal id"]
            setElementValue(driver,f"{rowId}_ProjectWBS",guidValue)
            setElementValue(driver,f"{rowId}_ProjectWBSExists","-1")
            

        selectFromContextMenu("hour type", f"{rowId}_Item",f"enter an hour type for {type}: ")

        setValue(document,["persistent files", "exactOnline", "type mapping", type], exactOnlineType)



    def enterTimes(self, document: Json, timeSlices: list[tuple[datetime,datetime,str,str]]):

        today = datetime.today()
        
        mainContent = self.exactOnlineNavigateToPage(document, "/docs/MenuPortal.aspx",(By.ID, "MainWindow"))
        driver = self.getDriver()
        driver.switch_to.frame(mainContent)

        table = waitForElementVisibility(driver,By.CSS_SELECTOR,"table.timeEntryWidget")

        calendarDays = table.find_elements(By.CSS_SELECTOR,"tbody tr td.tbCell")

        currentDayLinkElem = None
        for day in calendarDays:
            dayNumber = 0
            try:
                dayNumber = int(day.find_element(By.CSS_SELECTOR,"span.dayOfMonth.thisMonth").text)
            except:
                pass
            
            if dayNumber == today.day:
                currentDayLinkElem = day.find_element(By.TAG_NAME,"a")
                break

        currentDayLinkElem.click()

        timeEntryForm = waitForElementVisibility(driver,By.TAG_NAME,"form")

        submitButton = timeEntryForm.find_element(By.ID,"btnSaveAsSubmitted")
        lastIdNumber = int(timeEntryForm.find_element(By.ID,"mtx_LastID").get_attribute("value"))
        addNewRowButton = timeEntryForm.find_element(By.ID, "mtx_addnew")


        for (start,end, type, description) in timeSlices:
            rowId = f"mtx_r{lastIdNumber}"
            currentRow = waitForElementVisibility(driver,By.ID,f"{rowId}")
            if currentRow.get_attribute("class") != "ExpandedRow":
                expandButton = waitForElementVisibility(driver,By.ID,f"{rowId}_Expand")
                expandButton.click()

            self.enterExactOnlineType(document,type,rowId, mainContent)

            descriptionInput = waitForElementVisibility(driver,By.ID,f"{rowId}_Notes")
            descriptionInput.clear()
            notes = f"{start.hour:0>2}:{start.minute:0>2} - {end.hour:0>2}:{end.minute:0>2}\n type: {type} \n\n {description}"
            descriptionInput.send_keys(notes)

            hourInput = waitForElementVisibility(driver,By.ID,f"{rowId}_c1_Quantity")
            hourInput.clear()
            diff = end - start
            hourAmountFormatted = "{:.2f}".format((diff.seconds/(60*60))).replace(".",",")
            hourInput.send_keys(hourAmountFormatted)
            addNewRowButton.click()
            lastIdNumber += 1

        if getValue(document,["persistent files", "exactOnline", "auto submit"], False):
            submitButton.click()
            return True
        elif promptBoolInput("submit times? (y/n)\n"):
            submitButton.click()
            return True
        
        return False

        

