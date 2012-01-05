import struct, os, time, pickle, datetime
from tkFileDialog   import askopenfilename
from Tkinter import *

output = []
out_nod=[]

master = Tk()
master.withdraw() #hiding tkinter window
 
filename = askopenfilename(title="Otworz plik", filetypes=[("Pliki ste",".ste"),("Wszystkie pliki",".*")])
 
if filename == "":
   print "you didn't open anything!" 
master.quit()

print filename.split('/')[-1]

now = datetime.datetime.now()
text = ' Stress extracter made by Leszek Wittenbeck \n Version 1.0 - 3.06.2011 \n Data extracted from file: '+filename+'\n Date and time of extraction: '+ now.strftime("%Y-%m-%d %H:%M")+'\n'
output.append(text)
output.append(('%8s %16s %16s %16s %16s %16s %16s\n')%('Element','SX','SY','SZ','TXY','TXZ','TYZ'))
out_nod.append(text)
out_nod.append(('%8s %16s %16s %16s %16s %16s %16s\n')%('Node','SX','SY','SZ','TXY','TXZ','TYZ'))

t0 = time.time()

#filename ="element-Badanie 1.STE"
filesize =os.path.getsize(filename)
name = os.path.splitext(filename)[0]

f = open(filename, "rb")
data = f.read(filesize)
f.close()
t1 = time.time() - t0

elem_no = struct.unpack('i',data[12:16])[0]
node_no = struct.unpack('i',data[36:40])[0]
data_size = struct.unpack('i',data[28:32])[0] # ilosc 4-bajtowych liczb
data_start = struct.unpack('i',data[80:84])[0]
byte_no = int(struct.unpack('f',data[data_start+4:data_start+8])[0])
mesh_type = int(struct.unpack('f',data[data_start+12:data_start+16])[0])
print 'Calculation element No.: ',elem_no,'\nCalculation node No.:    ', node_no #, data_size, data_start, byte_no, mesh_type
elem_no = int(data_size / 189)
print 'Real elem No: ',elem_no

start = data_start
mpa = 1000000
output_node =[[0]*7 for i in range(node_no)]
#print len(output_node[0])
real_node_no = 0.0

for i in xrange(0, elem_no):
   
    elem = int(struct.unpack('f',data[start:start+4])[0])
    dat = struct.unpack('6f',data[start+56:start+80])
    output.append( '%8d %16.6e %16.6e %16.6e %16.6e %16.6e %16.6e \n' % (elem, dat[0]/mpa, dat[1]/mpa, dat[2]/mpa, dat[3]/mpa, dat[4]/mpa, dat[5]/mpa) )
    
    nod_dat = struct.unpack(str(mesh_type*8)+'f',data[start+116:start+116+mesh_type*32])
    #print len(nod_dat)
    #print len(output_node)
    
    for k in range (0, mesh_type):
        int_val = int(nod_dat[0+8*k])
        if real_node_no < int_val:
            real_node_no = int_val
            
        nod = output_node[int_val-1]
        nod[0] = nod[0] +1
        
        for j in range(1,7):
            nod[j] = nod[j]+ nod_dat[j+8*k]

    start = start + 4 * byte_no

print 'Real node No: ', real_node_no 
for i in range(real_node_no):
    nod = output_node[i]
    out_nod.append('%8d %16.6e %16.6e %16.6e %16.6e %16.6e %16.6e \n' % (i+1,  nod[1]/nod[0]/mpa, nod[2]/nod[0]/mpa, nod[3]/nod[0]/mpa, nod[4]/nod[0]/mpa, nod[5]/nod[0]/mpa, nod[6]/nod[0]/mpa))

t2 = time.time() - t0
f = open(name+'_ele.txt',"wb",64*1024)

f.writelines(output)
f.flush

f = open(name+'_nod.txt',"wb",64*1024)
f.writelines(out_nod)
f.flush

t3 = time.time() - t0
print 'Time of extraction: %6.3f sec'%t3#, t1, t2, t3
