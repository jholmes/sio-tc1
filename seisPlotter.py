#!/usr/bin/env python
# -*- coding: utf-8 -*-

# seisPlotter.py
# 
# Reads a bunch of seed files based on the time, and then displays a 12 hour
# helicorder plot ("dayplot").
#
# TODO:
# * Parse through the files on the server to make the dayplot
#       Put file in /srv/www/out
# * Generate a small XHTML page that can be imported containing:
#       Dayplot
#       List of Earthquakes in plot
#           "MXX LOCATION (XX km depth), Dist from receiver: XX km"
#           link location to USGS page (in feature['properties']['url']
#           or "No Earthquakes currently displayed"
#
import sys
from time import strftime, time, localtime

start_execute = time()

sys.stdout.write('loading dependencies... ')
sys.stdout.flush()
import matplotlib
matplotlib.use('Agg')
import datetime, urllib, json, subprocess
from obspy import read, UTCDateTime#, #Stream, Trace
from geopy.distance import vincenty

sys.stdout.write('done.\n')
sys.stdout.flush()

seismometer = (32.865468, -117.253436)
eventcoll = []
outstring = ""

# Get the hostname
p1=subprocess.check_output(['uname','-n']).rstrip()
p2=subprocess.check_output(['awk','/^domain/ {print $2}','/etc/resolv.conf']).rstrip()
hostname = p1 + "." + p2

datapath = "/srv/tc1/data/"

sys.stdout.write('querying USGS earthquake feed... ')
sys.stdout.flush()
url = "http://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson"
response = urllib.urlopen(url);
data = json.loads(response.read())
sys.stdout.write('done.\n')
sys.stdout.flush()

sys.stdout.write('filtering results by distance/magnitude... ')
sys.stdout.flush()

now   = datetime.datetime.now() + datetime.timedelta(hours=7, minutes=0, seconds=0) # convert time to UTC
past  = now - datetime.timedelta(hours=12, minutes=now.time().minute, seconds=now.time().second, microseconds=now.time().microsecond)
start = UTCDateTime(past) # put in UTCDateTime object
end   = UTCDateTime(now)

for feature in data['features']:
    place           = feature['properties']['place']
    mag             = feature['properties']['mag']
    url             = feature['properties']['url']
    (lon,lat,depth) = feature['geometry']['coordinates']
    eventtime       = UTCDateTime(feature['properties']['time']/1000)

    if (end - eventtime) <= 46800:
        # Decide which earthquakes to show
        show_quake = False
        dist = vincenty(seismometer, (lat,lon)).kilometers
        if (dist >= 8000):
            if mag >= 6.0:
                show_quake = True
        elif (dist < 8000 and dist >= 5000):
            if mag >= 5.9:
                show_quake = True
        elif (dist < 5000 and dist >= 3000):
            if mag >= 5.8: 
                show_quake = True
        elif (dist < 3000 and dist >= 1500):
            if mag >= 5.6:
                show_quake = True
        elif (dist < 1500 and dist >= 1000):
            if mag >= 4.7:
                show_quake = True
        elif (dist < 1000 and dist >= 300):
            if mag >= 3.5:
                show_quake = True
        elif (dist < 300 and dist >= 150):
            if mag >= 3.2:
                show_quake = True
        elif (dist < 150):
            if mag >= 3:
                show_quake = True
        
        if show_quake:
            # add to event collection
            event = {"time": eventtime, "text": ("M%s" % mag) + " " + place}
            eventcoll.append(event)
            outstring = outstring + "<a href=\"%s\" target=\"_new\">M%.1f %s (%.2f km depth), Distance from receiver: %.2f km</a><br />" % (url,mag,place,depth,dist)
sys.stdout.write('done.\n')
sys.stdout.flush()

yr    = end.year
ejday = end.julday
sjday = start.julday

#print "DEBUG: ejday: %d, sjday: %d" % (ejday,sjday)

sys.stdout.write('reading files... ')
sys.stdout.flush()

st = read(datapath + "%d/%d/*.mseed" % (yr,ejday), format="MSEED", starttime=start, endtime=end)
if sjday != ejday:
    st1 = read(datapath + "%d/%d/*.mseed" % (yr,sjday), format="MSEED", starttime=start, endtime=end)
    st = st + st1
    
sys.stdout.write('done.\n')
sys.stdout.flush()

numtraces = 0
try:
    numtraces = len(st.traces)
except AttributeError:
    sys.stdout.write('Error: There are no traces to gather.')
    sys.stdout.write('\nExiting process...\n')
    sys.stdout.flush()
    sys.exit(1)
    
ftime = st.traces[0].stats.starttime
ltime = st.traces[numtraces-1].stats.endtime
(fyear,fmon,fday) = (ftime.year,ftime.month,ftime.day)
(lyear,lmon,lday) = (ltime.year,ltime.month,ltime.day)

filedates = "%d%02d%02d-%d%02d%02d" % (lyear,lmon,lday,fyear,fmon,fday)
outfile = "/srv/www/%s/public/images/dayplots/iri.soca.%s.bhz.png" % (hostname, filedates)

sys.stdout.write('filtering data... ')
sys.stdout.flush()
st.filter("lowpass", freq=0.1, corners=2)
sys.stdout.write('done.\n')
sys.stdout.flush()

sys.stdout.write('generating plot... ')
sys.stdout.flush()
st.plot(type="dayplot", interval=60, right_vertical_labels=False,
        #title="%s (%s)" % (st.traces[0].id,hostname),
        title="",
        vertical_scaling_range=15, one_tick_per_line=True,
        color=['k', 'r', 'b', 'g'], 
        show_y_UTC_label=True,
        events=eventcoll,
        outfile=outfile
        )
sys.stdout.write('done.\n')
sys.stdout.flush()

timestring = strftime("%a, %d %b %Y %H:%M:%S %Z", localtime())

if len(eventcoll) == 0:
    outstring = "<i>No events currently displayed</i>"

imgurl = "http://%s/images/dayplots/iri.soca.%s.bhz.png" % (hostname, filedates)
htmlout = """
<html>
<head>
<meta http-equiv="Refresh" content="300">
<style>
table, th, td {
    border: 0px solid black;
    border-collapse: collapse;
}
</style>
</head>
<body>
<table>
<tr><td><img src="%s" /></td></tr>
<tr><th>Earthquakes shown on this plot</th></tr>
<tr><td style="text-align:center">%s</td></tr>
<tr><td style="text-align:center"><i>Note: Unlabeled seismic events are usually noise sources within the building.</i></td></tr>
<tr><td style="text-align:center"><i>Generated: %s on %s</i></td></tr>
</table>
</body>
</html>
""" % (imgurl, outstring, timestring, hostname)
sys.stdout.write('writing include file... ')
sys.stdout.flush()
f = open('/srv/www/%s/public/out/tc1.html' % hostname, 'w')
f.write(htmlout)
f.close()
sys.stdout.write('done.\n')
sys.stdout.write('processing finished.\n')

end_execute = time()
elapsed = end_execute - start_execute
print "Elapsed run time: ", elapsed, "seconds."
