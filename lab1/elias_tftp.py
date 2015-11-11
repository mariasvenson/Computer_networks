#! /usr/bin/python
# https://pymotw.com/2/struct/
import sys,socket,struct,select, hashlib

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

#TFTP_PORT= 13069
TFTP_PORT= 6969

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



def tftp_transfer(fd, hostname, direction):
    
    # Open socket interface
    host = socket.getaddrinfo(hostname, TFTP_PORT)
    ip = host[0][4][0]
    port = host[0][4][1]
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_TID = None
    last_packet = False

       
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
        p = make_packet_wrq(fd.name, MODE_OCTET)
        read_file = fd.read()
        bytes_left = len(read_file)
        print "Sending WRQ packet"
    else:
        print "No valid direction"

    # Send the just created packet
    (bytes) = s.sendto(p, (ip, port))  
    
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
                        if len(block) < BLOCK_SIZE + 4: 
                            last_packet = True

                        packet = make_packet_ack(blocknr)
                        current_blocknr += 1
                        print "Sending ACK for block: " + str(blocknr)
                        print "------------------------------------"


                    # Else, received wrong (a duplicate) DATA block, RE-Send the previous ACK
                    else:
                        packet = make_packet_ack(blocknr)
                        resend_count += 1
                        print "Duplicate!"
                        print "RE-Sending ACK for block: " + str(blocknr) + ", resend count: " + str(resend_count)
                        print "------------------------------------"


                # PUT ----------------------------
                #If what we received is ACK, did we get the expected block?
                #If yes, create DATA packet for the next block
                #If not, create DATA packet for the previous block
                elif opcode == OPCODE_ACK and direction == TFTP_PUT:

                    (opcode, blocknr, _) = pkt 
                    print "RECEIVED ACK BLOCKNR: " + str(blocknr)
                    
                    # If received correct ACK block, create next DATA block
                    if current_blocknr == blocknr:
                        resend_count = 0
                        current_blocknr += 1
                        blocknr += 1

                        # If last DATA packet to send, set the last_packet-flag TRUE
                        if(bytes_left < BLOCK_SIZE):
                            n_bytes = bytes_left
                            bytes_left -= bytes_left
                            msg = "Sending last"
                            if bytes_left == 0:
                                last_packet = True
                            
                        # Else create normal block_size'd DATA packet
                        else:     
                            n_bytes = BLOCK_SIZE
                            bytes_left -= BLOCK_SIZE
                            msg = "Sending"
                        
                        data_block = read_file[(BLOCK_SIZE * current_blocknr) : (BLOCK_SIZE * current_blocknr) + n_bytes]
                        packet = make_packet_data(blocknr, data_block)
                        print msg + " block: " + str(blocknr)
                        print "------------------------------------"
                        
                    
                    # Else, received wrong ACK block, RE-create the previous DATA block
                    else:
                        packet = make_packet_data(current_blocknr, read_file[(BLOCK_SIZE * current_blocknr): (BLOCK_SIZE * current_blocknr)+ BLOCK_SIZE])
                        resend_count += 1
                        print "Duplicate!"
                        print "Resending block: " + str(current_blocknr) + ", resend count: " + str(resend_count)
                        print "------------------------------------"
                    

                # SEND PACKET MADE IN GET OR PUT ---------------
                (rl,wl,xl) = select.select([], [s], [], TFTP_TIMEOUT)
                if s in wl: 
                    (bytes) = s.sendto(packet, sender_addr)
                    if last_packet == True: 
                        break
                else:
                    print "Send packet timed out!"


            # Initial request timed out
            else:
                # If RRQ packet was lost, resend
                if direction == TFTP_GET and current_blocknr == 1:
                    (bytes) = s.sendto(packet, sender_addr)
                    print "Timeout! Resent RRQ packet"

                # Else if WRQ packet was lost, resend
                elif direction == TFTP_PUT and current_blocknr == 0:
                    (bytes) = s.sendto(packet, sender_addr)
                    print "Timeout! Resent WRQ packet"

                # If failed to resend packet too many times and the server stop responding
                elif resend_count > 3:
                    print "Retried to send packet to many times. Restart request"
                    if direction == TFTP_GET:
                        current_blocknr = 1
                        p = make_packet_rrq(fd.name, MODE_OCTET)
                    elif direction == TFTP_PUT:
                        current_blocknr = 0
                        p = make_packet_wrq(fd.name, MODE_OCTET)
                    else:
                        print "Invalid direction"
                    fd.seek(0)
                    (bytes) = s.sendto(p, sender_addr)

                # No response yet
                #else:
                #print "Timeout!"

    # EXCEPTION ---------------------------------------------------------------------------           
        except: 
            print "Exception!!"
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

    try:
        if direction == TFTP_GET:
            with open(filename, "rb") as fd:
                d = fd.read()

    except IOError as e:
        sys.stderr.write("File error (%s): %s\n" % (filename, e.strerror))
        sys.exit(2)

    md5 = hashlib.md5(d).hexdigest()
    print md5
    print str(len(d))
    if filename == "small.txt":
        true_md5 = "667ff61c0d573502e482efa85b468f1f"
        true_size = 1931
    elif filename == "medium.pdf":
        true_md5 = "ee98d0524433e2ca4c0c1e05685171a7"
        true_size = 17577
    elif filename == "large.jpeg":
        ture_size = 82142
        true_md5 = "f5b558fe29913cc599161bafe0c08ccf"

    if md5 == true_md5 and len(d) == true_size:
        print "True"
    else:
        print "False"

if __name__ == "__main__":
    main()