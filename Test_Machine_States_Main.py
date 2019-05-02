from state import State
import RPi.GPIO as GPIO
import I2C_LCD_driver as LCD
from signal import pause
from time import sleep
from threading import Thread
import board
import busio
import adafruit_bmp280
import adafruit_tca9548a

Screen1 = LCD.lcd(0x27)
Screen2 = LCD.lcd(0x26)
Screen3 = LCD.lcd(0x25)

#Defining GPIO assignments
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(22, GPIO.IN, pull_up_down=GPIO.PUD_UP) # Left
GPIO.setup(23, GPIO.IN, pull_up_down=GPIO.PUD_UP) # Right
GPIO.setup(24, GPIO.IN, pull_up_down=GPIO.PUD_UP) # Up
GPIO.setup(25, GPIO.IN, pull_up_down=GPIO.PUD_UP) # Down
GPIO.setup(19, GPIO.IN) # Click
GPIO.setup(20, GPIO.IN) # Detent
GPIO.setup(21, GPIO.IN, pull_up_down=GPIO.PUD_UP) # Push Button
GPIO.setup(16, GPIO.OUT, initial=0) # Relay 1 - Extractor Fan
GPIO.setup(17, GPIO.OUT, initial=0) # Relay 2 - Cooling Fan
GPIO.setup(26, GPIO.OUT, initial=0) # Relay 3 - Peltier Element
GPIO.setup(27, GPIO.OUT, initial=0) # Relay 4 - Heating Fan

##-------------------------------------------------------------------------------------##
'''
To do:
- Write code to automatically change modes and maintain temperature
- Redo display timeout menu
- Add option for display timeout to be turned off


'''
##-------------------------------------------------------------------------------------##

# Create I2C bus for use by BMP280 sensors & Multiplexer
i2c = busio.I2C(board.SCL, board.SDA)
# Create the TCA9548A object and give it the I2C bus
tca = adafruit_tca9548a.TCA9548A(i2c)

#Creating a dictionary to store temperature sensors
SensorReaders = {
'tsl0' : adafruit_bmp280.Adafruit_BMP280_I2C(tca[0], 0x76),
'tsl1' : adafruit_bmp280.Adafruit_BMP280_I2C(tca[1], 0x76),
'tsl2' : adafruit_bmp280.Adafruit_BMP280_I2C(tca[2], 0x76),
'tsl3' : adafruit_bmp280.Adafruit_BMP280_I2C(tca[3], 0x76),
'tsl4' : adafruit_bmp280.Adafruit_BMP280_I2C(tca[4], 0x76),
'tsl5' : adafruit_bmp280.Adafruit_BMP280_I2C(tca[5], 0x76)
}

#Creating Temperature Variables
StudioSensors = {
'Sensor0' : 0,
'Sensor1' : 0,
'Sensor2' : 0,
'Sensor3' : 0,
'Sensor4' : 0,
'Sensor5' : 0
}

count = 0 # Counter for threaded operations

def SensorAverage(V):
    Total = 0
    for t in V:
        Total += V[t]
    Average = Total / len(V)
    return round(Average, 1)

Sensor6 = 0 #Studio Average
Sensor7 = 12 #Outside
Sensor8 = 32 #Heater
Sensor9 = 6 #Chiller

TargetTemp = 21
TempTargetTemp = 21

SystemStates = {
0 : 'Off',
1 : 'Manual',
2 : 'Auto'
}

SystemModes = {
0 : ['Vent', 1, 0, 0, 0], # [Name, Extractor, Cooler, Peltier, Heater] < Order of parameters
1 : ['Chill', 0, 1, 1, 0],
2 : ['Heat', 0, 0, 1, 1],
3 : ['Intake', 0, 1, 0, 0], 
4 : ['Idle', 0, 0, 0, 0] 
}

CurrentState = SystemStates[0]
CurrentMode = SystemModes[4]

def SystemModeHandler(List): # Gets passed a system mode list which it uses to change GPIO outputs and update current mode
    global CurrentMode
    CurrentMode = List
    if CurrentState == SystemStates[0]:
        GPIO.output(16, 0)
        GPIO.output(17, 0)
        GPIO.output(26, 0)
        GPIO.output(27, 0)
    elif CurrentState == SystemStates[1] or SystemStates[2]:
        GPIO.output(16, List[1])
        GPIO.output(17, List[2])
        GPIO.output(26, List[3])
        GPIO.output(27, List[4])
        if CurrentState == SystemStates[2] and Device.state == MainMenuPG1:
            Screen3Display()

def TempUpdate(): # Keeps the temp sensors updating and checks them every second
    global Sensor6
    while True:
        for i in range(6):
            StudioSensors['Sensor' + str(i)] = SensorReaders['tsl' + str(i)].temperature
        Sensor6 = SensorAverage(StudioSensors)
        sleep(1)
        #print (StudioSensors)

Thread(target=TempUpdate).start()

def Autonomy():
    while True:
        HT = (TargetTemp + 0.2)
        LT = (TargetTemp + 0.9)
        if CurrentState == SystemStates[2]:
##            print ('Autonomy Running...')
            if Sensor6 >= HT and Sensor6 <= LT and CurrentMode != SystemModes[4]:
                SystemModeHandler(SystemModes[4])
            elif Sensor6 < HT:
                if Sensor7 >= HT and CurrentMode != SystemModes[3]:
                    SystemModeHandler(SystemModes[3])
                elif Sensor7 < HT and CurrentMode != SystemModes[2]:
                    SystemModeHandler(SystemModes[2])
            elif Sensor6 > LT:
                if Sensor7 <= LT and CurrentMode != SystemModes[3]:
                    SystemModeHandler(SystemModes[3])
                elif Sensor7 > LT and CurrentMode != SystemModes[1]:
                    SystemModeHandler(SystemModes[1])
        sleep(1)
            
Thread(target=Autonomy).start()



##----------------------------------------------------------------------------------##

# Code for blinking LCD once the counting has finished, with loop number (x) and Timing (y) inputs

def BlinkLCD(dataUp, dataDown, dataFinalUp, dataFinalDown, x, y): 
    count = 0
    Screen2.lcd_clear()
    sleep(y)
    while count < x:
        Screen2.lcd_display_string(str(dataUp)[0:], 1)
        Screen2.lcd_display_string(str(dataDown)[0:], 2)
        sleep(y)
        Screen2.lcd_clear()
        sleep(y)
        count += 1
    Screen2.lcd_display_string(str(dataFinalUp), 1)
    Screen2.lcd_display_string(str(dataFinalDown), 2)

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
        Last_RoB_Status = GPIO.input(20)
        while(not GPIO.input(19)):
                Current_RoB_Status = GPIO.input(19)
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

Thread(target=DeviceTimeOut).start()

def BacklightCheck(): # Called every time a GPIO callback happens
    global count
    count = 0
    global blState
    if blState == 0:
        Screen1.backlight(1)
        Screen2.backlight(1)
        Screen3.backlight(1)
        blState = 1

def Screen3Conf(): # Short function to make displaying the confirm screen easier
    Screen3.lcd_clear()
    Screen3.lcd_display_string('^    Cancel    ^'[0:], 1)
    Screen3.lcd_display_string('v   Confirm?   v'[0:], 2)

def Screen3Display():
    Screen3.lcd_clear()
    Screen3.lcd_display_string('Sys State:' + CurrentState[0:], 1)
    Screen3.lcd_display_string('Sys Mode:' + CurrentMode[0][0:], 2)

##----------------------------------------------------------------------------------##

# Section containing the machine states

class MainMenuPG1(State):

    #The default menu presented on boot (Currently the trunk for parameter adjustment settings)
    
    def __init__(self):
        Screen1.lcd_clear()
        Screen1.lcd_display_string('  System  Info  '[0:], 1)
        Screen1.lcd_display_string('v              >'[0:], 2)

        Screen2.lcd_clear()
        Screen2.lcd_display_string('Studio Temp:' + str(Sensor6)[0:], 1)
        Screen2.lcd_display_string('Target Temp: ' + str(TargetTemp)[0:], 2)
        
        Screen3Display()

    def on_event(self, event):
        if event == DBP:
            return SystemStateAdjust()
        if event == RBP:
            return MainMenuPG2()
        return self

class SystemStateAdjust(State):

    #The menu used for changing system state between manual and auto
    
    def __init__(self):
        Screen1.lcd_clear()
        Screen1.lcd_display_string('  System State  '[0:], 1)
        Screen1.lcd_display_string('v    Adjust    ^'[0:], 2)

        sleep(0.2)
        Screen2.lcd_clear()
        Screen2.lcd_display_string('Current: ' + str(CurrentState)[0:], 1)
        Screen2.lcd_display_string('     Change    >'[0:], 2)
        
        Screen3Display()

    def on_event(self, event):
        if event == DBP:
            return SystemModeAdjust()
        if event == UBP:
            return MainMenuPG1()
        if event == RBP:
            Screen3Conf()
            if CurrentState == SystemStates[0]:
                return SystemStateManual()
            else:
                return SystemStateOff()
        return self

class SystemStateOff(State):

    def __init__(self):
        Screen2.lcd_clear()
        Screen2.lcd_display_string('Current: ' + str(CurrentState)[0:], 1)
        Screen2.lcd_display_string('<     Off      >'[0:], 2)

    def on_event(self, event):
        global CurrentState
        if event == UBP:
            return MainMenuPG1()
        if event == LBP:
            return SystemStateAdjust()
        if event == DBP:
            CurrentState = SystemStates[0]
            SystemModeHandler(CurrentMode)
            return SystemStateAdjust()
        if event == RBP:
            if CurrentState == SystemStates[1]:
                return SystemStateAuto()
            else:
                return SystemStateManual()
        return self

class SystemStateManual(State):
    
    def __init__(self):
        Screen2.lcd_clear()
        Screen2.lcd_display_string('Current: ' + str(CurrentState)[0:], 1)
        if CurrentState == SystemStates[2]:
            Screen2.lcd_display_string('<    Manual     '[0:], 2)
        else:
            Screen2.lcd_display_string('<    Manual    >'[0:], 2)

    def on_event(self, event):
        global CurrentState
        if event == UBP:
            return MainMenuPG1()
        if event == LBP:
            if CurrentState == SystemStates[0]:
                return SystemStateAdjust()
            else:
                return SystemStateOff()
        if event == DBP:
            CurrentState = SystemStates[1]
            SystemModeHandler(CurrentMode)
            return SystemStateAdjust()
        if event == RBP:
            if CurrentState == SystemStates[2]:
                return self
            else:
                return SystemStateAuto()
        return self

class SystemStateAuto(State):

    def __init__(self):
        Screen2.lcd_clear()
        Screen2.lcd_display_string('Current: ' + str(CurrentState)[0:], 1)
        Screen2.lcd_display_string('<     Auto      '[0:], 2)

    def on_event(self, event):
        global CurrentState
        if event == UBP:
            return MainMenuPG1()
        if event == LBP:
            if CurrentState == SystemStates[1]:
                return SystemStateOff()
            else:
                return SystemStateManual()
        if event == DBP:
            CurrentState = SystemStates[2]
            return SystemStateAdjust()
        return self

class SystemModeAdjust(State):

    #The menu for changing system modes when system state is in manual
    
    def __init__(self):
        Screen1.lcd_clear()
        Screen1.lcd_display_string('  System  Mode  '[0:], 1)
        Screen1.lcd_display_string('v    Adjust    ^'[0:], 2)

        Screen2.lcd_clear()
        Screen2.lcd_display_string('Current: ' + (CurrentMode[0])[0:], 1)
        Screen2.lcd_display_string('     Change    >'[0:], 2)
        
        Screen3Display()

    def on_event(self, event):
        global CurrentMode
        if event == DBP:
            return TargetTempAdjust()
        if event == UBP:
            return SystemStateAdjust()
        if event == RBP:
            Screen3Conf()
            if CurrentMode == SystemModes[0]:
                return SystemModeChill()
            else:
                return SystemModeVent()
        return self

class SystemModeVent(State):

    def __init__(self):
        Screen2.lcd_display_string('Current: ' + (CurrentMode[0])[0:], 1)
        Screen2.lcd_display_string('<     Vent     >'[0:], 2)

    def on_event(self, event):
        global CurrentMode
        if event == DBP:
            SystemModeHandler(SystemModes[0])
            return SystemModeAdjust()
        if event == UBP:
            return SystemStateAdjust()
        if event == LBP:
            return SystemModeAdjust()
        if event == RBP:
            if CurrentMode == SystemModes[1]:
                return SystemModeHeat()
            else:
                return SystemModeChill()
        return self

class SystemModeChill(State):

    def __init__(self):
        Screen2.lcd_display_string('Current: ' + (CurrentMode[0])[0:], 1)
        Screen2.lcd_display_string('<     Chill    >'[0:], 2)

    def on_event(self, event):
        global CurrentMode
        if event == DBP:
            SystemModeHandler(SystemModes[1])
            return SystemModeAdjust()
        if event == UBP:
            return SystemStateAdjust()
        if event == LBP:
            if CurrentMode == SystemModes[0]:
                return SystemModeAdjust()
            else:
                return SystemModeVent()
        if event == RBP:
            if CurrentMode == SystemModes[2]:
                return SystemModeIntake()
            else:
                return SystemModeHeat()
        return self

class SystemModeHeat(State):

    def __init__(self):
        Screen2.lcd_display_string('Current: ' + (CurrentMode[0])[0:], 1)
        Screen2.lcd_display_string('<     Heat     >'[0:], 2)

    def on_event(self, event):
        global CurrentMode
        if event == DBP:
            SystemModeHandler(SystemModes[2])
            return SystemModeAdjust()
        if event == UBP:
            return SystemStateAdjust()
        if event == LBP:
            if CurrentMode == SystemModes[1]:
                return SystemStateVent()
            else:
                return SystemStateChill()
        if event == RBP:
            if CurrentMode == SystemModes[3]:
                return SystemModeIdle()
            else:
                return SystemModeIntake()
        return self

class SystemModeIntake(State):
    
    def __init__(self):
        Screen2.lcd_display_string('Current: ' + (CurrentMode[0])[0:], 1)
        if CurrentMode == SystemModes[4]:
            Screen2.lcd_display_string('<    Intake     '[0:], 2)
        else:
            Screen2.lcd_display_string('<    Intake    >'[0:], 2)

    def on_event(self, event):
        global CurrentMode
        if event == DBP:
            SystemModeHandler(SystemModes[3])
            return SystemModeAdjust()
        if event == UBP:
            return SystemStateAdjust()
        if event == LBP:
            if CurrentMode == SystemModes[2]:
                return SystemModeChill()
            else:
                return SystemModeHeat()
        if event == RBP:
            if CurrentMode == SystemModes[4]:
                return self
            else:
                return SystemModeIdle()
        return self

class SystemModeIdle(State):
    
    def __init__(self):
        Screen2.lcd_display_string('Current: ' + (CurrentMode[0])[0:], 1)
        Screen2.lcd_display_string('<     Idle      '[0:], 2)

    def on_event(self, event):
        global CurrentMode
        if event == DBP:
            SystemModeHandler(SystemModes[4])
            return SystemModeAdjust()
        if event == UBP:
            return SystemStateAdjust()
        if event == LBP:
            if CurrentMode == SystemModes[3]:
                return SystemModeHeat()
            else:
                return SystemModeIntake()
        return self

class TargetTempAdjust(State):

    #The menu used for adjusting target temperature
    
    def __init__(self):
        Screen1.lcd_clear()
        Screen1.lcd_display_string('  Target  Temp  '[0:], 1)
        Screen1.lcd_display_string('     Adjust    ^' + str(TargetTemp)[0:], 2)

        Screen2.lcd_clear()
        Screen2.lcd_display_string('Current: ' + str(TargetTemp)[0:], 1)
        Screen2.lcd_display_string('<    Change    >'[0:], 2)
        
        Screen3Display()

    def on_event(self, event):
        if event == UBP:
            return SystemModeAdjust() 
        if event == RBP:
            Screen3Conf()
            return TargetTempInc()
        if event == LBP:
            Screen3Conf()
            return TargetTempDec()
        return self
    
class TargetTempInc(State):

    def __init__(self):
        global TempTargetTemp
        TempTargetTemp += 1
        Screen2.lcd_display_string('<      ' + str(TempTargetTemp) + '      >'[0:], 2)

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
        Screen2.lcd_display_string('<      ' + str(TempTargetTemp) + '      >'[0:], 2)

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
        Screen1.lcd_clear()
        Screen3.lcd_clear()
        BlinkLCD('Target Temp Set','To: ' + str(TargetTemp),'Target Temp:', str(TargetTemp), 3, 0.3)
        Screen2.lcd_display_string('^              ^'[0:], 1)
        Screen2.lcd_display_string('Target Temp: ' + str(TargetTemp)[0:], 2)
        sleep(1)

    def on_event(self, event):
        if event == UBP:
            return MainMenuPG1()
        return self

class MainMenuPG2(State):

    #The second menu page (currently the trunk for option adjust settings)
    
    def __init__(self):
        Screen1.lcd_clear()
        Screen1.lcd_display_string('System Options'[0:], 1)
        Screen1.lcd_display_string('<              v'[0:], 2)

        Screen2.lcd_display_string('Studio Temp:' + str(Sensor6)[0:], 1)
        Screen2.lcd_display_string('Target Temp: ' + str(TargetTemp)[0:], 2)
        
        Screen3Display()

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
        Screen1.lcd_display_string('Adjust: ' + str(int(TempDisplayTimeOut / 60)) + ' Mins'[0:], 2)

        Screen2.lcd_display_string('Studio Temp:' + str(Sensor6)[0:], 1)
        Screen2.lcd_display_string('Target Temp: ' + str(TargetTemp)[0:], 2)
        
        Screen3Display()

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
        TempDisplayTimeOut += 60
        Screen1.lcd_display_string('Adjust: ' + str(int(TempDisplayTimeOut / 60)) + ' Mins'[0:], 2)

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
        TempDisplayTimeOut -= 60
        Screen1.lcd_display_string('Adjust: ' + str(int(TempDisplayTimeOut / 60)) + ' Mins'[0:], 2)

    def on_event(self, event):
        if event == UBP:
            return MainMenuPG2()
        if event == RBP:
            return DisplayTimeOutInc()
        if event == DBP:
            return DisplayTimeOutConf()
        if event == LBP and TempDisplayTimeOut >= 61:
            return DisplayTimeOutDec()
        return self

class DisplayTimeOutConf(State):

    def __init__(self):
        global DisplayTimeOut
        DisplayTimeOut = TempDisplayTimeOut
        BlinkLCD('Display Timeout','Set To: ' + str(int(DisplayTimeOut / 60)) + ' Mins', 'Display TimeOut: ', str(int(DisplayTimeOut / 60)) + ' Minutes', 3, 0.3)
        sleep(1)

    def on_event(self, event):
        if event == UBP:
            return MainMenuPG2()
        return self

class Sleep(State):

    # This state gets called after a defined time period to save the screens from burn in and maintain privacy

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

class StateMachineDevice(object):
    """ 
    A simple state machine that mimics the functionality of a device from a 
    high level.
    """

    def __init__(self):
        """ Initialize the components. """

        # Start with a default state.
        self.state = MainMenuPG1() # Create variable for current state
        self.last_state = MainMenuPG1() # and the previous state
        
    def on_event(self, event):
        """
        This is the bread and butter of the state machine. Incoming events are
        delegated to the given states which then handle the event. The result is
        then assigned as the new state.
        """
        self.last_state = self.state # Records the current state in last_state for reference
        self.state = self.state.on_event(event) # The next state will be the result of the on_event function.
        print ('Last ' + str(self.last_state)) 
        print ('Current ' + str(self.state)) # Prints the states for debugging

##---------------------------------------------------------------------------------------------------

Device = StateMachineDevice()

# Updates the display with the current temperature every second
def DisplayUpdater():
    global Device
    UpdaterStates = {
        0 : 'MainMenuPG1',
        1 : 'MainMenuPG2'
        }
##    print (UpdaterStates.values())
##    print (str(Device.state))
    while True:
        if (str(Device.state) in UpdaterStates.values()):
            Screen2.lcd_display_string('Studio Temp:' + str(Sensor6)[0:], 1)
        sleep(1)
 
Thread(target=DisplayUpdater).start()

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
GPIO.add_event_detect(22, GPIO.FALLING, callback=LBP, bouncetime=500)
GPIO.add_event_detect(23, GPIO.FALLING, callback=RBP, bouncetime=500)
GPIO.add_event_detect(24, GPIO.FALLING, callback=UBP, bouncetime=500)
GPIO.add_event_detect(25 , GPIO.FALLING, callback=DBP, bouncetime=500)
GPIO.add_event_detect(21, GPIO.FALLING, callback=DBP) 
GPIO.add_event_detect(19 or 20, GPIO.BOTH, callback=rotaryDeal)
