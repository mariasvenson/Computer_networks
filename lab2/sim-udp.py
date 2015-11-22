
#
# This script simulates two nodes connected with a point-to-point channel and running
# a UDP Echo service on top of an Internet protocol stack. Node 0 is the client, and
# node 1 is the server.
#
# Node 0 generates 100 packets of size 1024 (+ some headers) with deterministic inter-
# arrival times.

import sys
import time
import ns.applications
import ns.core
import ns.internet
import ns.network
import ns.point_to_point
import ns.flow_monitor


#######################################################################################
# SEEDING THE RNG
#
# Enable this line to have random number being generated between runs.

#ns.core.RngSeedManager.SetSeed(int(time.time() * 1000 % (2**31-1)))

#######################################################################################
# LOGGING
#
# Here you may enable extra output logging. It will be printed to the stdout.
# This is mostly useful for debugging and investigating what is going on in the
# the simulator. You may use this output to generate your results as well, but
# you would have to write extra scripts for filtering and parsing the output.
# FlowMonitor may be a better choice of getting the information you want.

#ns.core.LogComponentEnable("UdpEchoClientApplication", ns.core.LOG_LEVEL_INFO)
#ns.core.LogComponentEnable("UdpEchoServerApplication", ns.core.LOG_LEVEL_INFO)
#ns.core.LogComponentEnable("PointToPointNetDevice", ns.core.LOG_LEVEL_ALL)
#ns.core.LogComponentEnable("DropTailQueue", ns.core.LOG_LEVEL_LOGIC)


#######################################################################################
# COMMAND LINE PARSING
#
# Parse the command line arguments. Some simulation parameters can be set from the
# command line instead of in the script. You may start the simulation by:
#
# bash$ ./waf shell
# bash$ python sim-udp.py --interval=0.1
#
# You can add your own parameters and there default values below. To access the values
# in the simulator, you use the variable cmd.something.

cmd = ns.core.CommandLine()

# Default values
cmd.latency = 1
cmd.rate = 500000
cmd.interval = 0.01
cmd.AddValue ("latency", "P2P link Latency in miliseconds")
cmd.AddValue ("rate", "P2P data rate in bps")
cmd.AddValue ("interval", "UDP client packet interval")
cmd.Parse(sys.argv)


#######################################################################################
# CREATE NODES

nodes = ns.network.NodeContainer()
nodes.Create(2)


#######################################################################################
# CONNECT NODES WITH POINT-TO-POINT CHANNEL
#
# We use a helper class to create the point-to-point channel. It helps us with creating
# the necessary objects on the two connected nodes as well, including creating the
# NetDevices (of type PointToPointNetDevice), etc.

pointToPoint = ns.point_to_point.PointToPointHelper()
pointToPoint.SetDeviceAttribute("DataRate",
                            ns.network.DataRateValue(ns.network.DataRate(int(cmd.rate))))
pointToPoint.SetChannelAttribute("Delay",
                                 ns.core.TimeValue(ns.core.MilliSeconds(int(cmd.latency))))
devices = pointToPoint.Install(nodes)

# devices is a collection (of two NetDevices). We can get them with the Get(n) method.
# a NetDevice has a method called GetQueue() that retrieves its outgoing buffer queue.
# By default that is a DropTailQueue, and that one has an attribute called "MaxPackets"
# that specifies the queue lengths in the number of packets. Default is 100 packets.
# Here you can change the default values:
devices.Get(0).GetQueue().SetAttribute("MaxPackets", ns.core.UintegerValue(100))
devices.Get(1).GetQueue().SetAttribute("MaxPackets", ns.core.UintegerValue(1))

em = ns.network.RateErrorModel()
em.SetAttribute("ErrorUnit", ns.core.StringValue("ERROR_UNIT_PACKET"))
em.SetAttribute("ErrorRate", ns.core.DoubleValue(0.1))
devices.Get(1).SetReceiveErrorModel(em)

#######################################################################################
# CREATE A PROTOCOL STACK
#
# This code creates an IPv4 protocol stack on both our nodes, including ARP, ICMP,
# pcap tracing, and routing if routing configurations are supplied.

stack = ns.internet.InternetStackHelper()
stack.Install(nodes)

# This part assigns IPv4 addresses to the NetDevices in the devices container. It
# returns a container of "interfaces" that we need when we create applications. A
# client application must know which server to connect to and here the interfaces are
# used.
address = ns.internet.Ipv4AddressHelper()
address.SetBase(ns.network.Ipv4Address("10.1.1.0"), ns.network.Ipv4Mask("255.255.255.0"))
interfaces = address.Assign(devices);


#######################################################################################
# CREATE UDP CLIENT AND SERVER
#
# In this section, we create two applications on the two different nodes, tells the
# client to connect to the server, and start generating 100 packets with a
# deterministic inter-arrival time.

# Create the server on port 9. Put it on node 1, and start it at time 1.0s.
echoServer = ns.applications.UdpEchoServerHelper(9)
serverApps = echoServer.Install(nodes.Get(1))
serverApps.Start(ns.core.Seconds(1.0))
serverApps.Stop(ns.core.Seconds(10.0))

# Create the client application and connect it to node 1 and port 9. Configure number
# of packets, packet sizes, inter-arrival interval.
echoClient = ns.applications.UdpEchoClientHelper(interfaces.GetAddress(1), 9)
echoClient.SetAttribute("MaxPackets", ns.core.UintegerValue(100))
echoClient.SetAttribute("Interval",
                        ns.core.TimeValue(ns.core.Seconds (float(cmd.interval))))
echoClient.SetAttribute("PacketSize", ns.core.UintegerValue(1024))

# Put the client on node 0 and start sending at time 2.0s.
clientApps = echoClient.Install(nodes.Get(0))
clientApps.Start(ns.core.Seconds(2.0))
clientApps.Stop(ns.core.Seconds(10.0))


#######################################################################################
# CREATE A PCAP PACKET TRACE FILE
#
# This line creates two trace files based on the pcap file format. It is a packet
# trace dump in a binary file format. You can use Wireshark to open these files and
# inspect every transmitted packets. Wireshark can also draw simple graphs based on
# these files.
#
# You will get two files. One per NetDevice (i.e., one per Node). Each file is like
# running Wireshark on each node. sim-udp-0-0.pcap is the file from node 0 and
# sim-udp-1-0.pcap is the file from node 1.

pointToPoint.EnablePcapAll("sim-udp")


#######################################################################################
# FLOW MONITOR
#
# Here is a better way of extracting information from the simulation. It is based on
# a class called FlowMonitor. This piece of code will enable monitoring all the flows
# created in the simulator. There are two flows in our example, one from the client to
# server and one from the server to the client.

flowmon_helper = ns.flow_monitor.FlowMonitorHelper()
monitor = flowmon_helper.InstallAll()


#######################################################################################
# RUN THE SIMULATION
#
# We have to set stop time, otherwise the flowmonitor causes simulation to run forever

ns.core.Simulator.Stop(ns.core.Seconds(15.0))
ns.core.Simulator.Run()


#######################################################################################
# FLOW MONITOR ANALYSIS
#
# Simulation is finished. Let's extract the useful information from the FlowMonitor and
# print it on the screen.

# check for lost packets
monitor.CheckForLostPackets ();

classifier = flowmon_helper.GetClassifier()

for flow_id, flow_stats in monitor.GetFlowStats():
  t = classifier.FindFlow(flow_id)
  proto = {6: 'TCP', 17: 'UDP'} [t.protocol]
  print ("FlowID: %i (%s %s/%s --> %s/%i)" % 
         (flow_id, proto, t.sourceAddress, t.sourcePort,
          t.destinationAddress, t.destinationPort))
          
  print ("  Tx Bytes: %i" % flow_stats.txBytes)
  print ("  Rx Bytes: %i" % flow_stats.rxBytes)
  print ("  Lost Pkt: %i" % flow_stats.lostPackets)
  print ("  Flow active: %fs - %fs" % (flow_stats.timeFirstTxPacket.GetSeconds(),
                                       flow_stats.timeLastRxPacket.GetSeconds()))
  print ("  Throughput: %f Mbps" % (flow_stats.rxBytes * 
                                    8.0 / 
                                    (flow_stats.timeLastRxPacket.GetSeconds() 
                                     - flow_stats.timeFirstTxPacket.GetSeconds())/
                                    1024/
                                    1024))


# This is what we want to do last
ns.core.Simulator.Destroy()

