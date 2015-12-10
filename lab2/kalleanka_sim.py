#
# This script simulates 6 nodes configured in a "dumb bell" network. See below:
#
# Network topology
#
#       n0 ---+      +--- n2
#             |      |
#             n4 -- n5
#             |      |
#       n1 ---+      +--- n3
#
# - All links are point-to-point with data rate 500kb/s and propagation delay 2ms
#
# Two data flows (and their applications are created):
# - A TCP flow form n0 to n2
# - A TCP flow from n1 to n3

import sys
import ns.applications
import ns.core
import ns.internet
import ns.network
import ns.point_to_point
import ns.point_to_point_layout
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
#ns.core.LogComponentEnable("OnOffApplication", ns.core.LOG_LEVEL_INFO)
#ns.core.LogComponentEnable("TcpWestwood", ns.core.LOG_LEVEL_LOGIC)
#ns.core.LogComponentEnable("TcpTahoe", ns.core.LOG_LEVEL_LOGIC)
#ns.core.LogComponentEnable("TcpNewReno", ns.core.LOG_LEVEL_LOGIC)




#######################################################################################
# COMMAND LINE PARSING
#
# Parse the command line arguments. Some simulation parameters can be set from the
# command line instead of in the script. You may start the simulation by:
#
# bash$ ./waf shell
# bash$ python sim-tcp.py --latency=10
#
# You can add your own parameters and there default values below. To access the values
# in the simulator, you use the variable cmd.something.

cmd = ns.core.CommandLine()

# Default values
cmd.latency = 1
cmd.rate = 1000000000
cmd.interval = 1
cmd.AddValue ("rate", "P2P data rate in bps")
cmd.AddValue ("latency", "P2P link Latency in miliseconds")
cmd.AddValue ("interval", "UDP client packet interval")
cmd.Parse(sys.argv)


#######################################################################################
# CREATE NODES

#nodes = ns.network.NodeContainer()
#nodes.Create(8)


#######################################################################################
# CONNECT NODES WITH POINT-TO-POINT CHANNEL
#
# We use a helper class to create the point-to-point channels. It helps us with creating
# the necessary objects on the two connected nodes as well, including creating the
# NetDevices (of type PointToPointNetDevice), etc.

# Set the default queue length to 5 packets (used by NetDevices)
ns.core.Config.SetDefault("ns3::DropTailQueue::MaxPackets", ns.core.UintegerValue(5))
pointToPoint = ns.point_to_point.PointToPointHelper()
pointToPoint.SetDeviceAttribute("Mtu", ns.core.UintegerValue(576))
pointToPoint.SetDeviceAttribute("DataRate",ns.network.DataRateValue(ns.network.DataRate(32000)))
pointToPoint.SetChannelAttribute("Delay",ns.core.TimeValue(ns.core.MilliSeconds(0)))
star = ns.point_to_point_layout.PointToPointStarHelper(8, pointToPoint)

# Add each client to a container
clnt = ns.network.NodeContainer()
for i in range(0, int(star.SpokeCount())):
  clnt.Add(star.GetSpokeNode(i))

# the minimum MTU size that an host can set is 576 and IP header max size can be 60 bytes 
# (508 = 576 MTU - 60 IP - 8 UDP)

pointToPoint.SetDeviceAttribute("Mtu", ns.core.UintegerValue(576))
pointToPoint.SetDeviceAttribute("DataRate", ns.network.DataRateValue(ns.network.DataRate(3200000000)))
pointToPoint.SetChannelAttribute("Delay", ns.core.TimeValue(ns.core.MilliSeconds(int(0))))

# Add server node to a own container
srvr = ns.network.NodeContainer()
srvr.Create(1) 

# Add server and switch nodes to a own container
srvrToSwitch = ns.network.NodeContainer()
srvrToSwitch.Add(srvr.Get(0))
srvrToSwitch.Add(star.GetHub())

# Install point-to-point between server and switch
pSrvrTopSwitch = pointToPoint.Install(srvrToSwitch)





# Here we can introduce an error model on the bottle-neck link (from node 4 to 5)
#em = ns.network.RateErrorModel()
#em.SetAttribute("ErrorUnit", ns.core.StringValue("ERROR_UNIT_PACKET"))
#em.SetAttribute("ErrorRate", ns.core.DoubleValue(0.02))
#d4d5.Get(1).SetReceiveErrorModel(em)


#######################################################################################
# CREATE A PROTOCOL STACK
#
# This code creates an IPv4 protocol stack on all our nodes, including ARP, ICMP,
# pcap tracing, and routing if routing configurations are supplied. All links need
# different subnet addresses. Finally, we enable static routing, which is automatically
# setup by an oracle.

# Install networking stack for nodes
stack = ns.internet.InternetStackHelper()
star.InstallStack(stack)

stack.Install(srvr)

clientAddresses = ns.internet.Ipv4AddressHelper()
clientAddresses.SetBase(ns.network.Ipv4Address("10.1.1.0"), ns.network.Ipv4Mask("255.255.255.0"))
clientInterface = star.AssignIpv4Addresses(clientAddresses)

serverAddresses = ns.internet.Ipv4AddressHelper()
serverAddresses.SetBase(ns.network.Ipv4Address("10.2.0.0"), ns.network.Ipv4Mask("255.255.255.0"))
serverInterface = serverAddresses.Assign(pSrvrTopSwitch)

ns.internet.Ipv4GlobalRoutingHelper.PopulateRoutingTables()


#######################################################################################
# CREATE TCP APPLICATION AND CONNECTION
#
# Create a TCP client at node N0 and a TCP sink at node N2 using an On-Off application.
# An On-Off application alternates between on and off modes. In on mode, packets are
# generated according to DataRate, PacketSize. In off mode, no packets are transmitted.

# CONFIGURE CLIENT
#clientApps = ns.applications.ApplicationContainer()
for i in range(0, int(star.SpokeCount())):
  #client_address = ns.network.InetSocketAddress(star.GetSpokeIpv4Address(i), 9)

  client_address = star.GetSpokeNode(i).GetDevice(0).GetAddress()
  packet_sink_helper = ns.applications.PacketSinkHelper("ns3::UdpSocketFactory", client_address)
  clientApps = packet_sink_helper.Install(star.GetSpokeNode(i))
  clientApps.Start(ns.core.Seconds(0.0))
  clientApps.Stop(ns.core.Seconds(3600.0))



# http://stackoverflow.com/questions/14993000/the-most-reliable-and-efficient-udp-packet-size
# CONFIGURE SERVER
for i in range(0, int(star.SpokeCount())):
  clnt1 = ns.network.NodeContainer()
  clnt1.Add(star.GetSpokeNode(i))
  server = ns.applications.UdpClientHelper(star.GetSpokeIpv4Address(i), 9)
  server.SetAttribute("MaxPackets", ns.core.UintegerValue(27000))
  server.SetAttribute("PacketSize", ns.core.UintegerValue(508)) 
  server.SetAttribute("Interval", ns.core.TimeValue(ns.core.Seconds(float(0.1))))
  serverApps = server.Install(srvr)
  serverApps.Start(ns.core.Seconds(0.0))
  serverApps.Stop(ns.core.Seconds(3600.0))






#######################################################################################
# CREATE A PCAP PACKET TRACE FILE
#
# This line creates two trace files based on the pcap file format. It is a packet
# trace dump in a binary file format. You can use Wireshark to open these files and
# inspect every transmitted packets. Wireshark can also draw simple graphs based on
# these files.
#
# You will get two files, one for node 0 and one for node 1

pointToPoint.EnablePcap("sim-server", pSrvrTopSwitch.Get(0), True)


#######################################################################################
# FLOW MONITOR
#
# Here is a better way of extracting information from the simulation. It is based on
# a class called FlowMonitor. This piece of code will enable monitoring all the flows
# created in the simulator. There are four flows in our example, one from the client to
# server and one from the server to the client for both TCP connections.

flowmon_helper = ns.flow_monitor.FlowMonitorHelper()
monitor = flowmon_helper.InstallAll()


#######################################################################################
# RUN THE SIMULATION
#
# We have to set stop time, otherwise the flowmonitor causes simulation to run forever

ns.core.Simulator.Stop(ns.core.Seconds(3800.0))
ns.core.Simulator.Run()


#######################################################################################
# FLOW MONITOR ANALYSIS
#
# Simulation is finished. Let's extract the useful information from the FlowMonitor and
# print it on the screen.

# check for lost packets
monitor.CheckForLostPackets()

classifier = flowmon_helper.GetClassifier()

for flow_id, flow_stats in monitor.GetFlowStats():
  t = classifier.FindFlow(flow_id)
  proto = {6: 'TCP', 17: 'UDP'} [t.protocol]
  print ("FlowID: %i (%s %s/%s --> %s/%i)" % 
          (flow_id, proto, t.sourceAddress, t.sourcePort, t.destinationAddress, t.destinationPort))
          
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
