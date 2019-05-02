#!/usr/bin/env python
import RPi.GPIO as GPIO
import time

RoAPin = 20    # pin11
RoBPin = 21    # pin12

globalCounter = 0

flag = 0
Last_RoB_Status = 0
Current_RoB_Status = 0
Out_Status = ''
def setup():
	GPIO.setmode(GPIO.BCM)       # Numbers GPIOs by BCM numbering
	GPIO.setup(RoAPin, GPIO.IN)    # input mode
	GPIO.setup(RoBPin, GPIO.IN)
	rotaryClear()

def rotaryDeal():
	global flag
	global Last_RoB_Status
	global Current_RoB_Status
	global globalCounter
	Last_RoB_Status = GPIO.input(RoBPin)
	while(not GPIO.input(RoAPin)):
		Current_RoB_Status = GPIO.input(RoBPin)
		flag = 1
	if flag == 1:
		flag = 0
		if (Last_RoB_Status == 0) and (Current_RoB_Status == 1):
			globalCounter = globalCounter - 1
			#print ('globalCounter = %d' % globalCounter)
			return globalCounter
		if (Last_RoB_Status == 1) and (Current_RoB_Status == 0):
			globalCounter = globalCounter + 1
			#print ('globalCounter = %d' % globalCounter)

def clear(ev=None):
	globalCounter = 0
	print ('globalCounter = %d') % globalCounter
	time.sleep(1)

def loop():
	global globalCounter
	while True:
		rotaryDeal()
#		print 'globalCounter = %d' % globalCounter

def destroy():
	GPIO.cleanup()             # Release resource
## **Insert this code into whatever code you want to use the encoder in**
##import Rot_Encoder as Enc
##
##if __name__ == '__main__':     # Program start from here
##	Enc.setup()
##	try:
##		Enc.loop()
##	except KeyboardInterrupt:  # When 'Ctrl+C' is pressed, the child program destroy() will be  executed.
##		Enc.destroy()
