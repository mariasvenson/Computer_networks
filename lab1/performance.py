import tftp

times_6969 = []
times_11069 = []
# times_12069 = []
# times_13069 = []

times_6969.append(tftp.main2("small.txt",1,"rabbit.it.uu.se",6969))
times_6969.append(tftp.main2("medium.pdf",1,"rabbit.it.uu.se",6969))
times_6969.append(tftp.main2("large.jpeg",1,"rabbit.it.uu.se",6969))
times_6969.append(tftp.main2("new_small.txt",2,"rabbit.it.uu.se",6969))
times_6969.append(tftp.main2("new_medium.pdf",2,"rabbit.it.uu.se",6969))
times_6969.append(tftp.main2("new_large.jpeg",2,"rabbit.it.uu.se",6969))

times_11069.append(tftp.main2("small.txt",1,"rabbit.it.uu.se",11069))
times_11069.append(tftp.main2("medium.pdf",1,"rabbit.it.uu.se",11069))
times_11069.append(tftp.main2("large.jpeg",1,"rabbit.it.uu.se",11069))
times_11069.append(tftp.main2("new_small.txt",2,"rabbit.it.uu.se",11069))
times_11069.append(tftp.main2("new_medium.pdf",2,"rabbit.it.uu.se",11069))
times_11069.append(tftp.main2("new_large.jpeg",2,"rabbit.it.uu.se",11069))

# times_12069.append(tftp.main2("small.txt",1,"rabbit.it.uu.se",12069))
# times_12069.append(tftp.main2("medium.pdf",1,"rabbit.it.uu.se",12069))
# times_12069.append(tftp.main2("large.jpeg",1,"rabbit.it.uu.se",12069))
# times_12069.append(tftp.main2("new_small.txt",2,"rabbit.it.uu.se",12069))
# times_12069.append(tftp.main2("new_medium.pdf",2,"rabbit.it.uu.se",12069))
# times_12069.append(tftp.main2("new_large.jpeg",2,"rabbit.it.uu.se",12069))

# times_13069.append(tftp.main2("small.txt",1,"rabbit.it.uu.se",13069))
# times_13069.append(tftp.main2("medium.pdf",1,"rabbit.it.uu.se",13069))
# times_13069.append(tftp.main2("large.jpeg",1,"rabbit.it.uu.se",13069))
# times_13069.append(tftp.main2("new_small.txt",2,"rabbit.it.uu.se",13069))
# times_13069.append(tftp.main2("new_medium.pdf",2,"rabbit.it.uu.se",13069))
# times_13069.append(tftp.main2("new_large.jpeg",2,"rabbit.it.uu.se",13069))

print "--------------------------" 
print "Performance, PORT: 6969" 

for t in times_6969:
	print " Time: " + str(t) 

print "--------------------------" 

print "--------------------------" 
print "Performance, PORT: 11069" 

for t in times_11069:
	print " Time: " + str(t) 

print "--------------------------" 

# print "--------------------------" 
# print "Performance, PORT: 12069" 

# for t in times_12069:
# 	print " Time: " + str(t) 

# print "--------------------------" 

# print "--------------------------" 
# print "Performance, PORT: 13069" 

# for t in times_13069:
# 	print " Time: " + str(t) 

# print "--------------------------" 

