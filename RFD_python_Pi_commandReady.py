import time, threading
from time import strftime
import subprocess
import datetime
import io
import picamera
import serial
import sys
import os
import Image
import base64
import hashlib
import re
import string
from array import array
import RPi.GPIO as GPIO


#------------
    #Adafruit

#import Adafruit_GPIO.SPI as SPI
import Adafruit_SSD1306

import Image
import ImageDraw
import ImageFont



# ------- Raspberry Pi pin configuration: -----
# camera mux enable pins
# board numbering
#selection = 7                           # variable used for GPIO pin 7  - mux "selection"
#enable1 = 11                            # variable used for GPIO pin 11 - mux "enable 1"
#enable2 = 12                            # variable used for GPIO pin 12 - mux "enable 2"

# broadcom numbering    ***** used by adafruits libraries *****
selection = 4
enable1 = 17
enable2 = 18

RST = 24
try:
    disp = Adafruit_SSD1306.SSD1306_128_64(rst=RST)
    # Initialize library.
    disp.begin()
    # Clear display.
    disp.clear()
    disp.display()

    # Create blank image for drawing.
    # Make sure to create image with mode '1' for 1-bit color.
    width = disp.width
    height = disp.height
    # Get drawing object to draw on image.
    draw = ImageDraw.Draw(image)

    # Draw a black filled box to clear the image.3
    draw.rectangle((0,0,width,height), outline=0, fill=0)


    # Load default font.
    font = ImageFont.load_default()
    # Display image.
    disp.image(image)
    disp.display()
except:
    i2cpresentflag = 1

#I2C check value
i2cpresentflag = 1


#RFD900 Serial Variables
port  = "/dev/ttyAMA0"
baud = 38400
timeout = 3

# Arduino Serial Variables
ardPort = "/dev/arduino"
ardBaud = 115200
ardTimeout = 3

# XBee Serial Variables
xPort = "/dev/xbee"
xBaud = 9600
xTimeout = 3

# ----  Initializations  -----
wordlength = 7000
checkOK = ''
ser = serial.Serial(port = port, baudrate = baud, timeout = timeout)
#xbee = serial.Serial(port = xPort, baudrate = xBaud, timeout = xTimeout)
ardSer = serial.Serial(port = ardPort, baudrate = ardBaud, timeout = ardTimeout)
pic_interval = 60
extension = ".jpg"
folder = "/home/pi/RFD_Pi_Code/%s/" % strftime("%m%d%Y_%H%M%S")
dir = os.path.dirname(folder)
if not os.path.exists(dir):
    os.mkdir(dir)
    
fh = open(folder + "imagedata.txt","w")
fh.write("")
fh.close()


#Camera Settings
width = 650
height = 450 
resolution = (width,height)
sharpness = 0
brightness = 50
contrast = 0
saturation = 0
iso = 400
camera_annotation = 'hi'                # global variable for camera annottation, initialize to something to prevent dynamic typing from changing type
cam_hflip = False                       # global variable for camera horizontal flip
cam_vflip = False                       # global variable for camera vertical flip

# GPIO settings for camera mux
#GPIO.setmode(GPIO.BOARD)        # use board numbering for GPIO header vs broadcom **** broadcom used in adafruit library dependant stuff ****
GPIO.setup(selection, GPIO.OUT)         # mux "select"
GPIO.setup(enable1, GPIO.OUT)           # mux "enable1"
GPIO.setup(enable2, GPIO.OUT)           # mux "enable2"
xbeeReceived = []
xbeeToSend = []
resetFlag = False
completeExit = False

piCommands = ['1','2','3','4','5','6','7','T','G','P']      # A list of all commands that the Pi looks for itself

# Thread to control the xbee radio so that it can run in parallel with the RFD radio
class xbeeThread(threading.Thread):
    def __init__(self,threadID):        # Constructor
        threading.Thread.__init__(self)
        self.threadID = threadID
    def run(self):                      # Thread loop
        global xbeeReceived, xbeeToSend, xPort, xBaud, xTimeout, completeExit
        xbee = serial.Serial(port = xPort, baudrate = xBaud, timeout = xTimeout)    # Open the xbee port first thing
        while not completeExit:         # Run this code forever
            try:
                line = xbee.readline()
                if line not in xbeeReceived:        # We don't want to fill it with the same piece of data over and over again while we wait for the RFD to send it out
                    xbeeReceived.append(line)
                for each in xbeeToSend:             # For everything added in the other thread, send them all out
                    xbee.write(each)
                xbeeToSend = []                     # Clear the send list once everything is sent
            except:         # This catches unexpected errors in the thread, and makes sure that the thread will start up again next loop
                resetFlag = True
                xbee.close()
                

def enable_camera_A():
    global cam_hflip
    global cam_vflip
    global camera_annotation
    GPIO.output(selection, False)
    GPIO.output(enable2, True)          # pin that needs to be high set first to avoid enable 1 and 2 being low at same time
    GPIO.output(enable1, False)         # if coming from a camera that had enable 2 low then we set enable 1 low on next camera
    #GPIO.output(enable2, True)         # first, we would have both enables low at the same time
    cam_hflip = False
    cam_vflip = False
    camera_annotation = 'Camera A'
    time.sleep(0.5)
    return

def enable_camera_B():
    global cam_hflip
    global cam_vflip
    global camera_annotation
    GPIO.output(selection, True)
    GPIO.output(enable2, True)
    GPIO.output(enable1, False)
    #GPIO.output(enable2, True)
    cam_hflip = False
    cam_vflip = False
    camera_annotation = 'Camera B'
    time.sleep(0.5)                        # ??? are these delays going to mess with timming else where ???
    return

def enable_camera_C():
    global cam_hflip
    global cam_vflip
    global camera_annotation
    GPIO.output(selection, False)
    GPIO.output(enable1, True)           # make sure first enable pin to be changed is going high
    GPIO.output(enable2, False)
    cam_hflip = False
    cam_vflip = False
    camera_annotation = 'Camera C'
    time.sleep(0.5)
    return

def enable_camera_D():
    global cam_hflip
    global cam_vflip
    global camera_annotation
    GPIO.output(selection, True)
    GPIO.output(enable1, True)
    GPIO.output(enable2, False)
    cam_hflip = False
    cam_vflip = False
    camera_annotation = 'Camera D'
    time.sleep(0.5)
    return


def initOLED():
    global draw
    global disp
    global font
    global image
    disp.begin()
    # Clear display.
    disp.clear()
    disp.display()

    # Create blank image for drawing.
    # Make sure to create image with mode '1' for 1-bit color.
    width = disp.width
    height = disp.height
    image = Image.new('1', (width, height))

    # Get drawing object to draw on image.
    draw = ImageDraw.Draw(image)

    # Draw a black filled box to clear the image.
    draw.rectangle((0,0,width,height), outline=0, fill=0)


    # Load default font.
    font = ImageFont.load_default()

    # Alternatively load a TTF font.
    # Some other nice fonts to try: http://www.dafont.com/bitmap.php
    #font = ImageFont.truetype('Minecraftia.ttf', 8)

    # Write two lines of text.
    draw.rectangle((0,0,width,height), outline=0, fill=0)
    disp.image(image)
    disp.display()

#    image = Image.open("MSGC.png")
#    image_r = image.resize((width,height),Image.BICUBIC)
#    image_bw = image_r.convert("1")
#
#    # Get drawing object to draw on image.
#    draw = ImageDraw.Draw(image)
#
#    for x in range(width):
#        for y in range (height):
#            disp.draw_pixel(x,y,bool(int(image_bw.getpixel((x,y)))))
#    disp.display()
#    time.sleep(1)
    return

def UpdateDisplay():
    global i2cpresentflag
    global draw
    global disp
    global image
    global font
    try:
        result = subprocess.check_output(["sudo","i2cdetect","-y","1"])
        if (i2cpresentflag == 1):
            if "3c" in result:
                initOLED()
                i2cpresentflag = 0
            else:
                return
        else:
            if not "3c" in result:
                i2cpresentflag = 1
        FirstLine = str(datetime.datetime.now().strftime("%m/%d/%Y %H:%M:%S"))
        SecondLine = ""
        ThirdLine = ""
        FourthLine = ""
        try:
            for line in reversed(list(open(folder+"piruntimedata.txt"))):
                if (SecondLine == ""):
                    SecondLine = line.rstrip()
                elif (ThirdLine == ""):
                    ThirdLine = line.rstrip()
                elif (FourthLine == ""):
                    FourthLine = line.rstrip()
                else:
                    break
        except:
            print "Error with Display Update"
        draw.rectangle((0,0,width,height), outline=0, fill=0)
        draw.text((0, 0), FirstLine,  font=font, fill=255)
        draw.text((0,15), FourthLine, font=font, fill=255)
        draw.text((0,30), ThirdLine, font=font, fill = 255)
        draw.text((0,45), SecondLine, font=font, fill=255)
        disp.image(image)
        disp.display()
        return
    except:
        return

def smile():
    global i2cpresentflag
    global draw
    global disp
    global image
    global font
    try:
        result = subprocess.check_output(["sudo","i2cdetect","-y","1"])
        if (i2cpresentflag == 1):
            if "3c" in result:
                initOLED()
                #UpdateDisplay()
                i2cpresentflag = 0
            else:
                return
        else:
            if not "3c" in result:
                i2cpresentflag = 1
        
        draw.rectangle((0,0,width,height), outline=0, fill=0)
        draw.text((0,0),"Capturing Photo...", font = font, fill = 255)
        draw.line([(40,20),(40,35)],fill = 255)
        draw.line([(50,20),(50,35)],fill = 255)
        draw.arc((20,30,70,60),20,160,fill = 255)
        disp.image(image)
        disp.display()
        time.sleep(0.5)
        return
    except:
        return

# Resets the camera to the default settings
def reset_cam():
    global width
    global height
    global sharpness
    global brightness
    global contrast
    global saturation
    global iso
    width = 650
    height = 450 
    resolution = (width,height)
    sharpness = 0
    brightness = 50
    contrast = 0
    saturation = 0
    iso = 400
    file = open(folder + "camerasettings.txt","w")
    file.write(str(width)+"\n")
    file.write(str(height)+"\n")
    file.write(str(sharpness)+"\n")
    file.write(str(brightness)+"\n")
    file.write(str(contrast)+"\n")
    file.write(str(saturation)+"\n")
    file.write(str(iso)+"\n")
    file.close()

# Converts an image to 64 bit encoding
def image_to_b64(path):
    with open(path,"rb") as imageFile:
        return base64.b64encode(imageFile.read())

# Converts a 64 bit encoding to an image
def b64_to_image(data,savepath):
    fl = open(savepath,"wb")
    fl.write(data.decode('base4'))
    fl.close()

# Creates a checksum based on data
def gen_checksum(data,pos):
    return hashlib.md5(data[pos:pos+wordlength]).hexdigest()

# Sends the appropriately sized piece of the total picture encoding
def sendword(data,pos):
    if(pos + wordlength < len(data)):       # Take a piece of size wordlength from the whole, and send it
        for x in range(pos, pos+wordlength):
            ser.write(data[x])
        return
    else:                                   # If the wordlength is greater than the amount remaining, send everything left
        for x in range(pos, len(data)):
            ser.write(data[x])
        return

# Synchronizes the data stream between the Pi and the ground station
def sync():
    synccheck = ''
    synctry = 5
    syncterm = time.time() + 10
    while((synccheck != 'S')&(syncterm > time.time())):
        ser.write("sync")
        synccheck = ser.read()
        if(synctry == 0):
            if (synccheck == ""):
                print "SyncError"
                break
        synctry -= 1
    time.sleep(0.5)
    return

# Sends the image through the RFD in increments of size wordlength
def send_image(exportpath):
    global wordlength
    timecheck = time.time()
    done = False
    cur = 0
    trycnt = 0
    outbound = image_to_b64(exportpath)     # Determine where the encoded image is
    size = len(outbound)
    print size,": Image Size"
    print "photo request received"
    ser.write(str(size)+'\n')               # Send the total size so the ground station knows how big it will be
    while(cur < len(outbound)):
        print "Send Position:", cur," // Remaining:", int((size - cur)/1024), "kB"      # Print out how much picture is remaining in kilobytes
        checkours = gen_checksum(outbound,cur)      # Create the checksum to send for the ground station to compare to
        ser.write(checkours)
        sendword(outbound,cur)                      # Send a piece of size wordlength
        #UpdateDisplay()
        checkOK = ser.read()
        if (checkOK == 'Y'):                # This is based on whether or not the word was successfully received based on the checksums
            cur = cur + wordlength
            trycnt = 0
        else:
            if(trycnt < 5):                 # There are 5 tries to get the word through, each time you fail, drop the wordlength by 1000
                if wordlength >1000:
                    wordlength -= 1000
                sync()
                trycnt += 1
                print "try number:", trycnt
                print "resending last @", cur
                print "ours:",checkours
                print "Wordlength",wordlength
            else:
                print "error out"
                cur = len(outbound)
    print "Image Send Complete"
    print "Send Time =", (time.time() - timecheck)
    return

class Unbuffered:
    def __init__(self,stream):
        self.stream = stream
    def write(self,data):
        self.stream.write(data)
        self.stream.flush()
        logfile.write(data)
        logfile.flush()

logfile = open(folder+"piruntimedata.txt","w")
logfile.close()
logfile = open(folder+"piruntimedata.txt","a")
sys.stdout = Unbuffered(sys.stdout)
imagenumber = 0
recentimg = ""
reset_cam()
starttime = time.time()
print "Startime @ ",starttime
checkpoint = time.time()

enable_camera_A()          # initialize the camera to something so mux is not floating

sideThread = xbeeThread("Thread -1")            # Get the xbee thread going to start
sideThread.start()

############################### Main loop #################################
while(True):
    try:
        print "RT:",int(time.time() - starttime),"Watching Serial"
        #UpdateDisplay()
    ##    command = str(ser.readline())

        # Read from the RFD for a certain amount of time, or until the EOL character has been found
        timeCheck = time.time()
        command = ''
        done = False
        while not done and (time.time()-timeCheck) < 3:
            newChar = ser.read()
            if newChar in piCommands and len(command) == 0:
                command = newChar
                done = True
            elif newChar == "!":
                command += newChar
                done = True
            elif newChar != '':
                command += newChar
                timeCheck = time.time()
                    
        if command != '':           # If there was a command, print it
            print("Command: " + command)

        # Command 1: Send most recent image
        if (command == '1'):
            ser.write('A')      # Send the acknowledge
            try:
                print "Send Image Command Received"
                #UpdateDisplay()
                #sync()
                print "Sending:", recentimg
                ser.write(recentimg)
                send_image(folder+recentimg)            # Send the most recent image
                wordlength = 7000                       # Reset the wordlength in case it was changed while sending
            except:
                print "Send Recent Image Error"

        # Command 2: Sends imagedata.txt
        if (command == '2'):
            ser.write('A')
            try:
                print "data list request recieved"
                #UpdateDisplay()
                #sync()
                file = open(folder+"imagedata.txt","r")
                print "Sending imagedata.txt"
                for line in file:
                    ser.write(line)
                    #print line
                file.close()
                time.sleep(1)
            except:
                print "Error with imagedata.txt read or send"

        # Command 3: Sends the requested image
        if (command == '3'):
            ser.write('A')
            try:
                print"specific photo request recieved"
                #UpdateDisplay()
                #sync()
                imagetosend = ser.read(15)                  # Determine which picture to send
                print(imagetosend)
                send_image(folder+imagetosend)
                wordlength = 7000
            except:
                print "Send Specific Image Error"

        # Command 4: Send camera settings
        if (command == '4'):
            ser.write('A')
            try:
                print "Attempting to send camera settings"
                #UpdateDisplay()
                #sync()
                camFile = open(folder+"camerasettings.txt","r")        # Open the camera settings file
                temp = camFile.read()
                while(temp != ""):      # For every line in the file, send it to the RFD
                    ser.write(temp)
                    temp = camFile.read()
                ser.write("\r")
                camFile.close()
                print "Camera Settings Sent"
            except:
                print "cannot open file/file does not exist"
                reset_cam()         # If there's an issue with camerasettings.txt, reset it

        # Command 5: Update camera settings
        if (command == '5'):
            ser.write('A')
            try:
                print "Attempting to update camera settings"
                #UpdateDisplay()
                file = open(folder+"camerasettings.txt","w")
                temp = ser.read()
                temp = ser.read()
                while(temp != ""):
                    file.write(temp)
                    temp = ser.read()
                file.close()
                print "New Camera Settings Received"
                ser.write('A')
                checkpoint = time.time()
            except:
                print "Error Retrieving Camera Settings"
                reset_cam()
                
        # Command6: Connection test, test ping time
        if (command == '6'):
                ser.write('A')
                print "Ping Request Received"
                #UpdateDisplay()
                try:
                    print "test"
                    termtime = time.time() + 10
                    pingread = ser.read()
                    while ((pingread != 'D') &(pingread != "") & (termtime > time.time())):     # Look for the stop character D, no new info, or too much time passing
                        if (pingread == 'P'):       # Whenever you get the P, send one back and get ready for another
                            print "Ping Received"
                            ser.flushInput()
                            ser.write('P')
                        else:                       # If you don't get the P, sne back an A instead
                            print "pingread = ",pingread
                            ser.flushInput()
                            ser.write('A')
                        pingread = ser.read()       # Read the next character
                        sys.stdin.flush()
                except:
                    print "Ping Runtime Error"

        # Command 7: Send runtimedata
        if (command == '7'):
            ser.write('A')
            try:
                print "Attempting to send piruntimedata"
                #UpdateDisplay()
                #sync()
                file = open(folder+"piruntimedata.txt","r")     # Open the runtimedata file
                temp = file.readline()
                while(temp != ""):      # Send everyting in the file until it's empty
                    ser.write(temp)
                    temp = file.readline()
                #ser.write("\r")
                file.close()
                print "piruntimedata.txt sent"
            except:
                print "error sending piruntimedata.txt"

    # ------  camera/mux commands  --------

        if (command == '8' + "\n"):             # enable camera a
            ser.write('A')
            try:
                print 'command received to enable camera A, attempting to enable camera A'
                enable_camera_A()
                #time.sleep(2)
                print 'returned from enabling camera A'

            except:
                print 'Not done, need to implement catch condition for enable camera A'

        if (command == '9'+"\n"):             # enable camera b
            ser.write('A')
            try:
                print 'command received to enable camera B, attempting to enable camera B'
                enable_camera_B()
                #time.sleep(2)
                print 'returned from enabling camera B'

            except:
                print 'Not done, need to implement catch condition for enable camera B'

        if (command == 'c'+"\n"):             # enable camera c
            ser.write('A')
            try:
                print 'command received to enable camera C, attempting to enable camera C'
                enable_camera_C()
                #time.sleep(2)
                print 'returned from enabling camera C'

            except:
                print 'Not done, need to implement catch condition for enable camera C'
                
        if (command == 'd' + "\n"):             # enable camera d
            ser.write('A')
            try:
                print 'command received to enable camera D, attempting to enable camera D'
                enable_camera_D()
                #time.sleep(2)
                print 'returned from enabling camera D'

            except:
                print 'Not done, need to implement catch condition for enable camera D'

    # -----  end of camera commands  -----------------

        # Command T: Time Sync
        if (command == 'T'):
            ser.write('A')
            try:
                print "Time Sync Request Recieved"
                
                timeval=str(datetime.datetime.now().strftime("%m/%d/%Y %H:%M:%S"))+"\n"     # Send the data time down to the ground station
                for x in timeval:
                    ser.write(x)
            except:
                print "error with time sync"

        # Command G: Send GPS Update
        if (command == 'G'):
            ser.write('A')
            ser.flushOutput()
            ser.flushInput()
            print "GPS Request Recieved"
            ardSer.write("G")           # Prep the arduino to send the GPS update to the Pi
            ardLine = ardSer.readline()     # Read the GPS update
            ser.write(ardLine)          # Send the GPS Update
            print(ardLine)

        if (command == 'P'):
            try:
                print "test"
                termtime = time.time() + 10
                pingread = ser.read()
                while ((pingread != 'D') &(pingread != "") & (termtime > time.time())):     # Look for the stop character D, no new info, or too much time passing
                    if (pingread == 'P'):       # Whenever you get the P, send one back and get ready for another
                        print "Ping Received"
                        ser.flushInput()
                        ser.write('P')
                    else:                       # If you don't get the P, sne back an A instead
                        print "pingread = ",pingread
                        ser.flushInput()
                        ser.write('A')
                    pingread = ser.read()       # Read the next character
                    sys.stdin.flush()
            except:
                print "Ping Runtime Error"
        
        
        if (checkpoint < time.time()):          # If the checkpoint is less than the time, take a picture
            #UpdateDisplay()
            try:
                camera = picamera.PiCamera()
                # Get the camera settings
                file = open(folder+"camerasettings.txt","r")
                width = int(file.readline())
                height = int(file.readline())
                sharpness = int(file.readline())
                brightness = int(file.readline())
                contrast = int(file.readline())
                saturation = int(file.readline())
                iso = int(file.readline())
                file.close()
                print "Camera Settings Read"
                
            except:
                print "cannot open file/file does not exist"
                reset_cam()     # Reset the camera if there's an issue
                
            try:
                # Setup the camera with the settings read previously
                camera.sharpness = sharpness
                camera.brightness = brightness
                camera.contrast = contrast
                camera.saturation = saturation
                camera.iso = iso
                #camera.annotate_text = "Image:" + str(imagenumber)
                camera.resolution = (2592,1944)             # Default max resolution photo
                extension = '.png'
                camera.hflip = cam_hflip
                camera.vflip = cam_vflip
        ##        camera.annotate_background = picamera.Color('black')
        ##        camera.annotate_text = camera_annotation
                #camera.start_preview()
                #smile()
                camera.capture(folder+"%s%04d%s" %("image",imagenumber,"_a"+extension))     # Take the higher resolution picture
                print "( 2592 , 1944 ) photo saved"
                #UpdateDisplay()
                fh = open(folder+"imagedata.txt","a")
                fh.write("%s%04d%s @ time(%s) settings(w=%d,h=%d,sh=%d,b=%d,c=%d,sa=%d,i=%d)\n" % ("image",imagenumber,"_a"+extension,str(datetime.datetime.now().strftime("%m/%d/%Y %H:%M:%S")),2592,1944,sharpness,brightness,contrast,saturation,iso))       # Add it to imagedata.txt
                camera.resolution = (width,height)          # Switch the resolution to the one set by the ground station
                extension = '.jpg'
                camera.hflip = cam_hflip
                camera.vflip = cam_vflip
        ##        camera.annotate_text = camera_annotation
                #smile()
                camera.capture(folder+"%s%04d%s" %("image",imagenumber,"_b"+extension))     # Take the lower resolution picture
                print "(",width,",",height,") photo saved"
                #UpdateDisplay()
                fh.write("%s%04d%s @ time(%s) settings(w=%d,h=%d,sh=%d,b=%d,c=%d,sa=%d,i=%d)\n" % ("image",imagenumber,"_b"+extension,str(datetime.datetime.now().strftime("%m/%d/%Y %H:%M:%S")),width,height,sharpness,brightness,contrast,saturation,iso))       # Add it to imagedata.txt
                print "settings file updated"
                #camera.stop_preview()
                camera.close()
                #print "camera closed"
                recentimg = "%s%04d%s" %("image",imagenumber,"_b"+extension)            # Make this photo the most recent image taken
                #print "resent image variable updated"
                fh.close()
                #print "settings file closed"
                print "Most Recent Image Saved as", recentimg
                imagenumber += 1
                checkpoint = time.time() + pic_interval         # Reset the checkpoint so it will be another minute before the next picture
            except:                                         # If there's any errors while taking the picture, reset the checkpoint
                print("Error taking picture")
                checkpoint = time.time() + pic_interval

    ##    xbee.write(command)
    ##    xLine = xbee.readline()
    ##    print "XBee: " + xLine
    ##    ser.write(xLine)
                
        xbeeToSend.append(command)      # Adds the command to the xbee send list so the xbee thread can send it out      
        if command == '':       # If no command was received, get a GPS update and send it out
            ardSer.write("G")
            gpsStr = "GPS:"+ardSer.readline()
            ser.write(gpsStr)
        for each in xbeeReceived:       # Send out everything that the xbee received since the last loop
            ser.write(each)
        xbeeReceived = []           # Clear the xbee list after sending everything
        if resetFlag == True:       # This is here to ensure that the xbee loop keeps running, if it crashes for any reason, this will restart it
            sideThread.start()
            resetFlag = False
        
        ser.flushInput()            # Clear the input buffer so we're ready for a new command to be received
    ##    ser.flushOutput()
        #time.sleep(.2)
        #print command
    except KeyboardInterrupt:
        completeExit = True
        quit()
