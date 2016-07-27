import time, threading
from multiprocessing import Process, Queue, Value, Array, Manager
from time import strftime
import datetime
import io
import picamera
import serial
import sys
import os
import base64
import hashlib

class Unbuffered:
    def __init__(self,stream):
        self.stream = stream
    def write(self,data):
        self.stream.write(data)
        self.stream.flush()
        logfile.write(data)
        logfile.flush()

class CameraSettings:
	""" A class to handle camera settings """
	def __init__(self,width,height,sharpness,brightness,contrast,saturation,iso):
	    self.width = width
	    self.height = height
	    self.resolution = (width,height)
	    self.sharpness = sharpness
	    self.brightness = brightness
	    self.contrast = contrast
	    self.saturation = saturation
	    self.iso = iso
	    self.hflip = False
	    self.vflip = False

	def getWidth(self):
	    return self.width

	def getHeight(self):
	    return self.height

	def getResolution(self):
	    return self.resolution

	def getSharpness(self):
	    return self.sharpness

	def getBrightness(self):
	    return self.brightness

	def getContrast(self):
	    return self.contrast

	def getSaturation(self):
	    return self.saturation

	def getISO(self):
	    return self.iso

	def setCameraAnnotation(self,annotation):
	    self.annotation = annotation

	def getCameraAnnotation(self):
	    return self.annotation

	def getHFlip(self):
            return self.hflip

        def getVFlip(self):
            return self.vflip

	def toggleHorizontalFlip(self):
            if(self.hflip == False):
                    self.hflip = True
            else:
                    self.hflip = False
            return self.hflip

	def toggleVerticalFlip(self):
            if(self.vflip == False):
                    self.vflip = True
            else:
                    self.vflip = False
            return self.vflip

class main:
    def __init__(self):

        ### Check for, and create the folder ###
	self.folder = "/home/pi/RFD_Pi_Code/%s/" % strftime("%m%d%Y_%H%M%S")
	dir = os.path.dirname(self.folder)
	if not os.path.exists(dir):
	    os.mkdir(dir)

	### Serial Port Initializations ###
	#RFD900 Serial Variables
	self.rfdPort  = "/dev/ttyAMA0"
	self.rfdBaud = 38400
	self.rfdTimeout = 3
	self.ser = serial.Serial(port = self.rfdPort,baudrate = self.rfdBaud, timeout = self.rfdTimeout)

	# Arduino Serial Variables
	self.ardPort = "/dev/arduino"
	self.ardBaud = 115200
	self.ardTimeout = 3

	# XBee Serial Variables
	self.xPort = "/dev/xbee"
	self.xBaud = 9600
	self.xTimeout = 3

	self.piCommands = ['1','2','3','4','5','6','7','T','G','P']			# List of pi commands listened for
		
        ### Create the logfile ###
        self.logfile = open(self.folder+"piruntimedata.txt","w")
        self.logfile.close()
        self.logfile = open(self.folder+"piruntimedata.txt","a")
            
        fh = open(self.folder + "imagedata.txt","w")
        fh.write("")
        fh.close()

        ### Picture Variables ###
        self.wordlength = 7000
        self.imagenumber = 0
        self.recentimg = ""
        self.pic_interval = 60
        self.cameraSettings = CameraSettings(650,450,0,50,0,0,400)
        self.reset_cam()
        self.starttime = time.time()
        print "Started at @ ",datetime.datetime.now()
        self.checkpoint = time.time()

        ### Set up managers for the data being shared by the processes ###
        self.xDict = Manager().dict()
        self.gpsDict = Manager().dict()
        self.xDict['received'] = []
        self.xDict['toSend'] = []
        self.xDict['kill'] = False
        self.xDict['reset'] = False
        self.gpsDict['gps'] = []
        self.gpsDict['kill'] = False
        self.gpsDict['reset'] = False

        ### Create the side processes for the xBee and GPS ###
        self.xProc = Process(target = xbeeHandler, args = (self.xPort,self.xBaud,self.xTimeout,self.xDict))
        self.gpsProc = Process(target = gpsHandler, args = (self.ardPort,self.ardBaud,self.ardTimeout,self.gpsDict))
        self.xProc.daemon = True
        self.gpsProc.daemon = True
        self.xProc.start()
        self.gpsProc.start()
        
    def getArduinoCom(self):
        return [self.ardPort,self.ardBaud,self.ardTimeout]

    def getXbeeCom(self):
        return [self.xPort,self.xBaud,self.xTimeout]

    def getRFDCom(self):
        return [self.rfdPort,self.rfdBaud,self.rfdTimeout]

    def reset_cam(self):
        """ Resets the camera to the default settings """
        self.cameraSettings = CameraSettings(650,450,0,50,0,0,400)
        f = open(self.folder + "camerasettings.txt","w")
        f.write(str(self.cameraSettings.getWidth())+"\n")
        f.write(str(self.cameraSettings.getHeight())+"\n")
        f.write(str(self.cameraSettings.getSharpness())+"\n")
        f.write(str(self.cameraSettings.getBrightness())+"\n")
        f.write(str(self.cameraSettings.getContrast())+"\n")
        f.write(str(self.cameraSettings.getSaturation())+"\n")
        f.write(str(self.cameraSettings.getISO())+"\n")
        f.close()

    def image_to_b64(self,path):
        """ Converts an image to 64 bit encoding """
        with open(path,"rb") as imageFile:
            return base64.b64encode(imageFile.read())

    def b64_to_image(self,data,savepath):
        """ Converts a 64 bit encoding to an image """
        fl = open(savepath,"wb")
        fl.write(data.decode('base4'))
        fl.close()

    def gen_checksum(self,data,pos):
        """ Creates a checksum based on data """
        return hashlib.md5(data[pos:pos+self.wordlength]).hexdigest()

    def sendword(self,data,pos):
        """ Sends the appropriately sized piece of the total picture encoding """
        if(pos + self.wordlength < len(data)):       # Take a piece of size self.wordlength from the whole, and send it
            for x in range(pos, pos+self.wordlength):
                self.ser.write(data[x])
            return
        else:                                   # If the self.wordlength is greater than the amount remaining, send everything left
            for x in range(pos, len(data)):
                self.ser.write(data[x])
            return

    def sync(self):
        """ Synchronizes the data stream between the Pi and the ground station """
        synccheck = ''
        synctry = 5
        syncterm = time.time() + 10
        while((synccheck != 'S')&(syncterm > time.time())):
            self.ser.write("sync")
            synccheck = self.ser.read()
            if(synctry == 0):
                if (synccheck == ""):
                    print "SyncError"
                    break
            synctry -= 1
        time.sleep(0.5)
        return

    def send_image(self,exportpath):
        """ Sends the image through the RFD in increments of size self.wordlength """
        timecheck = time.time()
        done = False
        cur = 0
        trycnt = 0
        outbound = self.image_to_b64(exportpath)     # Determine where the encoded image is
        size = len(outbound)
        print size,": Image Size"
        print "photo request received"
        self.ser.write(str(size)+'\n')               # Send the total size so the ground station knows how big it will be
        while(cur < len(outbound)):
            print "Send Position:", cur," // Remaining:", int((size - cur)/1024), "kB"      # Print out how much picture is remaining in kilobytes
            checkours = self.gen_checksum(outbound,cur)      # Create the checksum to send for the ground station to compare to
            self.ser.write(checkours)
            self.sendword(outbound,cur)                      # Send a piece of size self.wordlength
            #UpdateDisplay()
            checkOK = self.ser.read()
            if (checkOK == 'Y'):                # This is based on whether or not the word was successfully received based on the checksums
                cur = cur + self.wordlength
                trycnt = 0
            else:
                if(trycnt < 5):                 # There are 5 tries to get the word through, each time you fail, drop the self.wordlength by 1000
                    if self.wordlength >1000:
                        self.wordlength -= 1000
                    self.sync()
                    trycnt += 1
                    print "try number:", trycnt
                    print "resending last @", cur
                    print "ours:",checkours
                    print "self.wordlength",self.wordlength
                else:
                    print "error out"
                    cur = len(outbound)
        print "Image Send Complete"
        print "Send Time =", (time.time() - timecheck)
        return

    def mostRecentImage(self):
        """ Command 1: Send most recent image """
        self.ser.write('A')      # Send the acknowledge
##        try:
        print "Send Image Command Received"
        #UpdateDisplay()
        #sync()
        print "Sending:", self.recentimg
        self.ser.write(self.recentimg)
        self.send_image(self.folder+self.recentimg)            # Send the most recent image
        self.wordlength = 7000                       # Reset the self.wordlength in case it was changed while sending
##        except:
##            print "Send Recent Image Error"

    def sendImageData(self):
    	""" Command 2: Sends imagedata.txt """
        self.ser.write('A')
        try:
            print "data list request recieved"
            #UpdateDisplay()
            #sync()
            f = open(self.folder+"imagedata.txt","r")
            print "Sending imagedata.txt"
            for line in f:
                self.ser.write(line)
                #print line
            f.close()
            time.sleep(1)
        except:
            print "Error with imagedata.txt read or send"

    def requestedImage(self):
    	""" Command 3: Sends the requested image """
        self.ser.write('A')
        try:
            print"specific photo request recieved"
            #UpdateDisplay()
            #sync()
            imagetosend = self.ser.read(15)                  # Determine which picture to send
            print(imagetosend)
            self.send_image(self.folder+imagetosend)
            self.wordlength = 7000
        except:
            print "Send Specific Image Error"

    def sendCameraSettings(self):
    	""" Command 4: Sends the camera settings """
        self.ser.write('A')
        try:
            print "Attempting to send camera settings"
            #UpdateDisplay()
            #sync()
            camFile = open(self.folder+"camerasettings.txt","r")        # Open the camera settings file
            temp = camFile.read()
            while(temp != ""):      # For every line in the file, send it to the RFD
                self.ser.write(temp)
                temp = camFile.read()
            self.ser.write("\r")
            camFile.close()
            print "Camera Settings Sent"
        except:
            print "cannot open file/file does not exist"
            self.reset_cam()         # If there's an issue with camerasettings.txt, reset it

    def getCameraSettings(self):
    	""" Updates the camera settings """
        self.ser.write('A')
        try:
            print "Attempting to update camera settings"
            #UpdateDisplay()
            file = open(self.folder+"camerasettings.txt","w")
            temp = self.ser.read()
            while(temp != ""):
                file.write(temp)
                temp = self.ser.read()
            file.close()
            print "New Camera Settings Received"
            self.ser.write('A')
            self.checkpoint = time.time()
        except:
            print "Error Retrieving Camera Settings"
            reset_cam

    def timeSync(self):
    	""" Sends the current time """
        self.ser.write('A')
        try:
            print "Time Sync Request Recieved"
            
            timeval=str(datetime.datetime.now().strftime("%m/%d/%Y %H:%M:%S"))+"\n"     # Send the data time down to the ground station
            for x in timeval:
                self.ser.write(x)
        except:
            print "error with time sync"

    def pingTest(self):
    	""" Connection test, test ping time """
        self.ser.write('A')
        print "Ping Request Received"
        #UpdateDisplay()
        try:
            print "test"
            termtime = time.time() + 10
            pingread = self.ser.read()
            while ((pingread != 'D') &(pingread != "") & (termtime > time.time())):     # Look for the stop character D, no new info, or too much time passing
                if (pingread == 'P'):       # Whenever you get the P, send one back and get ready for another
                    print "Ping Received"
                    self.ser.flushInput()
                    self.ser.write('P')
                else:                       # If you don't get the P, sne back an A instead
                    print "pingread = ",pingread
                    self.ser.flushInput()
                    self.ser.write('A')
                pingread = self.ser.read()       # Read the next character
                sys.stdin.flush()
        except:
            print "Ping Runtime Error"

    def sendPing(self):
        try:
            print "test"
            termtime = time.time() + 10
            pingread = self.ser.read()
            while ((pingread != 'D') &(pingread != "") & (termtime > time.time())):     # Look for the stop character D, no new info, or too much time passing
                if (pingread == 'P'):       # Whenever you get the P, send one back and get ready for another
                    print "Ping Received"
                    self.ser.flushInput()
                    self.ser.write('P')
                else:                       # If you don't get the P, sne back an A instead
                    print "pingread = ",pingread
                    self.ser.flushInput()
                    self.ser.write('A')
                pingread = self.ser.read()       # Read the next character
                sys.stdin.flush()
        except:
            print "Ping Runtime Error"

    def sendPiRuntime(self):
    	""" Sends the runtimedata """
        self.ser.write('A')
        try:
            print "Attempting to send piruntimedata"
            #UpdateDisplay()
            #sync()
            file = open(self.folder+"piruntimedata.txt","r")     # Open the runtimedata file
            temp = file.readline()
            while(temp != ""):      # Send everyting in the file until it's empty
                self.ser.write(temp)
                temp = file.readline()
            #ser.write("\r")
            file.close()
            print "piruntimedata.txt sent"
        except:
            print "error sending piruntimedata.txt"

    def takePicture(self):
    	""" Takes a picture at full resolution, and one at the selected resolution """
    	try:
            camera = picamera.PiCamera()
            # Get the camera settings
            f = open(self.folder+"camerasettings.txt","r")
            width = int(f.readline())
            height = int(f.readline())
            sharpness = int(f.readline())
            brightness = int(f.readline())
            contrast = int(f.readline())
            saturation = int(f.readline())
            iso = int(f.readline())
            f.close()
            print "Camera Settings Read"
            
        except:
            print "cannot open file/file does not exist"
            self.reset_cam()     # Reset the camera if there's an issue
            
        try:
            # Setup the camera with the settings read previously
            camera.sharpness = sharpness
            camera.brightness = brightness
            camera.contrast = contrast
            camera.saturation = saturation
            camera.iso = iso

            camera.resolution = (2592,1944)             # Default max resolution photo
            extension = '.png'
            camera.hflip = self.cameraSettings.getHFlip()
            camera.vflip = self.cameraSettings.getVFlip()

            camera.capture(self.folder+"%s%04d%s" %("image",self.imagenumber,"_a"+extension))     # Take the higher resolution picture
            print "( 2592 , 1944 ) photo saved"

            fh = open(self.folder+"imagedata.txt","a")
            fh.write("%s%04d%s @ time(%s) settings(w=%d,h=%d,sh=%d,b=%d,c=%d,sa=%d,i=%d)\n" % ("image",self.imagenumber,"_a"+extension,str(datetime.datetime.now().strftime("%m/%d/%Y %H:%M:%S")),2592,1944,sharpness,brightness,contrast,saturation,iso))       # Add it to imagedata.txt
            camera.resolution = (width,height)          # Switch the resolution to the one set by the ground station
            extension = '.jpg'

            camera.capture(self.folder+"%s%04d%s" %("image",self.imagenumber,"_b"+extension))     # Take the lower resolution picture
            print "(",width,",",height,") photo saved"
            fh.write("%s%04d%s @ time(%s) settings(w=%d,h=%d,sh=%d,b=%d,c=%d,sa=%d,i=%d)\n" % ("image",self.imagenumber,"_b"+extension,str(datetime.datetime.now().strftime("%m/%d/%Y %H:%M:%S")),width,height,sharpness,brightness,contrast,saturation,iso))       # Add it to imagedata.txt
            print "settings file updated"
            camera.close()
            self.recentimg = "%s%04d%s" %("image",self.imagenumber,"_b"+extension)            # Make this photo the most recent image taken
            fh.close()
            print "Most Recent Image Saved as", self.recentimg
            self.imagenumber += 1
            self.checkpoint = time.time() + self.pic_interval         # Reset the checkpoint so it will be another minute before the next picture
        except:                                         # If there's any errors while taking the picture, reset the checkpoint
            print("Error taking picture")
            self.checkpoint = time.time() + self.pic_interval

    def loop(self):
    	try:
            print("RT:",int(time.time() - self.starttime),"Watching Serial")
            timeCheck = time.time()
            command = ''
            done = False
            while((not done) and (time.time() - timeCheck) < 3):
                    newChar = self.ser.read()
                    if((newChar in self.piCommands) and (len(command) == 0)):
                            command = newChar
                            done = True
                    elif(newChar == "!"):
                            command += newChar
                            done = True
                    elif(newChar != ""):
                            command += newChar
                            timeCheck = time.time()

            if(command != ''):
                    print("Command: ",command)

            if(command == '1'):
                    self.mostRecentImage()
            elif(command == '2'):
                    self.sendImageData()
            elif(command == '3'):
                    self.requestedImage()
            elif(command == '4'):
                    self.sendCameraSettings()
            elif(command == '5'):
                    self.getCameraSettings()
            elif(command == '6'):
                    self.pingTest()
            elif(command == '7'):
                    self.sendPiRuntime()
            elif(command == 'T'):
                    self.timeSync()
            elif(command == 'P'):
                    self.sendPing()

            else:
                lst = self.xDict['toSend']
                lst.append(command)
                self.xDict['toSend'] = lst
                if command == '':       # If no command was received, get a GPS update and send it out
                    if(len(self.gpsDict['gps'])>0):
                        self.ser.write("GPS:"+self.gpsDict['gps'][-1])
                for each in self.xDict['received']:       # Send out everything that the xbee received since the last loop
                    self.ser.write(each)
                self.xDict['received'] = []           # Clear the xbee list after sending everything
                self.ser.flushInput()            # Clear the input buffer so we're ready for a new command to be received

            if(self.checkpoint < time.time()):
                self.takePicture()

            self.ser.flushInput()

            if(self.xDict['reset'] == True):
                self.xProc = Process(target = xbeeHandler, args = (self.xPort,self.xBaud,self.xTimeout,self.xDict))
                self.xDict['reset'] = False
                self.xProc.daemon = True
                self.xProc.start()

            if(self.gpsDict['reset'] == True):
                self.gpsProc = Process(target = gpsHandler, args = (self.ardPort,self.ardBaud,self.ardTimeout,self.gpsDict))
                self.gpsDict['reset'] = False
                self.gpsProc.daemon = True
                self.gpsProc.start()
                
        except KeyboardInterrupt:
                self.xDict['kill'] = True
                self.gpsDict['kill'] = True
                quit()

def xbeeHandler(xPort,xBaud,xTimeout,xDict):
    xbee = serial.Serial(port = xPort, baudrate = xBaud, timeout = xTimeout)      # Open the xbee port first thing
    while(not xDict['kill']):         # Run this code forever
        try:
            line = ''
            done = False
            timeCheck = time.time()
            while((not done) and (time.time() - timeCheck) < 1):
                newChar = xbee.read()
                print(newChar)
                if(newChar == "!"):
                    line += newChar
                    done = True
                elif(newChar != ""):
                    line += newChar
                    timeCheck = time.time()

            if line not in xDict['received']:        # We don't want to fill it with the same piece of data over and over again while we wait for the RFD to send it out
            	lst = xDict['received']
            	lst.append(line)
            	xDict['received'] = lst
            for each in xDict['toSend']:             # For everything added in the other thread, send them all out
                xbee.write(each)
            xDict['toSend'] = []                   # Clear the send list once everything is sent
        except:         # This catches unexpected errors in the thread, and makes sure that the thread will start up again next loop
            xDict['reset'] = True
            xbee.close()

def gpsHandler(ardPort,ardBaud,ardTimeout,gpsDict):
    ardSer = serial.Serial(port = ardPort, baudrate = ardBaud, timeout = ardTimeout)    # Open the xbee port first thing
    while(not gpsDict['kill']):         # Run this code forever
        try:
            line = ardSer.readline()
            if(line.find("GPGGA") != -1):
                prev = line[1].split('.')[0]
                line = line.split(',')
                hours = int(line[1][0:2])
                minutes = int(line[1][2:4])
                seconds = int(line[1][4:].split('.')[0])
                if(line[2] == ''):
                    lat = 0
                else:
                    lat = float(line[2][0:2]) + (float(line[2][3:]))/60
                if(line[3] == ''):
                    lon = 0
                else:
                    lon = float(line[4][0:3]) + (float(line[4][4:]))/60
                if(line[9] == ''):
                    alt = 0
                else:
                    alt = float(line[7])
                sat = int(line[7])
                gpsStr = str(hours)+','+ str(minutes)+','+ str(seconds)+','+ str(lat)+','+str(lon)+','+str(alt)+','+str(sat)+'!'+'\n'
                
                lst = gpsDict['gps']
                lst.append(gpsStr)
                gpsDict['gps'] = lst
        except:         # This catches unexpected errors in the thread, and makes sure that the thread will start up again next loop
            gpsDict['reset'] = True
            ardSer.close()

if __name__ == "__main__":
	##sys.stdout = Unbuffered(sys.stdout)
	mainLoop = main()
	while True:
		mainLoop.loop()

