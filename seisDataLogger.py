#!/usr/bin/env python
# -*- coding: utf-8 -*-

# seisDataLogger.py
# 
# Connects to educational seismometer and gathers data.
# Make save to current trace every user-defined interval of seconds
# Reads a config file for parameters, but runs as a process.
#

from obspy.core import Stream, Trace, UTCDateTime
from seisDataLoggerDaemon import Daemon
from threading import Thread
from time import strftime
import serial, sys, os
import numpy as np


class DataLoggerDaemon(Daemon):
    def run(self):        
        baseTime     = UTCDateTime()
        
        # Assign all the configuration variables
        port     = self.config.get     ("connection","port")
        baud     = self.config.getint  ("connection","baudrate")
        tout     = self.config.getfloat("connection","timeout")
        interval = self.config.getint  ("data","interval")
        offset   = self.config.getint  ("calibration","offset")
        network  = self.config.get     ("device","network")
        station  = self.config.get     ("device","station")
        location = self.config.get     ("device","location")
        channel  = self.config.get     ("device","channel")
        samprate = self.config.getfloat("device","samplerate")
        dataqual = self.config.get     ("device","dataquality")   
                       
        sampleIdx = 0
        traceData = np.array([])
            
        self.logger.debug("["+ strftime('%X') + "] connecting...")
        
        rawData = serial.Serial(port,baud,timeout=tout)

        self.logger.debug("["+ strftime('%X') + "] listening for incoming data...")
        
        while True: # While loop that loops forever
            while (rawData.inWaiting()==0): #Wait here until there is data
                pass #do nothing
                
            dataPointString = rawData.readline()
            
            try:
                traceData = np.append(traceData, int(dataPointString))
            except ValueError:
                offset = int(np.mean(traceData))
                self.logger.debug("["+ strftime('%X') + "] * Bad value received. Replacing with current mean...")
                traceData = np.append(traceData, offset)
            
            sampleIdx = sampleIdx + 1
            
            currentTime = UTCDateTime()
            elapsedTime = (currentTime - baseTime)
            
            # Write the data after x seconds
            if elapsedTime >= (interval + (baseTime.microsecond / 1e6)):
                # Fill header attributes
                stats = {'network':      network,
                        'station':       station,
                        'location':      location,
                        'channel':       channel,
                        'npts':          len(traceData),
                        'sampling_rate': samprate,
                        'mseed': {'dataquality': dataqual},
                        'starttime': baseTime}
                
                # Save the file using a different thread.
                worker = Thread(target=self._writeData, args=(traceData, stats, baseTime))
                worker.setDaemon(True)
                worker.start()
                                
                baseTime = currentTime
                
                sampleIdx = 0
    
                traceData = np.array([])

    def _writeData(self, traceData, stats, timeObj):
        streamObj = Stream([Trace(data=traceData, header=stats)])

        filename = self._prepareFilename(timeObj)
        offset = int(np.mean(streamObj.traces[0].data))
        streamObj.traces[0].data = np.array([x - offset for x in streamObj.traces[0].data])
        
        self.logger.debug("["+ strftime('%X') + "] Saving %d samples (corrected by %d) to %s..." % (len(traceData), offset, filename))
        streamObj.write(filename, format='MSEED')
        
    def _prepareFilename(self, timeObj):
        datapath = self.config.get("file","datapath")
        filepath = datapath +"%d/%d/" % (timeObj.year, timeObj.julday)
        
        try:
            if not os.path.exists(filepath):
                os.makedirs(filepath)
        except OSError as exception:
            self.logger.debug("["+ strftime('%X') + "] * Error preparing path: (%d) %s" % (exception.errno, exception.strerror))
        
        network = self.config.get("device","network")
        station = self.config.get("device","station")
        channel = self.config.get("device","channel")
        filename = network+"."+station+".%02d%02d%4d_%02d%02d%02d." % \
        (timeObj.day,timeObj.month,timeObj.year,
        timeObj.hour,timeObj.minute,timeObj.second) +channel+".mseed"
        return (filepath+filename)
    
    def normalize(v):
        norm=np.linalg.norm(v)
        if norm==0: 
            return v
        return v/norm
        
if __name__ == "__main__":
    daemon = DataLoggerDaemon('/srv/tc1/run/seis_data_logger.pid')
    if len(sys.argv) == 2:
        if 'start' == sys.argv[1]:
            daemon.start()
        elif 'stop' == sys.argv[1]:
            daemon.stop()
        elif 'restart' == sys.argv[1]:
            daemon.restart()
        else:
            print "Unknown command"
            sys.exit(2)
        sys.exit(0)
    else:
        print "usage: %s start|stop|restart" % sys.argv[0]
        sys.exit(2)