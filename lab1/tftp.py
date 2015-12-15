#! /usr/bin/python
import sys,socket,struct,select,time,hashlib

BLOCK_SIZE= 512

# 512 + header (4)

#TFTP header consists of a 2 byte opcode field which indicates the packet's type
OPCODE_RRQ = 1
OPCODE_WRQ = 2
OPCODE_DATA = 3
OPCODE_ACK = 4
OPCODE_ERR = 5

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
    if opcode == OPCODE_RRQ or opcode == OPCODE_WRQ:
        l = msg[2:].split('\0')
        if len(l) != 3:
            return None
        return opcode, l[1], l[2]
    
    elif opcode == OPCODE_DATA:
        block = struct.unpack("!H", msg[2:4])[0]
        return opcode, block, msg[4:] 
    
    elif opcode == OPCODE_ACK:
        block = struct.unpack("!H", msg[2:])[0]
        return opcode, block, msg[4:]
    
    elif opcode == OPCODE_ERR:
        errcode = struct.unpack("!H", msg[2:4])[0]
        errmsg = msg[4:-1]
        return opcode, errcode, errmsg
    else:
        return None 



def tftp_transfer(fd, hostname, direction, port):
    
    # Open socket interface
    (family, socktype, proto, canonname, sockaddr) = socket.getaddrinfo(hostname, port)[0]
    s = socket.socket(family, socktype, proto)
    server_TID = None
    last_packet = False
    total_packet_lost = 0
       
    # Check if we are putting a file or getting a file and create 
    # the corresponding packet and send it
    if direction == TFTP_GET:
        RECEIVE_SIZE = BLOCK_SIZE + 4
        current_blocknr = 1
        p = make_packet_rrq(fd.name, MODE_OCTET)
        print "Sending RRQ packet"

    elif direction == TFTP_PUT:
        RECEIVE_SIZE = 4
        current_blocknr = 0
        blocknr = 0
        p = make_packet_wrq(fd.name, MODE_OCTET)
        bytes_left = 0
        bytes_leftx = 0
    else:
        print "No valid direction"

    # Send the just created packet
    (bytes) = s.sendto(p, sockaddr)  
    
    # Put or get the file, block by block, in a loop.
    while True:

        # Listen and wait until received a packet
        (rl,wl,xl) = select.select([s],[],[],TFTP_TIMEOUT)
        try: 

            # If received from server, read and unpack the packet
            if s in rl:
                (block, sender_addr) = s.recvfrom(RECEIVE_SIZE)
                (host_IP, host_TID) = sender_addr
                pkt = parse_packet(block) 
                
                if server_TID == None:
                    server_TID = host_TID

                # If received packet with wrong TID, send ERR packet to the source
                elif server_TID != host_TID:
                    error_pack = make_packet_err(5, ERROR_CODES[5])
                    s.sendto(error_pack, sender_addr)
                    continue 

                (opcode, _,_) = pkt



                # RECEIVED ERROR PACKET ---------
                if opcode == OPCODE_ERR:
                    (opcode, errcode, errmsg) = pkt
                    print "RECEIVED ERROR PACKET", errcode, errmsg
                    break

                # GET ---------------------------
                #If what we received is DATA, did we get the expected block?
                #If yes, create ACK packet for the received block
                #If not, create ACK packet for the previous block

                elif opcode == OPCODE_DATA and direction == TFTP_GET:
                    (opcode, blocknr, data) = pkt
                    print "RECEIVED DATA BLOCKNR " + str(blocknr)
                    
                    # If received correct DATA block, write data to file and send ACK
                    if current_blocknr == blocknr:
                        resend_count = 0

                        fd.write(data)

                        # If last packet, set the last_packet-flag TRUE
                        if len(data) < BLOCK_SIZE: 
                            last_packet = True

                        packet = make_packet_ack(blocknr)
                        current_blocknr += 1
                        print "Sending ACK for block: " + str(blocknr)
                        


                    # Else, received wrong (a duplicate) DATA block, RE-Send the previous ACK
                    else:
                        packet = make_packet_ack(blocknr)
                        total_packet_lost += 1
                        resend_count += 1
                        print "Duplicate!"
                        print "RE-Sending ACK for block: " + str(blocknr) + ", resend count: " + str(resend_count)


                # PUT ----------------------------
                #If what we received is ACK, did we get the expected block?
                #If yes, create DATA packet for the next block
                #If not, create DATA packet for the previous block
                elif opcode == OPCODE_ACK and direction == TFTP_PUT:
                    (opcode, blocknr, _) = pkt
                    print "RECEIVED ACK BLOCKNR: " + str(blocknr)
                    #print "Current BLOCK NR: " +str(current_blocknr)
                    
                    # If received correct ACK block, create next DATA block
                    if current_blocknr == blocknr:
                        resend_count = 0
                        current_blocknr += 1
                        blocknr += 1
                        data_block = fd.read(BLOCK_SIZE)
  
                        # If last DATA packet to send, set the last_packet-flag TRUE
                        # if blx to small, do not send moar
                        if(len(data_block) < BLOCK_SIZE):
                            msg = "Sending last"
                            last_packet = True
                            
                        # Else create normal block_size'd DATA packet
                        else:
                            msg = "Sending"

                        packet = make_packet_data(blocknr, data_block)
                        print "Sending " +str(len(data_block)) +" bytes of data"
                        print msg + " block: " + str(blocknr)
                    else:
                        total_packet_lost += 1
                        resend_count += 1
                        (_, blocknr, _) = parse_packet(packet)
                        print "Wrong ACK number! Resend last ACK, block " + str(blocknr)
                    

                # SEND PACKET MADE IN GET OR PUT ---------------
                print "------------------------------------"
                (bytes) = s.sendto(packet, sender_addr)
                if last_packet == True:
                    break


            # Initial request timed out
            else:
                # If RRQ packet was lost, resend
                if direction == TFTP_GET and current_blocknr == 1:
                    (bytes) = s.sendto(p, sender_addr)
                    print "Timeout! Resent RRQ packet"

                # Else if WRQ packet was lost, resend
                elif direction == TFTP_PUT and current_blocknr == 0:
                    (bytes) = s.sendto(p, sender_addr)
                    print "Timeout! Resent WRQ packet"

                # If failed to resend packet too many times and the server stop responding
                elif resend_count > 3:
                    print "Retried to send packet to many times. Terminating request"
                    break

                # No response yet
                #else:
                    #print "Timeout!"

    # EXCEPTION ---------------------------------------------------------------------------           
        except: 
            print "Exception!!"
    s.close()


def usage():
    """Print the usage on stderr and quit with error code"""
    sys.stderr.write("Usage: %s [-g|-p] FILE HOST\n" % sys.argv[0])
    sys.exit(1)

# MAIN_2 ---------------------------------------------------------------------------   
def main_performance(filename, direction, hostname, port, n_iterations):
    TFTP_PORT= port
    # No need to change this function
    if direction == TFTP_GET:
        print "Transfer file %s from host %s" % (filename, hostname)
    else:
        print "Transfer file %s to host %s" % (filename, hostname)

    total_time = 0

    for i in range(0,n_iterations):
        try:
            if direction == TFTP_GET:
                fd = open(filename, "wb")
            else:
                fd = open(filename, "rb")
        except IOError as e:
            sys.stderr.write("File error (%s): %s\n" % (filename, e.strerror))
            sys.exit(2)
        start = time.time()
        tftp_transfer(fd, hostname, direction, port)
        stop = time.time()
        time_taken = stop-start
        print "Time taken: " + str(time_taken) + ", Iteration: " + str(i)
        print "++++++++++++++++++++++++++++++++++++"
        print "\n"
        total_time += time_taken
        fd.close()

    average_time = total_time/n_iterations
    print "Average time taken: " + str(average_time)
    return average_time


# MAIN ---------------------------------------------------------------------------   

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

    tftp_transfer(fd, hostname, direction, TFTP_PORT)
    fd.close()

    if direction == TFTP_GET:
        with open(filename, "rb") as fd:
            d = fd.read()
        md5 = hashlib.md5(d).hexdigest()
        print md5
        print str(len(d))
        if filename == "small.txt" or filename == "ensmall.txt":
            true_md5 = "667ff61c0d573502e482efa85b468f1f"
            true_size = 1931
        elif filename == "medium.pdf" or filename == "enmedium.pdf":
            true_md5 = "ee98d0524433e2ca4c0c1e05685171a7"
            true_size = 17577
        elif filename == "large.jpeg" or filename == "enlarge.jpeg":
            true_md5 = "f5b558fe29913cc599161bafe0c08ccf"
            true_size = 82142

        print true_md5
        if md5 == true_md5 and len(d) == true_size:
            print "True"
        else:
            print "False"

if __name__ == "__main__":
    main()
