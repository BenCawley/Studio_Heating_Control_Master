from state import State
import RPi.GPIO as GPIO
import I2C_LCD_driver as LCD
from signal import pause
from time import sleep
from threading import Thread

Screen1 = LCD.lcd(0x27)
Screen2 = LCD.lcd(0x26)
Screen3 = LCD.lcd(0x25)

#Defining GPIO assignments
GPIO.setmode(GPIO.BCM)
GPIO.setup(17, GPIO.IN, pull_up_down=GPIO.PUD_UP) # Left
GPIO.setup(27, GPIO.IN, pull_up_down=GPIO.PUD_UP) # Right
GPIO.setup(19, GPIO.IN, pull_up_down=GPIO.PUD_UP) # Up
GPIO.setup(13, GPIO.IN, pull_up_down=GPIO.PUD_UP) # Down
GPIO.setup(20, GPIO.IN) # Click
GPIO.setup(21, GPIO.IN) # Detent
GPIO.setup(16, GPIO.IN, pull_up_down=GPIO.PUD_UP) # Center 

#Defining Temperature Values
StudioSensors = {
'Sensor0' : 23,
'Sensor1' : 26,
'Sensor2' : 23,
'Sensor3' : 23,
'Sensor4' : 22,
'Sensor5' : 25
}

def SensorAverage(V):
    Total = 0
    for t in V:
        Total += V[t]
    Average = Total / len(V)
    return (Average)

Sensor6 = SensorAverage(StudioSensors)
Sensor7 = 12 #Outside
Sensor8 = 32 #Heater
Sensor9 = 6 #Chiller

TargetTemp = 21
TempTargetTemp = 21
SystemState = 'On'
SystemMode = 'Vent'

# Code for blinking LCD once the counting has finished, with loop number (x) and Timing (y) inputs

def BlinkLCD(dataUp, dataDown, dataFinalUp, dataFinalDown, x, y): 
    count = 0
    Screen1.lcd_clear()
    sleep(y)
    while count < x:
        Screen1.lcd_display_string(str(dataUp)[0:], 1)
        Screen1.lcd_display_string(str(dataDown)[0:], 2)
        sleep(y)
        Screen1.lcd_clear()
        sleep(y)
        count += 1
    Screen1.lcd_display_string(str(dataFinalUp), 1)
    Screen1.lcd_display_string(str(dataFinalDown), 2)

# Rotary Encoder Variables & Handler

globalCounter = 0
flag = 0
Last_RoB_Status = 0
Current_RoB_Status = 0

def rotaryDeal(channel):
        global flag
        global Last_RoB_Status
        global Current_RoB_Status
        global globalCounter
        Last_RoB_Status = GPIO.input(21)
        while(not GPIO.input(20)):
                Current_RoB_Status = GPIO.input(20)
                flag = 1
        if flag == 1:
                flag = 0
                if (Last_RoB_Status == 0) and (Current_RoB_Status == 1):
                        globalCounter = globalCounter - 1
                        LBP(channel)
                            
                if (Last_RoB_Status == 1) and (Current_RoB_Status == 0):
                        globalCounter = globalCounter + 1
                        RBP(channel)

# Backlight timer, timeout and wakeup handler (threaded)

count = 0
blState = 1
TempDisplayTimeOut = 300
DisplayTimeOut = 300

def DeviceTimeOut():
    global DisplayTimeOut
    global blState
    global count
    while True:
        count += 1
        sleep(1)
##        print (count)
        if count > DisplayTimeOut and blState == 1: 
            if Device.state != Sleep:
                Device.state = Sleep()


TimeOutCall = Thread(target=DeviceTimeOut)

TimeOutCall.start()

def BacklightCheck(): # Called every time a GPIO callback happens
    global count
    count = 0
    global blState
    if blState == 0:
        Screen1.backlight(1)
        Screen2.backlight(1)
        Screen3.backlight(1)
        blState = 1

##----------------------------------------------------------------------------------##

# Start of our states

class MainMenuPG1(State):

    #The default menu presented on boot (Currently the trunk for temperature adjust settings)
    
    def __init__(self):
        Screen1.lcd_clear()
        Screen1.lcd_display_string('Main Menu:'[0:], 1)
        Screen1.lcd_display_string('-Page 1'[0:], 2)

        Screen2.lcd_display_string('Current Temp: ' + str(Sensor6)[0:], 1)
        Screen2.lcd_display_string('Target Temp: ' + str(TargetTemp)[0:], 2)
        
        Screen3.lcd_display_string('Sys State: ' + SystemState[0:], 1)
        Screen3.lcd_display_string('Sys Mode: ' + SystemMode[0:], 2)

    def on_event(self, event):
        if event == DBP:
            return TargetTempAdjust()
        if event == RBP:
            return MainMenuPG2()
        return self

class MainMenuPG2(State):

    #The second menu page (currently the trunk for option adjust settings
    
    def __init__(self):
        Screen1.lcd_clear()
        Screen1.lcd_display_string('Main Menu:'[0:], 1)
        Screen1.lcd_display_string('-Page 2'[0:], 2)

        Screen2.lcd_display_string('Current Temp: ' + str(Sensor6)[0:], 1)
        Screen2.lcd_display_string('Target Temp: ' + str(TargetTemp)[0:], 2)
        
        Screen3.lcd_display_string('Sys State: ' + SystemState[0:], 1)
        Screen3.lcd_display_string('Sys Mode: ' + SystemMode[0:], 2)

    def on_event(self, event):
        if event == DBP:
            return DisplayTimeOutAdjust()
        if event == LBP:
            return MainMenuPG1()
        return self

class DisplayTimeOutAdjust(State):

    #The menu used for adjusting display timeout
    
    def __init__(self):
        Screen1.lcd_clear()
        Screen1.lcd_display_string('Display Timeout'[0:], 1)
        Screen1.lcd_display_string('Adjust: ' + str(TempDisplayTimeOut)[0:], 2)

        Screen2.lcd_display_string('Current Temp: ' + str(Sensor6)[0:], 1)
        Screen2.lcd_display_string('Target Temp: ' + str(TargetTemp)[0:], 2)
        
        Screen3.lcd_display_string('Sys State: ' + SystemState[0:], 1)
        Screen3.lcd_display_string('Sys Mode: ' + SystemMode[0:], 2)

    def on_event(self, event):
        if event == UBP:
            return MainMenuPG2()
        if event == RBP:
            return DisplayTimeOutInc()
        if event == LBP:
            return DisplayTimeOutDec()
        return self
    
class DisplayTimeOutInc(State):

    def __init__(self):
        global TempDisplayTimeOut
        TempDisplayTimeOut += 1
        Screen1.lcd_display_string('Adjust: ' + str(TempDisplayTimeOut)[0:], 2)

    def on_event(self, event):
        if event == UBP:
            return MainMenuPG2()
        if event == LBP:
            return DisplayTimeOutDec()
        if event == DBP:
            return DisplayTimeOutConf()
        if event == RBP:
            return DisplayTimeOutInc()
        return self

class DisplayTimeOutDec(State):

    def __init__(self):
        global TempDisplayTimeOut
        TempDisplayTimeOut -= 1
        Screen1.lcd_display_string('Adjust: ' + str(TempDisplayTimeOut)[0:], 2)

    def on_event(self, event):
        if event == UBP:
            return MainMenuPG2()
        if event == RBP:
            return DisplayTimeOutInc()
        if event == DBP:
            return DisplayTimeOutConf()
        if event == LBP and TempDisplayTimeOut >= 30:
            return DisplayTimeOutDec()
        return self

class DisplayTimeOutConf(State):

    def __init__(self):
        global DisplayTimeOut
        DisplayTimeOut = TempDisplayTimeOut
        BlinkLCD('Display Timeout','Set To: ' + str(DisplayTimeOut),'Display TimeOut: ', str(DisplayTimeOut), 3, 0.3)
        sleep(1)

    def on_event(self, event):
        if event == UBP:
            return MainMenuPG2()
        return self

class TargetTempAdjust(State):

    #The menu used for adjusting target temperature
    
    def __init__(self):
        Screen1.lcd_clear()
        Screen1.lcd_display_string('Target Temp'[0:], 1)
        Screen1.lcd_display_string('Adjust: ' + str(TargetTemp)[0:], 2)

        Screen2.lcd_display_string('Current Temp: ' + str(Sensor6)[0:], 1)
        Screen2.lcd_display_string('Target Temp: ' + str(TargetTemp)[0:], 2)
        
        Screen3.lcd_display_string('Sys State: ' + SystemState[0:], 1)
        Screen3.lcd_display_string('Sys Mode: ' + SystemMode[0:], 2)

    def on_event(self, event):
        if event == UBP:
            return MainMenuPG1()
        if event == RBP:
            return TargetTempInc()
        if event == LBP:
            return TargetTempDec()
        return self
    
class TargetTempInc(State):

    def __init__(self):
        global TempTargetTemp
        TempTargetTemp += 1
        Screen1.lcd_display_string('Adjust: ' + str(TempTargetTemp)[0:], 2)

    def on_event(self, event):
        if event == UBP:
            return MainMenuPG1()
        if event == LBP:
            return TargetTempDec()
        if event == DBP:
            return TargetTempConf()
        if event == RBP:
            return TargetTempInc()
        return self

class TargetTempDec(State):

    def __init__(self):
        global TempTargetTemp
        TempTargetTemp -= 1
        Screen1.lcd_display_string('Adjust: ' + str(TempTargetTemp)[0:], 2)

    def on_event(self, event):
        if event == UBP:
            return MainMenuPG1()
        if event == RBP:
            return TargetTempInc()
        if event == DBP:
            return TargetTempConf()
        if event == LBP:
            return TargetTempDec()
        return self

class TargetTempConf(State):

    def __init__(self):
        global TargetTemp
        TargetTemp = TempTargetTemp
        BlinkLCD('Target Temp Set','To: ' + str(TargetTemp),'Target Temp:', str(TargetTemp), 3, 0.3)
        Screen2.lcd_display_string('Target Temp: ' + str(TargetTemp)[0:], 2)
        sleep(1)

    def on_event(self, event):
        if event == UBP:
            return MainMenuPG1()
        return self

class Sleep(State):

    # This state gets called after a defined time period to save the screens from burn in

    def __init__(self):
        global blState
        Screen1.lcd_clear()
        Screen2.lcd_clear()
        Screen3.lcd_clear()
        Screen1.backlight(0)
        Screen2.backlight(0)
        Screen3.backlight(0)
        blState = 0
        
    def on_event(self, event):
        global count
        global blState
        if event == UBP or DBP or RBP or LBP:
            return MainMenuPG1()
            sleep(2)
        return self
        
# End of our states.

##---------------------------------------------------------------------------------------

class SimpleTestDevice(object):
    """ 
    A simple state machine that mimics the functionality of a device from a 
    high level.
    """

    def __init__(self):
        """ Initialize the components. """

        # Start with a default state.
        self.state = MainMenuPG1()
        
    def on_event(self, event):
        """
        This is the bread and butter of the state machine. Incoming events are
        delegated to the given states which then handle the event. The result is
        then assigned as the new state.
        """

        # The next state will be the result of the on_event function.
        self.state = self.state.on_event(event)
        print (self.state)

##---------------------------------------------------------------------------------------------------

Device = SimpleTestDevice()

#Setting up inputs to our state machine (Device) that are triggered by GPIO callbacks
def LBP(channel):
    Device.on_event(LBP)
    BacklightCheck()
def RBP(channel):
    Device.on_event(RBP)
    BacklightCheck()
def UBP(channel):
    Device.on_event(UBP)
    BacklightCheck()
def DBP(channel):
    Device.on_event(DBP)
    BacklightCheck()

#Setting up callbacks that activate when a button is pushed
GPIO.add_event_detect(17, GPIO.FALLING, callback=LBP, bouncetime=300)
GPIO.add_event_detect(27, GPIO.FALLING, callback=RBP, bouncetime=300)
GPIO.add_event_detect(19, GPIO.FALLING, callback=UBP, bouncetime=300)
GPIO.add_event_detect(13, GPIO.FALLING, callback=DBP, bouncetime=300)
GPIO.add_event_detect(16, GPIO.FALLING, callback=DBP) 
GPIO.add_event_detect(20 or 21, GPIO.BOTH, callback=rotaryDeal)

