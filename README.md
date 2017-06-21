# Still-Images-and-Command-Relay-for-Raspberry-Pi
By Austin Langford, based on work from MSU-BOREALIS


Python code for the Raspberry Pi that uses an RFD900+ radio to receive information from a ground station,
 and relay it through the xbee radio to other nearby payloads. Also has the ability to take and transmit images.

All of the RFD_python_Pi files are historical versions that were used at various stages through the summer of 2016,
 and are not intended for use.

The Still_Images_and_Command_Relay.py program is a multithreaded program that received commands from the
 [RFD900+ radio](http://store.rfdesign.com.au/rfd-900p-modem/). It handles raw GPS input, allowing for a GPS
 such as the [Adafruit GPS](https://www.adafruit.com/product/746) module to be directly connected to the Pi via a 
 serial converter. Picture taking is also handled in a side thread, so communication can happen even while a picture
 is being taken. The xbee send and receive are handled in separate threads so they occur simultaneously.

The Still_Images_and_Command_Relay_usbRadio.py program is the same as the above mentioned, however it allows the
 radio to be connected through a serial converter over USB, rather than through the Pis uart.
 (The raspberry pi UART is more difficult to work with on a Raspberry Pi 3). 

The Still_Images_and_Command_Relay_classFlight.py program is a based on Still_Images_and_Command_Relay_usbRadio,
 with added GPIO features such as a blinking LED and a push button. It was created for a Freshmen cubesat class,
 and is a good resource for examples of integrating GPIO features into this software.

The uBlox_Relay.py program is identical to the usbRadio one, but includes additional code for calibrating a
 [u-Blox](https://www.u-blox.com/en/standard-precision-gnss-modules) family gps unit for high-altitude use.

## Using this code:
Load the chosen program onto a raspberry pi, and set it to run on startup by editing the crontab. Connect the RFD900
 to either the Rx and Tx pins or through USB, connect the [xbee through USB](https://www.sparkfun.com/products/11697),
 and the GPS through USB.
 
## Converting from the Montana Still Image System
This Still Image and Relay system uses all of the same components (Raspberry Pi, Power Board, etc.) as the
 Still Image system distributed by the Montana Space Grant. Using all the features of our relay system will require
 several additional components.
 
* 1 GPS unit of user's choice. The following units have been or are being tested for use with this system:
	* Adafruit Ultimate GPS - Easy plug-and-play module, but can sometimes have issues with high altitudes
	* u-Blox NEO-6M - Great high-altitude module, but requires special calibration step when powered on
	* Copernicus II - Also good for high altitude, but difficult first-time setup and requires external antenna
* 1 USB to TTL serial converter cable to connect the GPS to the Raspberry Pi.
* 1 Series 1 xbee with USB explorer, allowing additional payloads to communicate with the Relay and in turn, with
	the ground station.

In addition, the following components are also recommended, but not necessary.

* 1 additional USB to TTL serial converter to connect the RFD900 to the Raspberry Pi. **Important:** Only connect
	the communication pins (RX and TX) to the RFD. Power for the RFD should still come directly from the Power Board,
	as it draws more power than the USB port can support.
* 1 USB to micro-USB connector for powering the Raspberry Pi. Although the Pi can be powered directly through pins,
	the micro-USB port has extra protection in place against improper power input.

Users will also need to install our version of the [Ground Station Software](https://github.com/MNSGC-Ballooning/Antenna-Tracker-and-RFD-Controls-GUI),
 as Montana's AntennaTracker is not completely compatible with this payload (sorry...).

For more information and detailed setup instructions, consult our [Still Image Relay Conversion Guide](https://docs.google.com/document/d/13WaC4CmkZhawQQ4u93gT95UDGDIEdv2z2k1gTSNnGMk/edit?usp=sharing).