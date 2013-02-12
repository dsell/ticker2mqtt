#!/usr/bin/python
# -*- coding: utf-8 -*-
# vim tabstop=4 expandtab shiftwidth=4 softtabstop=4

#
# stock-alert-bridge
#	Provides stock price information
#


__author__ = "Dennis Sell"
__copyright__ = "Copyright (C) Dennis Sell"


APPNAME = "ticker2mqtt"
VERSION = "0.8"
WATCHTOPIC = "/raw/" + APPNAME + "/command"


import threading
from weatheralerts import nws
import time
import subprocess
from daemon import Daemon
from mqttcore import MQTTClientCore
from mqttcore import main
import time
import datetime
import ystockquote

class MyMQTTClientCore(MQTTClientCore):
    def __init__(self, appname, clienttype):
        MQTTClientCore.__init__(self, appname, clienttype)
        self.clientversion = VERSION
        self.tickerlist = self.cfg.STOCK_TICKERS
        self.interval = self.cfg.INTERVAL
        self.basetopic = self.cfg.BASE_TOPIC
        self.stocktickers = self.cfg.STOCK_TICKERS
        self.openhour = self.cfg.OPEN_TIME_HOUR
        self.openmin = self.cfg.OPEN_TIME_MIN
        self.closehour = self.cfg.CLOSE_TIME_HOUR
        self.closemin = self.cfg.CLOSE_TIME_MIN
        self.tradingdow = self.cfg.TRADING_DOW


        t = threading.Thread(target=self.do_thread_loop)
        t.start()

    def do_thread_loop(self):
        while ( self.running ):
		    if ( self.mqtt_connected ):
			    for stock in self.tickerlist:
				    ticker = stock.ticker
				    print "querrying for ", ticker
				    now = datetime.datetime.now()
				    open_time = now.replace( hour=self.openhour, minute=self.openmin, second=0 )
				    close_time = now.replace( hour=self.closehour, minute=self.closemin, second=0 )
				    open_day = False
				    for day in self.tradingdow:
					    if ( day == datetime.datetime.today().weekday() ):
						    open_day = True
				    if (( now > open_time) and ( now < close_time ) and open_day):
					    self.mqttc.publish( self.basetopic + "/" + ticker + "/name", stock.name, qos = 2, retain=True)
					    try:
						    price = ystockquote.get_price( ticker )
						    self.mqttc.publish( self.basetopic + "/" + ticker + "/price", price, qos = 2, retain=True)
#TODO add previous close value!!!!!!1
						    change = ystockquote.get_change( ticker )
						    self.mqttc.publish( self.basetopic + "/" + ticker + "/change", change, qos = 2, retain=True)

						    volume = ystockquote.get_volume( ticker )
						    self.mqttc.publish( self.basetopic + "/" + ticker + "/volume", volume, qos = 2, retain=True)

						    if ( stock.high_low ):
							    yrhigh = ystockquote.get_52_week_high( ticker )
							    self.mqttc.publish( self.basetopic + "/" + ticker + "/yrhigh", yrhigh, qos = 2, retain=True)

							    yrlow = ystockquote.get_52_week_low( ticker )
							    self.mqttc.publish( self.basetopic + "/" + ticker + "/yrlow", yrlow, qos = 2, retain=True)

						    if ( stock.mavg ):
							    avg50 = ystockquote.get_50day_moving_avg( ticker )
							    self.mqttc.publish( self.basetopic + "/" + ticker + "/50day-ma", avg50, qos = 2, retain=True)

							    avg200 = ystockquote.get_200day_moving_avg( ticker )
							    self.mqttc.publish( self.basetopic + "/" + ticker + "/200day-ma", avg200, qos = 2, retain=True)

						    self.mqttc.publish( self.basetopic + "/" + ticker  + "/time", time.strftime( "%x %X" ), qos = 2, retain=True)
					    except:
						    print "querry error in ystockquote."
				    else:
					    print "market closed"
			    if ( self.interval ):
				    print "Waiting ", self.interval, " minutes for next update."
				    time.sleep(60 * self.interval)
			    else:
				    self.running = False	#do a single shot
				    print "Querries complete."
		    pass



class MyDaemon(Daemon):
    def run(self):
        mqttcore = MyMQTTClientCore(APPNAME, clienttype="type1")
        mqttcore.main_loop()


if __name__ == "__main__":
    daemon = MyDaemon('/tmp/' + APPNAME + '.pid')
    main(daemon)
