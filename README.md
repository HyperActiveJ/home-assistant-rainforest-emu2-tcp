
Overview

![Untitled](https://user-images.githubusercontent.com/6298301/132909545-06cd73ec-42cf-4233-b32f-67c6f57e10b2.png)


Installation
1. Connect your Rainforest Automation EMU2 zibee energy monitor via USB to a computer on your LAN.
2. Using netcat (nc) or a similar tool, map /dev/by-serial/your_emu_device to a TCP port. Example below for typical raspberry pi (in my case an OranePiZero):
2a. sudo apt-get install ser2net
2b. sudo nano /etc/ser2.net.conf
2c. Add the line 9999:raw:0:/dev/ttyACM0:115200 8DATABITS NONE 1STOPBIT
2d. sudo service ser2net restart
4. Place the custom component in your home assistance instane at config\custom_components\
5. Restart homeassistant
6. Use the intergrations web interface to add the connection, entering the host name (or ip) of the remote (or loalhost) computer, and the port number asssigned (in this case 9999)


Reference Material
https://github.com/smakonin/RAEdataset/blob/master/EMU2_reader.py
https://github.com/home-assistant/home-assistant/blob/master/homeassistant/components/sensor/serial.py
https://home-assistant.io/components/sensor.date_countdown/
https://github.com/rainforestautomation/Emu-Serial-API

Thank you to to:
https://github.com/jrhorrisberger/home-assistant/tree/master/custom_components/rainforest


