#!/usr/bin/python
# -*- coding: utf-8 -*-
# vim tabstop=4 expandtab shiftwidth=4 softtabstop=4

#
# stock-alert-bridge
#	Provides stock price information
#


__author__ = "Dennis Sell"
__copyright__ = "Copyright (C) Dennis Sell"


#TODO keep last price of day as previous close
#TODO Add in a time range for the market and only querry when open
#TODO need to add a begin and end date for each ticker, so that commodities can cycle thru


#import sys
import mosquitto
#import socket
import time
#import subprocess
import logging
import signal
import threading
from config import Config
import ystockquote


CLIENT_NAME = "ticker2mqtt"
CLIENT_VERSION = "0.6"
MQTT_TIMEOUT = 60	#seconds


#TODO might want to add a lock file
#TODO  need to deal with no config file existing!!!

#read in configuration file
f = file('.ticker2mqtt.conf')
cfg = Config(f)
MQTT_HOST = cfg.MQTT_HOST
MQTT_PORT = cfg.MQTT_PORT
CLIENT_TOPIC = cfg.CLIENT_TOPIC
BASE_TOPIC = cfg.BASE_TOPIC
STOCK_TICKERS = cfg.STOCK_TICKERS
INTERVAL = cfg.INTERVAL


mqtt_connected = 0

#TICKER = sys.argv[1]


#define what happens after connection
def on_connect(self, obj, rc):
	global mqtt_connected
	global running
	global alerts

	mqtt_connected = True
	print "MQTT Connected"
	mqttc.publish( CLIENT_TOPIC + "status" , "running", 1, 1 )
	mqttc.publish( CLIENT_TOPIC + "version", CLIENT_VERSION, 1, 1 )
	mqttc.subscribe( CLIENT_TOPIC + "ping", 2)


def do_stock_loop():
	global running
	global STOCK_TICKERS
	global mqttc

	while ( running ):
		if ( mqtt_connected ):
			for stock in STOCK_TICKERS:
				ticker = stock.ticker
		
				print "querrying for ", ticker
				mqttc.publish( BASE_TOPIC + "/" + ticker + "/name", stock.name, qos = 2, retain = 1 )

				price = ystockquote.get_price( ticker )
				mqttc.publish( BASE_TOPIC + "/" + ticker + "/price", price, qos = 2, retain = 1 )

				change = ystockquote.get_change( ticker )
				mqttc.publish( BASE_TOPIC + "/" + ticker + "/change", change, qos = 2, retain = 1 )

				volume = ystockquote.get_volume( ticker )
				mqttc.publish( BASE_TOPIC + "/" + ticker + "/volume", volume, qos = 2, retain = 1 )

				if ( stock.high_low ):
					yrhigh = ystockquote.get_52_week_high( ticker )
					mqttc.publish( BASE_TOPIC + "/" + ticker + "/yrhigh", yrhigh, qos = 2, retain = 1 )

					yrlow = ystockquote.get_52_week_low( ticker )
					mqttc.publish( BASE_TOPIC + "/" + ticker + "/yrlow", yrlow, qos = 2, retain = 1 )

				if ( stock.mavg ):
					avg50 = ystockquote.get_50day_moving_avg( ticker )
					mqttc.publish( BASE_TOPIC + "/" + ticker + "/50day-ma", avg50, qos = 2, retain = 1 )

					avg200 = ystockquote.get_200day_moving_avg( ticker )
					mqttc.publish( BASE_TOPIC + "/" + ticker + "/200day-ma", avg200, qos = 2, retain = 1 )

				mqttc.publish( BASE_TOPIC + "/" + ticker  + "/time", time.strftime( "%x %X" ), qos = 2, retain = 1 )
			if ( INTERVAL ):
				print "Waiting ", INTERVAL, " minutes for next update."
				time.sleep(60 * INTERVAL)
			else:
				running = False	#do a single shot
				print "Querries complete."
		pass


def on_message():
	if (( msg.topic == CLIENT_TOPIC + "ping" ) and ( msg.payload == "request" )):
		mqttc.publish( CLIENT_TOPIC + "ping", "response", qos = 1, retain = 0 )


def do_disconnect():
       global mqtt_connected
       mqttc.disconnect()
       mqtt_connected = False
       print "Disconnected"


def mqtt_disconnect():
	global mqtt_connected
	print "Disconnecting..."
	mqttc.disconnect()
	if ( mqtt_connected ):
		mqtt_connected = False 
		print "MQTT Disconnected"


def mqtt_connect():

	rc = 1
	while ( rc ):
		print "Attempting connection..."
		mqttc.will_set(CLIENT_TOPIC + "status", "disconnected_", 1, 1)

		#define the mqtt callbacks
		mqttc.on_message = on_message
		mqttc.on_connect = on_connect
#		mqttc.on_disconnect = on_disconnect

		#connect
		rc = mqttc.connect( MQTT_HOST, MQTT_PORT, MQTT_TIMEOUT )
		if rc != 0:
			logging.info( "Connection failed with error code $s, Retrying in 30 seconds.", rc )
			print "Connection failed with error code ", rc, ", Retrying in 30 seconds." 
			time.sleep(30)
		else:
			print "Connect initiated OK"


def cleanup(signum, frame):
	mqtt_disconnect()
	sys.exit(signum)


#create a client
mqttc = mosquitto.Mosquitto( CLIENT_NAME ) 

#trap kill signals including control-c
signal.signal(signal.SIGTERM, cleanup)
signal.signal(signal.SIGINT, cleanup)

running = True

t = threading.Thread(target=do_stock_loop)
t.start()


def main_loop():
	global mqtt_connected
	mqttc.loop(10)
	while running:
		if ( mqtt_connected ):
			rc = mqttc.loop(10)
			if rc != 0:	
				mqtt_disconnect()
				print rc
				print "Stalling for 20 seconds to allow broker connection to time out."
				time.sleep(20)
				mqtt_connect()
				mqttc.loop(10)
		pass


mqtt_connect()
main_loop()









