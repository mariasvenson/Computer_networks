FILES
=====

This archive contains the following two files:

tftp.py
This is the only file that you should edit. Look through it and read
the comments. Note that TODO marks places where you should insert/edit code.

README.txt
This file.
 
PROGRAMMING
===========

Now you are ready to start programming the client that should be able to GET a
file from a server as well as PUT a file onto a server.

You will need to extend the skeleton code in tftp.py and do the following:
 * Write the socket handling code to open the socket to the server (code for
   closing the socket is provided).
 * Construct packets according to the standard. Send, receive, and parse all
   packet types:
    - Read request packets
    - Write request packets
    - Acknowledgment packets
    - Data packets
 * Handle receiving data and perform the appropriate action
    - Write data to file
    - Read data from file and send to server
    - Handle errors from server and time outs


RUNNING
=======

To run the program and get the file small.txt from the server joshua.it.uu.se
simply type (this will of course not work until you have implemented what is
necessary)

 ./tftp.py -g small.txt joshua.it.uu.se


ADDITIONAL INFORMATION
======================

General documentation on Python can be found here: https://www.python.org/doc/

In particular you need to look at the modules socket and struct:
 * https://docs.python.org/2/library/socket.html
 * https://docs.python.org/2/library/struct.html
You may also look at the module select:
 * https://docs.python.org/2/library/select.html

Further notes:
 * Always use mode=MODE_OCTET, it is enough.
 * Take care of the network byte order
 * Pay attention to signed/unsigned numbers
 * Do not lookup DNS names more than once. Find the server IP address by
   using, for instance, socket.getaddrinfo().

Always see the document addition_info.pdf from the C-language code skeleton.
There are further information that also applies to other languages (especially
sections 1.1, 1.3, and 1.4).

