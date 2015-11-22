#! /usr/bin/python
#
# Computer Networks II - 2014
#
# This script makes som simple plots using matplotlib based on the logging
# output of a ns-3 simulation. First part is to enable logging of two TCP
# streams. We assume both node 0 and node 1 will be TCP clients (this is
# the original script code of sim-tcp.py). Uncomment the following line in
# that script (assuming you still use TCP NewReno):
#
#  ns.core.LogComponentEnable("TcpNewReno", ns.core.LOG_LEVEL_LOGIC)
#
# Next run a simulation and put the logging data in the file log.data:
#
#  bash$ python sim-tcp.py --latency=1 2> log.data
#
# Then filter out the interesting bits of the log file using the awk tool:
#
#  bash$ awk '/node 0.*updated to cwnd/{ print $1, $9 }' < log.data > cwnd-0.data
#  bash$ awk '/node 1.*updated to cwnd/{ print $1, $9 }' < log.data > cwnd-1.data
#
# It will generate two new files (cwnd-0.data and cwnd-1.data). They should
# contain two columns, one with time stamps, and one with the congestion
# window size at that time.
#
# Finally, you run this script in the same file directory as the two new
# cwnd files. It should make graph of the congestion window over time for
# the two TCP flows.

import matplotlib.pyplot as plt
import numpy

# Read data from a file and convert it into two arrays
a=numpy.loadtxt("cwnd-0.data")
(x0,y0)=a.transpose()

# Read data from another file in the same way
b=numpy.loadtxt("cwnd-1.data")
(x1,y1)=b.transpose()

# Plot the whole thing with matplotlib
plt.plot(x0,y0, 'r-', x1, y1, 'b-')

# Change some default behavior in matplotlib
plt.ylabel("cwnd")
plt.xlim(0,60)

# Finally show the results
plt.show()
