"""The Rainforest EMU2 TCP Integration."""
import asyncio
import logging
import threading
import socket, time
from datetime import timedelta
from typing import Optional
from threading import Thread
import voluptuous as vol
import homeassistant.helpers.config_validation as cv
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, CONF_HOST, CONF_PORT, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.core import callback
from homeassistant.helpers.event import async_track_time_interval
import sys, os
from .const import (
    DOMAIN,
    DEFAULT_NAME,
)

_LOGGER = logging.getLogger(__name__)

RAINFOREST_EMU2_TCP_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_PORT): cv.string,
    }
)

CONFIG_SCHEMA = vol.Schema(
    {DOMAIN: vol.Schema({cv.slug: RAINFOREST_EMU2_TCP_SCHEMA})}, extra=vol.ALLOW_EXTRA
)

PLATFORMS = ["sensor"]


async def async_setup(hass, config):
    """Set up the Solaredge modbus component."""
    hass.data[DOMAIN] = {}
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Rainforest Eagle from a config entry."""
    host = entry.data[CONF_HOST]
    name = entry.data[CONF_NAME]
    port = entry.data[CONF_PORT]
    
    #_LOGGER.debug("2 async_setup_entry host %s name %s  port %s DOMAIN %s ", host, name, port, DOMAIN) 
    
    hub = EMU2TCPHub(
        hass, name, host, port
    )
    """Register the hub."""
    hass.data[DOMAIN][name] = {"hub": hub}

    #hass.config_entries.async_setup_platforms(entry, PLATFORMS)
    
    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in PLATFORMS
            ]
        )
    )
    if not unload_ok:
        return False

    hass.data[DOMAIN].pop(entry.data["name"])
    return True


class EMU2TCPHub:
    """TODO."""

    def __init__(
        self,
        hass,
        name,
        host,
        port,
    ):
        """Initialize the Modbus hub."""
        #_LOGGER.debug("4 EMU2TCPHub host %s name %s  port %s ", host, name, port) 
        self._test = 0
        self._hass = hass
        self._lock = threading.Lock()
        self._name = name
        self._sensors = []
        self.data = {}
        self.InstantaneousDemand = None
        self.CurrentSummationDelivered = None
        self.CurrentSummationReceived = None          
        self._reader = None
        self._serial_thread_isEnabled = True
        self._serial_thread = Thread(target = self.tcp_read, args = (host, port))
        self._serial_thread.name = "EMU2 TCP Reader Thread"
        self._serial_thread.start()
    
    @callback
    def async_add_emu2_sensor(self, sensor):
        """Listen for data updates."""
        self._sensors.append(sensor)

    @callback
    def async_remove_emu2_sensor(self, sensor):
        self._sensors.remove(sensor)
        if not self._sensors:
            """stop the interval timer upon removal of last sensor"""
            self._serial_thread_isEnabled = False
            if (self._reader != None):
                self._reader.close()
                self._reader = None
 
    @property
    def name(self):
        """Return the name of this hub."""
        return self._name
        
    def test(self, var):
        if (var == "EMU2:InstantaneousDemand"):
            return self.InstantaneousDemand
        if (var == "EMU2:CurrentSummationDelivered"):
            return self.CurrentSummationDelivered
        if (var == "EMU2:CurrentSummationReceived"):
            return self.CurrentSummationReceived            
        self._test += 1
        return self._test
        
    def available(self):
        if (self._reader == None):
            return False
        return True
        
        
    def connectx(self, hostINx, portINx):
        _LOGGER.debug("Connecting")    
        if self._reader != None:
            self._reader.close()
        self._reader = None
        while self._reader == None:
            try:
                result = socket.gethostbyname(hostINx)
                _LOGGER.debug("Attempting to connect %s %s", hostINx, result)
                self._reader = socket.create_connection((result, portINx), 20.0)
            except socket.error as msg:
                self._reader = None
                _LOGGER.error("Failed to open %s %s. Retrying in 5s... %s", hostINx, portINx, msg)
                time.sleep(30.0)
        self.firstrun = False
        _LOGGER.debug("Begining Loop")
        
    def tcp_read(self, hostIN, portIN):
        _LOGGER.debug("Thread Starting %s %s", hostIN, portIN)
        import xml.etree.ElementTree as xmlDecoder
        self.connectx(hostIN, portIN) 
        msgStr = ""        
        while self._serial_thread_isEnabled:
            try:
                #_LOGGER.debug("presleep ")
                time.sleep(0.01)
                #_LOGGER.debug("Pre RX")
                self.state = "Recv"
                recv = self._reader.recv(16384).decode()
                if  (recv == None) or (recv == []): 
                    _LOGGER.warning(" Recv Failed or timed out")
                    self.connectx(hostIN, portIN) 
                    continue
                #_LOGGER.debug(" recv %s ", recv)
                msgStr = msgStr + recv
                #_LOGGER.debug(" msgStr %s ", msgStr)
                #Decide if we have enough to start processing
                msgtype = 0
                start = -1
                secondStart = 999999
                test = msgStr.find("<InstantaneousDemand>")
                if (test >=0):
                    start = test
                    msgtype = 1
                test = msgStr.find("<CurrentSummationDelivered>")
                if (test >=0):
                    if (msgtype > 0) and (test < start):
                        #Message type 2  found before type 1
                        secondStart = start
                        start = test
                        msgtype = 2
                    elif (msgtype > 0):
                        #message type 2 found after message type 1
                        secondStart = test
                    else:
                        #no message type 1 found
                        start = test
                        msgtype = 2
                test = msgStr.find("<PriceCluster>")
                if (test >=0) and (msgtype > 0) and (test < start):
                    if (msgtype > 0) and (test < start):
                        #Message type 3 also found before type 2 or 1
                        secondStart = start
                        start = test
                        msgtype = 3
                    elif (msgtype > 0):
                        #message type 2 found after message type 1
                        if (secondStart > test):
                            secondStart = test
                    else:
                        #no message type 2 or 1 found, but found type 3
                        start = test
                        msgtype = 3                
                if msgtype == 0:
                    #No start of message received yet, keep getting data
                    continue
                #found a message start, trim to first found valid tag start
                msgStr = msgStr[start:]
                secondStart = secondStart - start
                #find the end of the message
                end = 999999
                msgtyperx = 0
                test = msgStr.find("</InstantaneousDemand>")
                if test >= 0 and test < end:
                    msgtyperx = 1
                    end = test
                test = msgStr.find("</CurrentSummationDelivered>")
                if test >= 0 and test < end:
                    msgtyperx = 2
                    end = test
                test = msgStr.find("</PriceCluster>")
                if test >= 0 and test < end:
                    msgtyperx = 3
                    end = test
                #check if we have an end
                if msgtyperx == 0:
                    # have not received end yet
                    continue
                #check if the end does not match the begining
                if (msgtyperx != msgtype):
                    if self.firstrun:
                        _LOGGER.warning("partial message dropped %s", msgStr[:secondStart])
                    self.firstrun = True
                    msgStr = msgStr[secondStart:]
                    continue
                #grab the message to be decoded
                if msgtype == 1:
                    end += len("</InstantaneousDemand>")
                elif msgtype == 2:
                    end += len("</CurrentSummationDelivered>")
                elif msgtype == 3:
                    end += len("</PriceCluster>")
                procMsg = msgStr[start:end]
                #save the rest for next loop
                msgStr = msgStr[end:]
                #go ahead and try and decode the message
                try:
                    xmlTree = xmlDecoder.fromstring(procMsg)
                except Exception as e:
                    if self.firstrun:
                        _LOGGER.warning("xmlDecoder Exception %s", e)
                    self.firstrun = True
                    continue
                #_LOGGER.debug("xmlTree Tag %s", xmlTree.tag )
                if xmlTree.tag == 'InstantaneousDemand':
                    demand = int(xmlTree.find('Demand').text, 16)
                    demand = -(demand & 0x80000000) | (demand & 0x7fffffff)
                    multiplier = int(xmlTree.find('Multiplier').text, 16)
                    divisor = int(xmlTree.find('Divisor').text, 16)
                    digitsRight = int(xmlTree.find('DigitsRight').text, 16)
                    if(divisor != 0):
                        self.InstantaneousDemand = round(((demand * multiplier) / divisor), digitsRight)
                        _LOGGER.debug("InstantaneousDemand: %s", self.InstantaneousDemand)
                        for sensor in self._sensors:
                            if (sensor.entity_description.key == "EMU2:InstantaneousDemand"):
                                sensor._data_updated()
                        #self.async_schedule_update_ha_state()  
                    else: 
                        _LOGGER.warning("divisor ==0")  
                    #self._data[ATTR_DEVICE_MAC_ID] = xmlTree.find('DeviceMacId').text
                    #self._data[ATTR_METER_MAC_ID] = xmlTree.find('MeterMacId').text               
                elif xmlTree.tag == 'PriceCluster':
                    #priceRaw = int(xmlTree.find('Price').text, 16)
                    #trailingDigits = int(xmlTree.find('TrailingDigits').text, 16)
                    #self._data[ATTR_PRICE] = priceRaw / pow(10, trailingDigits)
                    #self._data[ATTR_TIER] = int(xmlTree.find('Tier').text, 16)                          
                    _LOGGER.error("PriceCluster Found but not Used")
                elif xmlTree.tag == 'CurrentSummationDelivered':
                    delivered = int(xmlTree.find('SummationDelivered').text, 16)
                    delivered *= int(xmlTree.find('Multiplier').text, 16)
                    delivered /= int(xmlTree.find('Divisor').text, 16)
                    self.CurrentSummationDelivered = delivered
                    _LOGGER.debug("_CurrentSummationDelivered: %s", self.CurrentSummationDelivered)   
                    received = int(xmlTree.find('SummationReceived').text, 16)
                    received *= int(xmlTree.find('Multiplier').text, 16)
                    received /= int(xmlTree.find('Divisor').text, 16)
                    self.CurrentSummationReceived = received
                    _LOGGER.debug("_CurrentSummationReceived: %s", self.CurrentSummationReceived)
                    for sensor in self._sensors:
                        if (sensor.entity_description.key == "EMU2:CurrentSummationDelivered"):
                            sensor._data_updated()
                        if (sensor.entity_description.key == "EMU2:CurrentSummationReceived"):
                            sensor._data_updated()
                else:
                    _LOGGER.warning("Unable to Decode Msg")
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                _LOGGER.error("191 Exception %s  %s %s %s", e, exc_type, fname, exc_tb.tb_lineno)
                time.sleep(30.0)
                self.connectx(hostIN, portIN)
        _LOGGER.error("Closing ")
        self._reader.close()
        self._reader = None