# Xbee-Relay-and-Still-Images-for-Raspberry-Pi
Python code for the Raspberry Pi that uses an RFD900+ radio to receive information from a ground station, and relay it through the xbee radio to other nearby payloads. Also has the ability to take and transmit images

A multithreaded application for the raspberry pi that takes input from the [RFD900+ radio](http://store.rfdesign.com.au/rfd-900p-modem/). If it is a recognized single byte command, the Pi will enter the correct state for communicating with the ground station for picture transmission or picture settings changes.

If it is not a recognized single byte command, the information is sent directly through the xbee radio to other nearby receiving units.

## Using this code:
Load this code onto a raspberry pi, and set it to run on startup by editting the crontab. Connect the RFD900 to the Rx and Tx pins, connect the xbee through USB, and the arduino through USB.

[You will need to set the device names of the xbee and the arduino to "xbee" and "arduino" respectively](http://unix.stackexchange.com/questions/66901/how-to-bind-usb-device-under-a-static-name)
