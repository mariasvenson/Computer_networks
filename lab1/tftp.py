#! /usr/bin/python
# https://pymotw.com/2/struct/
import sys,socket,struct,select

BLOCK_SIZE= 512

# 512 + header (4)

#TFTP header consists of a 2 byte opcode field which indicates the packet's type
OPCODE_RRQ =   1
OPCODE_WRQ =   2
OPCODE_DATA =  3
OPCODE_ACK=   4
OPCODE_ERR=   5

MODE_NETASCII= "netascii"
MODE_OCTET=    "octet"
MODE_MAIL=     "mail"

TFTP_PORT= 13069

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
    # ! = network, H = unsigned short
    return struct.pack("!H", OPCODE_RRQ) + filename + '\0' + mode + '\0'

def make_packet_wrq(filename, mode):
    return struct.pack("!H", OPCODE_WRQ) + filename + '\0' + mode + '\0'

def make_packet_data(blocknr, data):
    # !HH
    return struct.pack("!HH", OPCODE_DATA, blocknr) + data

def make_packet_ack(blocknr):
    return struct.pack("!HH", OPCODE_ACK, blocknr) 

def make_packet_err(errcode, errmsg):
    return struct.pack("!HH", OPCODE_ERR, errcode) + errmsg + '\0'

def parse_packet(msg):
    """This function parses a recieved packet and returns a tuple where the
        first value is the opcode as an integer and the following values are
        the other parameters of the packets in python data types"""
    opcode = struct.unpack("!H", msg[:2])[0]
    if opcode == OPCODE_RRQ:
        l = msg[2:].split('\0')
        if len(l) != 3:
            return None
        return opcode, l[1], l[2]

    elif opcode == OPCODE_WRQ:
        l = msg[2:].split('\0')
        if len(l) != 3:
            return None
        return opcode, l[1], l[2]
    
    elif opcode == OPCODE_DATA:
        block = struct.unpack("!H", msg[2:4])[0]
        #print "BLOCKNR:  " + str(block)
        return opcode, block, msg[4:] # something here
    
    elif opcode == OPCODE_ACK:
        block = struct.unpack("!H", msg[2:])[0]
        return opcode, block, msg[4:] 
    
    elif opcode == OPCODE_ERR:
        errcode = struct.unpack("!H", msg[2:4])[0]
        errmsg = msg[4:-1]
        return opcode, errcode, errmsg
    else:
        return None 



def tftp_transfer(fd, hostname, direction):
    # Implement this function
    # Open socket interface
    
    host = socket.getaddrinfo(hostname, TFTP_PORT)
    ip = host[0][4][0]
    port = host[0][4][1]
    serversocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    
    #(sender_ip, sender_tid) = sender_addr # When do we get the TID?     
    # Check if we are putting a file or getting a file and send
    #  the corresponding request.
    if direction == TFTP_GET:
        current_blocknr = 1
        p = make_packet_rrq(fd.name, MODE_OCTET)
        serversocket.sendto(p, (ip, port))

    elif direction == TFTP_PUT:
        current_blocknr = 0
        p = make_packet_wrq(fd.name, MODE_OCTET)
        serversocket.sendto(p, (ip, port))  
        read_file = fd.read()
        bytes_left = len(read_file)
        print bytes_left
        print "PUT ok!"
        # create packet
        # send
    else:
        print "Error in direction"
    
    # Put or get the file, block by block, in a loop.
    last_packet = False
    while True:    

        # GET -------------------------------------------------------------------------------
        (rl,wl,xl) = select.select([serversocket],[],[], TFTP_TIMEOUT)
        try: 
            if serversocket in rl:
                (block, sender_addr) = serversocket.recvfrom(BLOCK_SIZE + 4)
                pkt = parse_packet(block) #packerterar upp paketet 
                try:
                    (opcode, _,_) = pkt
                except ValueError as e:
                    print "GOT AN ERROR"

                if opcode == OPCODE_DATA:
                    (opcode, blocknr, data) = pkt
                    print "RECEIVED BLOCK " + str(blocknr)
                    if current_blocknr == blocknr:
                    #check if we got the right TID from the sender
                    #if (sender_tid == x_tid):
                        fd.write(data)
                        if len(block) < BLOCK_SIZE + 4: 
                            last_packet = True

                        (rl,wl,xl) = select.select([],[serversocket],[], TFTP_TIMEOUT)
                        if serversocket in wl:
                            ack = make_packet_ack(blocknr)
                            serversocket.sendto(ack, sender_addr)
                            current_blocknr += 1
                            print "Sent ack for: " + str(blocknr)
                            print "------------------------------------"
                            if last_packet == True:
                                break
                        else: 
                            ack = make_packet_ack(current_blocknr)
                            serversocket.sendto(ack, sender_addr)
                            #if wrong ack, server pls resend ack 
                            #send ack -1
                    else:
                        (rl,wl,xl) = select.select([],[serversocket],[], TFTP_TIMEOUT)
                        if serversocket in wl:
                            ack = make_packet_ack(blocknr)
                            serversocket.sendto(ack, sender_addr)
                            print "RE-Sent ack for: " + str(blocknr)
                            print "------------------------------------"









                elif opcode == OPCODE_ACK:
                    print "OPCODE NUMBER:  " + str(opcode)
                    (opcode, blocknr, _) = pkt 
                    
                    if current_blocknr == blocknr:

                        if (bytes_left < BLOCK_SIZE):
                            current_blocknr += 1
                            blocknr += 1
                            data_packet = make_packet_data(blocknr, read_file[(BLOCK_SIZE * current_blocknr): (BLOCK_SIZE * current_blocknr)+ bytes_left])  
                            bytes_left -= bytes_left
                            if bytes_left == 0:
                                break
                            print ">>>>BLOCKNR:  " + str(blocknr) 
                            print ">>>>DATA PACKET: " + str(data_packet)
                            print ">>>>CURRENT BLOCKNR:  " + str(current_blocknr)
                           
                        else:  
                            current_blocknr += 1
                            blocknr += 1     
                            data_packet = make_packet_data(blocknr, read_file[(BLOCK_SIZE * current_blocknr): (BLOCK_SIZE * current_blocknr)+ BLOCK_SIZE])
                            bytes_left -= BLOCK_SIZE
                            #print "BLOCKNR:  " + str(blocknr) 
                            #print "CURRENT BLOCKNR:  " + str(current_blocknr)
                            #print "DATA PACKET: " + str(data_packet)

                        serversocket.sendto(data_packet, sender_addr)
                    

                    else: 
                        print "er"
                        #error duplicate ack 
                
                elif opcode == OPCODE_ERR:
                    (opcode, errcode, errmsg) = pkt
                    (opcode, errcode, errmsg) = pkt
                    print "ERR", errcode, errmsg
                # Wait for packet, write the data to the filedescriptor or
                # read the next block from the file. Send new packet to server.

                # Don't forget to deal with timeouts and received error packets.
                pass
        except: 
            serversocket.sendto(p, (ip, port))
            
    print "DONE"
    fd.close() 



def usage():
    """Print the usage on stderr and quit with error code"""
    sys.stderr.write("Usage: %s [-g|-p] FILE HOST\n" % sys.argv[0])
    sys.exit(1)


def main():
    # No need to change this function
    # select
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