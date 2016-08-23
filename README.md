# Xbee-Relay-and-Still-Images-for-Raspberry-Pi
By Austin Langford, based on work from MSU-BOREALIS


Python code for the Raspberry Pi that uses an RFD900+ radio to receive information from a ground station, and relay it through the xbee radio to other nearby payloads. Also has the ability to take and transmit images

The Still Images and Command Relay file is a multithreaded program that received commands from the [RFD900+ radio](http://store.rfdesign.com.au/rfd-900p-modem/). It handles raw GPS input, allowing for a Adafruit GPS module to be directly connected to the Pi via a USB-to-TTL cable. Picture taking is also handled in a side thread, so communication can happen even while a picture is being taken. The xbee send and receive are handled in separate threads so they occur simultaneously.

## Using this code:
Load this code onto a raspberry pi, and set it to run on startup by editting the crontab. Connect the RFD900 to the Rx and Tx pins, connect the xbee through USB, and the arduino through USB.

[You will need to set the device names of the xbee and the arduino to "xbee" and "arduino" respectively](http://unix.stackexchange.com/questions/66901/how-to-bind-usb-device-under-a-static-name)
