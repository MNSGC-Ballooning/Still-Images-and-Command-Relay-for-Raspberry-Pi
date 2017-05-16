# Still-Images-and-Command-Relay-for-Raspberry-Pi
By Austin Langford, based on work from MSU-BOREALIS


Python code for the Raspberry Pi that uses an RFD900+ radio to receive information from a ground station, and relay it through the xbee radio to other nearby payloads. Also has the ability to take and transmit images

All of the RFD_python_Pi files are historical versions that were used at various stages through the summer of 2016, and are not intended for use.

The Still_Images_and_Command_Relay.py program is a multithreaded program that received commands from the [RFD900+ radio](http://store.rfdesign.com.au/rfd-900p-modem/). It handles raw GPS input, allowing for an GPS such as the [Adafruit GPS](https://www.adafruit.com/product/746) module to be directly connected to the Pi via a serial converter. Picture taking is also handled in a side thread, so communication can happen even while a picture is being taken. The xbee send and receive are handled in separate threads so they occur simultaneously.

The Still_Images_and_Command_Relay_usbRadio.py program is the same as the above mentioned, however it allows the radio to be connected through a serial converter over USB, rather than through the Pis uart (the raspberry pi UART is more difficult to work with on a Raspberry Pi 3).

The Still_Images_and_Command_Relay_classFlight.py program is a based on Still_Images_and_Command_Relay_usbRadio, with added GPIO features such as a blinking LED and a push button. It was created for a Freshmen cubesat class, and is a good resource for examples of integrating GPIO features into this software.

## Using this code:
Load the chosen program onto a raspberry pi, and set it to run on startup by editing the crontab. Connect the RFD900 to either the Rx and Tx pins or through USB, connect the [xbee through USB](https://www.sparkfun.com/products/11697), and the GPS through USB.
