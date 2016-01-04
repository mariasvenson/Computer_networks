#
#
# Network topology: Star 
#
#                n2 n3 n4
#                 \ | /
#                  \|/
#              S0---R0---n5
#                  /|\
#                 / | \
#             n100 ... n6
#
# - All links between R0 and n1..n100 are point-to-point with data rate 100 KB/s and propagation delay 10ms
# - The link between R0 and the server S0 is point-to-point with data rate 10 MB/s and propagation delay 10ms
# Two data flows (and their applications are created):
# - TCP flow between all the nodes 
# - Server is n(100) BulkSendApplications and the nodes is PacketSink with TCP sockets.

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
# bash$ python kalleanka_sim.py --nclients=100
#
# You can add your own parameters and there default values below. To access the values
# in the simulator, you use the variable cmd.something.

cmd = ns.core.CommandLine()

# Default values
cmd.latency = 10 # 10 ms
cmd.crate = 800000 # 100 KB/s
cmd.srate = 80000000 # 10 MB/s
cmd.nclients = 100 
cmd.AddValue ("latency", "P2P link Latency in miliseconds")
cmd.AddValue ("crate", "P2P data rate of the clients in bps")
cmd.AddValue ("srate", "P2P data rate of the server in bps")
cmd.AddValue ("nclients", "Number of clients/spokes in the star topology")
cmd.Parse(sys.argv)


#######################################################################################
# OTHER DEFAULT VALUES

PACKET_SIZE = 1448 # 1448 B
FILE_SIZE = 12000000 # 12 MB
scenario = 2

ns.core.Config.SetDefault("ns3::TcpSocket::SegmentSize", ns.core.UintegerValue(1448));
ns.core.Config.SetDefault("ns3::DropTailQueue::MaxPackets", ns.core.UintegerValue(150))


#######################################################################################
# SET UP STAR TOPOLOGY AND CONNECT NODES WITH POINT-TO-POINT CHANNEL
#
# We use a helper class to create the point-to-point channels. It helps us with creating
# the necessary objects on the two connected nodes as well, including creating the
# NetDevices (of type PointToPointNetDevice), etc.

# First we set up the point-to-point channels between the clients (spokes) and insert
# them to the PointToPointStarHelper which then will create nclients. 
pointToPoint = ns.point_to_point.PointToPointHelper()
pointToPoint.SetDeviceAttribute("Mtu", ns.core.UintegerValue(1500))
pointToPoint.SetDeviceAttribute("DataRate",ns.network.DataRateValue(ns.network.DataRate(int(cmd.crate))))
pointToPoint.SetChannelAttribute("Delay",ns.core.TimeValue(ns.core.MilliSeconds(int(cmd.latency))))
star = ns.point_to_point_layout.PointToPointStarHelper(int(cmd.nclients), pointToPoint)

# Next we set up another point-to-point channel between the hub and the server
pointToPoint.SetDeviceAttribute("Mtu", ns.core.UintegerValue(1500))
pointToPoint.SetDeviceAttribute("DataRate", ns.network.DataRateValue(ns.network.DataRate(int(cmd.srate))))
pointToPoint.SetChannelAttribute("Delay", ns.core.TimeValue(ns.core.MilliSeconds(int(cmd.latency))))

# Add server node to a own container. This is done because the BulkSendApplication requires
# a NodeContainer as input to install
srvr = ns.network.NodeContainer()
srvr.Create(1) 

# Add server and hub nodes to a own container in order to assign ip addresses in the same subnet
srvrToHub = ns.network.NodeContainer()
srvrToHub.Add(srvr.Get(0))
srvrToHub.Add(star.GetHub())


#######################################################################################
# CREATE A PROTOCOL STACK
#
# This code creates an IPv4 protocol stack on all our nodes, including ARP, ICMP,
# pcap tracing, and routing if routing configurations are supplied. All links need
# different subnet addresses. Finally, we enable static routing, which is automatically
# setup by an oracle.

# Install point-to-point between server and hub
pSrvrTopHub = pointToPoint.Install(srvrToHub)

# Install networking stack for nodes
stack = ns.internet.InternetStackHelper()
star.InstallStack(stack)
stack.Install(srvr)

clientAddresses = ns.internet.Ipv4AddressHelper()
clientAddresses.SetBase(ns.network.Ipv4Address("10.0.2.0"), ns.network.Ipv4Mask("255.255.255.0"))
clientInterface = star.AssignIpv4Addresses(clientAddresses)

serverAddresses = ns.internet.Ipv4AddressHelper()
serverAddresses.SetBase(ns.network.Ipv4Address("10.0.1.0"), ns.network.Ipv4Mask("255.255.255.0"))
serverInterface = serverAddresses.Assign(pSrvrTopHub)

ns.internet.Ipv4GlobalRoutingHelper.PopulateRoutingTables()


#######################################################################################
# CREATE TCP APPLICATION AND CONNECTION
#
# Create a TCP packet sink at each client/spoke, node N1..N100 and 100 TCP BulkSendApplications
# at the server S0, one for each client to send to.

# CONFIGURE CLIENTS
for i in range(0, int(star.SpokeCount())):
  client_address = ns.network.InetSocketAddress(star.GetSpokeIpv4Address(i), 9)
  packet_sink_helper = ns.applications.PacketSinkHelper("ns3::TcpSocketFactory", client_address)
  clientApps = packet_sink_helper.Install(star.GetSpokeNode(i))
  clientApps.Start(ns.core.Seconds(0.0))
  clientApps.Stop(ns.core.Seconds(130.0))

# CONFIGURE SERVER
start = 10.0
for i in range(0, int(star.SpokeCount())):
  client_address = ns.network.InetSocketAddress(star.GetSpokeIpv4Address(i), 9)
  server = ns.applications.BulkSendHelper("ns3::TcpSocketFactory", client_address)
  server.SetAttribute("MaxBytes", ns.core.UintegerValue(FILE_SIZE))
  server.SetAttribute("SendSize", ns.core.UintegerValue(PACKET_SIZE)) 
  serverApps = server.Install(srvr)

  # if scneario == 1, clients will join in during while the movie is availible for streaming
  # if scenario == 2, two clients will join every second
  # otherwise it will be the ideal scenario, 100 clients start at the same time in the beginning
  if scenario == 1:
    # clients 0..39 start at 10.0
    # clients 40..69 start at 30.0
    if i == 40:
      start = 30.0
    # clients 70..89 start at 50.0
    elif i == 70:
      start = 50.0
   # clients 90..95 start at 70.0
    elif i == 90:
      start = 70.0
   # clients 96..100 start at 90.0
    elif i == 96:
      start = 90.0
  elif scenario == 2:
    if i % 2 == 1:
      start = float(i-1)
    else:
      start = float(i)

  serverApps.Start(ns.core.Seconds(start))
  serverApps.Stop(ns.core.Seconds(130.0))


#######################################################################################
# CREATE A PCAP PACKET TRACE FILE
#
# This line creates two trace files based on the pcap file format. It is a packet
# trace dump in a binary file format. You can use Wireshark to open these files and
# inspect every transmitted packets. Wireshark can also draw simple graphs based on
# these files.
#
# You will get two files, one for node 0 and one for node 1

#pointToPoint.EnablePcap("/media/sf_shared/sim-svtplay-srvr", pSrvrTopHub.Get(1), True)
#pointToPoint.EnablePcap("/media/sf_shared/sim-svtplay-clnt", star.GetSpokeNode(0).GetDevice(0), True)

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

ns.core.Simulator.Stop(ns.core.Seconds(200.0))
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
