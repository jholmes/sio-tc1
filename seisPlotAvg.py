#!/usr/bin/env python
# -*- coding: utf-8 -*-
 
import serial, argparse
import numpy as np
from collections import deque
import ConfigParser as cp
import matplotlib.pyplot as plt 
import matplotlib.animation as animation
 
    
# plot class
class AnalogPlot:
    # constr
    def __init__(self, strPort, maxLen):
        # open serial port
        self.ser = serial.Serial(strPort, 9600, timeout=.1)
        
        self.ax = deque([0.0]*maxLen)
        self.ay = deque([0.0]*maxLen)
        self.maxLen = maxLen
        
        config = cp.RawConfigParser()
        config.read("/srv/tc1/conf/datalogger.props.cfg")
        self.offset = config.getint("calibration","offset")
        
        self.dataArr = np.array([])
        self.sec = 0
      
    # add to buffer
    def addToBuf(self, buf, val):
        if len(buf) < self.maxLen:
            buf.append(val)
        else:
            buf.pop()
            buf.appendleft(val)
 
    # add data
    def add(self, data):
        assert(len(data) == 2)
        self.addToBuf(self.ax, data[0])
        self.addToBuf(self.ay, data[1])
 
    # update plot
    def update(self, frameNum, a0, a1):
        try:
            line = self.ser.readline()
            try:
                datapt = float(line)
                #datapt = datapt - 33487
                if (datapt > (self.offset * 2) or datapt < (self.offset / 2)):
                    return self.offset
                self.dataArr = np.append(self.dataArr, datapt)
                self.sec = self.sec + 1
                data = [self.sec, self.dataArr.mean()]
                # print data
                self.add(data)
                print "x: %d y: %d val: %d" % (data[0], data[1], datapt)
                a0.set_data(range(self.maxLen), self.ax)
                a1.set_data(range(self.maxLen), self.ay)
            except ValueError:
                pass
        except KeyboardInterrupt:
            print('exiting')
      
        return a0, 
 
    # clean up
    def close(self):
        # close serial
        self.ser.flush()
        self.ser.close()    
 
# main() function
def main():
    config = cp.RawConfigParser()
    config.read("/srv/tc1/conf/datalogger.props.cfg")
    offset = config.getint("calibration","offset")
    
    strPort = '/dev/ttyACM0'
    
    print('reading from serial port %s...' % strPort)
    
    # plot parameters
    analogPlot = AnalogPlot(strPort, 100)
    
    print('plotting data...')
    # set up animation
    fig = plt.figure()
    ax = plt.axes(xlim=(0, 100), ylim=(offset-10, offset+10))
    a0, = ax.plot([], [])
    a1, = ax.plot([], [])
    anim = animation.FuncAnimation(fig, analogPlot.update, 
                                   fargs=(a0, a1), 
                                   interval=10)
    
    # show plot
    plt.show()
    
    # clean up
    analogPlot.close()
 
    print('exiting.')
  
 
# call main
if __name__ == '__main__':
    main()