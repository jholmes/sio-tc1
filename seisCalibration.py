#!/usr/bin/env python
# -*- coding: utf-8 -*-

import serial, sys, time, os.path, datetime
from time import strftime
import numpy as np
import ConfigParser as cp

def printStats(alldata, alladj, counts, etime):
    numsam = len(alldata)
    (numpos, numneg, numzer) = counts
    pospct = (numpos/(numsam-numzer))*100
    negpct = (numneg/(numsam-numzer))*100
    zerpct = (numzer/numsam)*100
    print("\n-----------------------------------------------------------------------------")
    print "Running time seconds: %d" % etime
    print "# of samples: %d" % numsam
    print "    Max/Adjusted max: %d / %d"  % (np.amax(alldata),np.amax(alladj))
    print "    Min/Adjusted min: %d / %d"  % (np.amin(alldata),np.amin(alladj))
    print "    Avg/Adjusted avg: %d / %d"  % (np.mean(alldata),np.mean(alladj))
    print "    # of positive: %d (%.2f%%)" % (numpos,pospct)
    print "    # of negative: %d (%.2f%%)" % (numneg,negpct)
    print "    # of zeroes: %d (%.2f%%)"   % (numzer,zerpct)
    print "System check completed."

def msg(txt):
    sys.stdout.write(txt)
    sys.stdout.flush()

def main():
    # Check if the data logger is running. If so, stop.
    # We can't risk locking out the serial port from the data logger.
    
    if os.path.exists('/srv/tc1/run/seis_data_logger.pid'):
        print "Error: Data Logger is already running! Exiting..."
        exit(0)
    
    alldata = []
    alladj  = []
    numpos  = 0
    numneg  = 0
    numzer  = 0
    
    config = cp.RawConfigParser()
    config.read("/srv/tc1/conf/datalogger.props.cfg")
    
    port   = config.get     ("connection", "port")
    baud   = config.getint  ("connection", "baudrate")
    tout   = config.getfloat("connection", "timeout")
    offset = config.getint  ("calibration","offset")
    limit  = config.getint  ("calibration","samplelimit")
    model  = config.get     ("device",     "model")
    srate  = config.getfloat("device",     "samplerate")
    
    ttlsec = limit / srate
    m, s   = divmod(ttlsec, 60)
    h, m   = divmod(m, 60)
    now    = datetime.datetime.now()
    ftime  = now + datetime.timedelta(hours=h, minutes=m, seconds=s)
    (fhr,fmn,fsc) = (ftime.time().hour,ftime.time().minute,ftime.time().second)
    
    print("SIO Seismic Calibration Tool, v1.0")
    print("* Initialized on " + strftime('%x at %X %Z'))
    print("* Device info: model %s on %s (%d Hz transmission rate)" % (model, port, baud))
    print("* Using offset: %d" % offset)
    print("* Sample limit: %d (approx. %d:%02d:%02d, finish at %d:%02d:%02d)" % (limit,h,m,s,fhr,fmn,fsc))
    print("-----------------------------------------------------------------------------")
    print(" Sample Count | Sample Rate | Original Value | Adjusted Value | Current Mean ")
    
    device = serial.Serial(port,baud,timeout=tout)
    stime = time.time()
    try:
        sampcount = 0
        runcount  = 0
        curtotl   = 0
        while len(alldata) < limit:
            sproctime = time.time()
            data = device.readline()[:-2]
            sampcount = sampcount + 1
            if data:
                eproctime = time.time()
    
                try:
                    rawdata = int(data)
                    runcount = runcount + 1
                    alldata.append(rawdata)
                    adjdata = rawdata - offset
                    alladj.append(adjdata)
                    curtotl = curtotl + rawdata
                    curmean = int(curtotl / runcount)
                    if adjdata > 0:
                        numpos = numpos + 1
                    elif adjdata < 0:
                        numneg = numneg + 1
                    else:
                        numzer = numzer + 1
                            
                    samprate = sampcount / (eproctime - sproctime)
                                        
                    m = "{3:^13d} | {2:^11.2f} | {1:^14d} | {0:^14d} | {4:^14d}".format(adjdata,rawdata,samprate,runcount,curmean)
                    msg(m + chr(13))            
                except ValueError:
                    continue
                sampcount = 0
    except KeyboardInterrupt:
        etime = time.time()
        elapsed = etime - stime
        counts = (float(numpos),float(numneg),float(numzer))
        printStats(alldata, alladj, counts, elapsed)
        exit()
    etime = time.time()
    elapsed = etime - stime
    counts = (float(numpos),float(numneg),float(numzer))
    printStats(alldata, alladj, counts, elapsed)
    
if __name__ == '__main__':
    main()