# Xbee-Relay-and-Still-Images-for-Raspberry-Pi
By Austin Langford, based on work from MSU-BOREALIS


Python code for the Raspberry Pi that uses an RFD900+ radio to receive information from a ground station, and relay it through the xbee radio to other nearby payloads. Also has the ability to take and transmit images

The commandReady file is a multithreaded application for the raspberry pi that takes input from the [RFD900+ radio](http://store.rfdesign.com.au/rfd-900p-modem/). If it is a recognized single byte command, the Pi will enter the correct state for communicating with the ground station for picture transmission or picture settings changes. Requires the arduino to output the GPS coordinates in a specific format.

If it is not a recognized single byte command, the information is sent directly through the xbee radio to other nearby receiving units.

The Still Images and Command Relay file takes advantage of the python multiprocessing library to handle the xbee, gps, and mainloop simultaneously. Set up the same way as the commandReady program, but takes raw GPS instead.

## Using this code:
Load this code onto a raspberry pi, and set it to run on startup by editting the crontab. Connect the RFD900 to the Rx and Tx pins, connect the xbee through USB, and the arduino through USB.

[You will need to set the device names of the xbee and the arduino to "xbee" and "arduino" respectively](http://unix.stackexchange.com/questions/66901/how-to-bind-usb-device-under-a-static-name)
