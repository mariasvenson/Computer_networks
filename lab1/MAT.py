#! /usr/bin/python

import sys,socket,struct,select
import time

BLOCK_SIZE= 512

OPCODE_RRQ=   1
OPCODE_WRQ=   2
OPCODE_DATA=  3
OPCODE_ACK=   4
OPCODE_ERR=   5

MODE_NETASCII= "netascii"
MODE_OCTET=    "octet"
MODE_MAIL=     "mail"

TFTP_PORT= 69

# Timeout in seconds
TFTP_TIMEOUT= 2

ERROR_CODES = ["Undef",
               "File not found",
               "Access violation",
               "Disk full or allocation exceeded",
               "Illegal TFTP operation",
               "Unknown transfer ID",
               "File already exists",
               "No such user"]

# Internal defines
TFTP_GET = 1
TFTP_PUT = 2


def make_packet_rrq(filename, mode):
    # Note the exclamation mark in the format string to pack(). What is it for?
    return struct.pack("!H", OPCODE_RRQ) + filename + '\0' + mode + '\0'

def make_packet_wrq(filename, mode):
	return struct.pack("!H", OPCODE_WRQ) + filename + '\0' + mode + '\0'


def make_packet_data(blocknr, data):
	return struct.pack("!HH", OPCODE_DATA, blocknr) + data


def make_packet_ack(blocknr):
	return struct.pack("!HH", OPCODE_ACK, blocknr) 
	
def make_packet_err(errcode, errmsg):
    return struct.pack("!HH", OPCODE_ERR, errcode) + errmsg + '\0'


"""This function parses a recieved packet and returns a tuple where the
        first value is the opcode as an integer and the following values are
        the other parameters of the packets in python data types"""
def parse_packet(msg):
	opcode = struct.unpack("!H", msg[:2])[0]
	if opcode == OPCODE_RRQ:
		l = msg[2:].split('\0')
		if len(l) != 3:
			return None
		return opcode, l[1], l[2]
	elif opcode == OPCODE_WRQ:
	# TDOO
		l = msg[2:].split('\0')
		if len(l) != 3:
			return None
		return opcode, l[1], l[2]
	elif opcode == OPCODE_DATA:
		block = struct.unpack("!H", msg[2:4])[0]
		data = msg[4:]
		return opcode, block, data
	elif opcode == OPCODE_ACK:
		block = struct.unpack("!H", msg[2:])[0]
		return opcode, block
		
	else:
		return None


		
def tftp_transfer(fd, hostname, direction):
    # Implement this function
    
    # Open socket interface
	

	try:	
		(family, socktype, proto, canonname, sockaddr) = socket.getaddrinfo('0.0.0.0', 50007, socket.AF_INET, socket.SOCK_DGRAM, socket.getprotobyname('udp'))[0]
		
		print (family, socktype, proto, canonname, sockaddr)
		
		s = socket.socket(family, socktype, proto)
		s.setblocking(0)
		s.bind(sockaddr)

		(family, socktype, proto, canonname, serverAddrInit) = socket.getaddrinfo(hostname, 20069      , socket.AF_INET, socket.SOCK_DGRAM, socket.getprotobyname('udp'))[0]
		(serverHost, serverPortInit) = serverAddrInit
		print (family, socktype, proto, canonname, serverAddrInit)
		
		# Check if we are putting a file or getting a file and send
		#  the corresponding request.

		reqPacket = None
		dataToWrite = ""	
		currentBlock=0
		serverTID = None
		resendCount=0
		serverAddr = None
		if direction == TFTP_GET: 
			print "Sending RRQ"
			print serverAddrInit
			reqPacket = make_packet_rrq(fd.name, MODE_OCTET)
			s.sendto(reqPacket, serverAddrInit)		
		elif direction == TFTP_PUT:
			print "Sending WRQ"
			print serverAddrInit
			s.sendto(make_packet_wrq(fd.name, MODE_OCTET), serverAddrInit)
		else:
			return
			

    # Put or get the file, block by block, in a loop.
		try:	
			while True:
	
				if direction == TFTP_GET: 

					print "Waiting for Data"	
					(rl,wl,xl) = select.select([s], [], [], TFTP_TIMEOUT)

					
					if s in rl:
						(data, serverAddr) = s.recvfrom(516)
						(host, port) = serverAddr
							
						if host != serverHost:
							print 'Received message from unexpected host. Ignores.'
							continue
									
						if serverTID == None:
							serverTID = port
						elif port != serverTID:
							print 'Received data from an unexpected TID. Sends error packet to source.'
							(bytes) = s.sendto(make_packet_err(5, ERROR_CODES[5]), serverAddr)
							continue
								
						(opcode, block, data) = parse_packet(data)
								
						print 'Received block #{0}'.format(block)

						if opcode != OPCODE_DATA:
							print 'Received unexpected packet type. Sends error and terminates.'
							(bytes) = s.sendto(make_packet_err(4, ERROR_CODES[4]), serverAddr)
							break
							
							
						if block == currentBlock + 1: #CORRECT PACKET
							dataToWrite+=data
							currentBlock = block	
							resendCount = 0
						else:
							print 'Retrieved a duplicate data packet, ignores it.'
							continue

					else:
						print "Timeout on recieve"
	
						if currentBlock == 0:
							print "Retransmits RRQ packet"
							(bytes) = s.sendto(reqPacket, serverAddrInit)
							continue
						elif len(data) < BLOCK_SIZE:
							print "Transmission complete."
							fd.write(dataToWrite) 
							break	
						else:
							resendCount += 1
							if resendCount >= 4:
								print "Stops retransmission and terminates."
								break						
							print "Retransmits last packet"
					
					(rl,wl,xl) = select.select([], [s], [], TFTP_TIMEOUT)
					if s in wl:												
						print 'Sends ACK for block #{0}'.format(currentBlock)	
						(bytes) = s.sendto(make_packet_ack(currentBlock), serverAddr)	
					else:
						print "Timeout on send"
						break
							
				elif direction == TFTP_PUT:
						print "Waiting for Acc"
						
						(rl,wl,xl) = select.select([s], [], [], TFTP_TIMEOUT)

						if s in rl:
							(data, serverAddr) = s.recvfrom(4)
							
							(host, port) = serverAddr
							
							if host != serverHost:
								print 'Received message from unexpected host. Ignores.'
								continue
								
							if serverTID == None:
								serverTID = port
							elif port != serverTID:
								print 'Received data from an unexpected TID. Sends error packet to source.'
								(bytes) = s.sendto(make_packet_err(5, ERROR_CODES[5]), serverAddr)
								continue						
							
							(opcode, block) = parse_packet(data)	
							
							if opcode != OPCODE_ACK:
								print 'Received unexpected packet type. Sends error and terminates.'
								(bytes) = s.sendto(make_packet_err(4, ERROR_CODES[4]), serverAddr)
								break
								
							if block == currentBlock: #CORRECT ACK
								currentData = fd.read(BLOCK_SIZE)
								currentBlock += 1
								resendCount = 0
							else:
								print 'Retrieved a duplicate data packet, ignores it.'
								continue
								
								
							print 'Received ACK for block #{0}'.format(block)
						else:
							print "Timeout on receive"					
							if currentData == "":
								print "Transmission complete."
								break		
							elif currentBlock == 0:
								print "Retransmits WRQ packet"
								(bytes) = s.sendto(reqPacket, serverAddrInit)
								continue
							else:
								resendCount += 1
								if resendCount >= 4:
									print "Stops retransmission and terminates."
									break						
								print "Retransmits last packet"
									

						(rl,wl,xl) = select.select([], [s], [], TFTP_TIMEOUT)
						if s in wl:					
							print 'Sends Data for block #{0}'.format(currentBlock)	
							(bytes) = s.sendto(make_packet_data(currentBlock, currentData), serverAddr)	
						else:
							print "Timeout on send"
							break
						
						

						
				else:
					return
				
				
			# Wait for packet, write the data to the filedescriptor or
			# read the next block from the file. Send new packet to server.
			# Don't forget to deal with timeouts and received error packets.
				
		except:
			print "Unexpected error:", sys.exc_info()[0]					
			if serverAddr != None:
				(bytes) = s.sendto(make_packet_err(0, ERROR_CODES[0]), serverAddr)	
			raise						
							
		s.close()
		
	except socket.error as e:
		print "Socket error\n", e
		sys.exit(2)
	except socket.gaierror as e1: 
		sys.stderr.write("Socket GAI error (%s)\n" % ( e1.strerror))
		sys.exit(2)
		
	



def usage():
    """Print the usage on stderr and quit with error code"""
    sys.stderr.write("Usage: %s [-g|-p] FILE HOST\n" % sys.argv[0])
    sys.exit(1)


def main():
    # No need to change this function
    direction = TFTP_GET
    if len(sys.argv) == 3:
        filename = sys.argv[1]
        hostname = sys.argv[2]
    elif len(sys.argv) == 4:
        if sys.argv[1] == "-g":
            direction = TFTP_GET
        elif sys.argv[1] == "-p":
            direction = TFTP_PUT
        else:
            usage()
            return
        filename = sys.argv[2]
        hostname = sys.argv[3]
    else:
        usage()
        return

    if direction == TFTP_GET:
        print "Transfer file %s from host %s" % (filename, hostname)
    else:
        print "Transfer file %s to host %s" % (filename, hostname)

    try:
        if direction == TFTP_GET:
            fd = open(filename, "wb")
        else:
            fd = open(filename, "rb")
    except IOError as e:
        sys.stderr.write("File error (%s): %s\n" % (filename, e.strerror))
        sys.exit(2)

    tftp_transfer(fd, hostname, direction)
    fd.close()

if __name__ == "__main__":
    main()
