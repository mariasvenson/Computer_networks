#!/usr/bin/python
#
# Computer Networks 2 - 2014-2015
#
# This script parses the output of tshark and makes a plot using matplotlib.
#
# usage: plot_tput.py <interval in seconds> <tshark output file name>
#
# To generate the input file for this script run tshark on your pcap file as follows:
# bash$ tshark -r <pcap file name> -t r -q -z io,stat,0.5 > tputfile
#
# And then plot the graph:
# bash$ python plot_tput.py tputfile
#
# A bug in the installed tshark version, prohibits you from generating intervals less
# than 1 second.


import sys, os, re
import datetime
import matplotlib.pyplot as plt

class LogParser:
    def __init__(self):
        self.lst_regex_handlers = []
        
    def AddHandler(self, s_regex, o_function):
        self.lst_regex_handlers.append((re.compile(s_regex, re.M|re.I), o_function))
        
    def ParseFile(self, s_file):
        if os.path.isfile(s_file) == False :
            sys.stderr.write('ERROR : No such file in %s\n' % s_file)
            sys.exit(1)
        h_file = open(s_file, 'r')
        s_line = h_file.readline()
        while s_line :
            for o_regex, handler in self.lst_regex_handlers:
                o_matchobj = o_regex.match(s_line)
                if o_matchobj:
                    handler(o_matchobj)
                    break
            s_line = h_file.readline()
        h_file.close()

class ThroughputData:
    def __init__(self, o_time, i_bytes):
        self.o_time = o_time
        self.i_bytes = i_bytes
#-----------------------------------------------------------------------------------------

lst_throughput_data = []

#-----------------------------------------------------------------------------------------
# Regex: \|\s+(\d+.\d+)\s<>\s+\d+.\d+\s\|\s+\d+\s\|\s+(\d+)\s\|
# Ex: | 10.5 <> 11.0 |      6 |  1380 |
def onMatchThroughputData(o_matchobj):
    global lst_throughput_data
    
    o_throughput_data = ThroughputData(o_matchobj.group(1), int(o_matchobj.group(2)))
    lst_throughput_data.append(o_throughput_data)

#-----------------------------------------------------------------------------------------


def MakePlot(s_data_file_1):
    o_log_parser = LogParser()
    o_log_parser.AddHandler("\|\s+(\d+.\d+)\s<>\s+\d+.\d+\s\|\s+\d+\s\|\s+(\d+)\s\|",
                            onMatchThroughputData)
    o_log_parser.ParseFile(s_data_file_1)

    y_array_1 = [o_data.i_bytes for o_data in lst_throughput_data]
    x_array_1 = [o_data.o_time for o_data in lst_throughput_data]

    plt.plot(x_array_1, y_array_1, color='#E9AB17', linewidth=0.5)
    plt.ylim(0)
    plt.xlim(0)
    plt.show()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.stderr.write("usage: %s <tshark output file name>\n"
                         % sys.argv[0])
        sys.exit(1)
    MakePlot(sys.argv[1])

