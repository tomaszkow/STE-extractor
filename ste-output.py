#!/usr/bin/python
# -*- coding: utf8 -*-

import logging

nodes_filename_suffix = ".nodes"
elements_filename_suffix = ".elements"

def main():
    '''Command line runner for STE extractor''' 

    from optparse import OptionParser
    import sys

    # command line parsing
    usage = "usage: %prog [options] STE_input_file"
    parser = OptionParser(usage=usage)
    parser.add_option("-l", "--log", default="INFO",
                      action="store", type="string", dest="loglevel",
                      help="how many status messages do you want? "+
                        "(error,WARN,info,debug)")

    (options, args) = parser.parse_args()

    # handling options

    # assuming loglevel is bound to the string value obtained from the
    # command line argument. Convert to upper case to allow the user to
    # specify --log=DEBUG or --log=debug
    numeric_loglevel = getattr(logging, options.loglevel.upper(), None)
    if not isinstance(numeric_loglevel, int):
        logging.warn('Can not set log level "{}" (is not: error, warn, info or debug). Falling back to warn.'.format(options.loglevel))
        numeric_loglevel = getattr(logging, 'warn', None)
    logging.basicConfig(level=numeric_loglevel)

    # parsing args
    if 1 != len(args):
        sys.stderr.write('The only arg expected is a STE file name but ' +
                         str(len(args)) + ' where found:\n' +
                         '\t\n'.join(args) + '\n')
        sys.exit(1)

    # here is the only arg 
    ste_filename = args[0] 
    
    # let us get to work
    extract_stress_to_files(ste_input_filename=ste_filename,
                            elements_output_filename=ste_filename+elements_filename_suffix,
                            nodes_output_filename=ste_filename+nodes_filename_suffix)

    sys.exit(0)


def extract_stress_to_files(ste_input_filename, elements_output_filename, nodes_output_filename):
    '''Extracts stress from STE file and saves it into 2 files:
       - stress in nodes
       - stress in elements
    '''

    import struct
    import time
    import datetime

    output = []
    out_nod=[]

    output.append(('%8s %16s %16s %16s %16s %16s %16s\n')%('Element','SX','SY','SZ','TXY','TXZ','TYZ'))
    out_nod.append(('%8s %16s %16s %16s %16s %16s %16s\n')%('Node','SX','SY','SZ','TXY','TXZ','TYZ'))

    t0 = time.time()

    f = open(ste_input_filename, "rb")
    data = f.read(-1) #read whole file
    f.close()
    t1 = time.time() - t0

    elem_no = struct.unpack('i',data[12:16])[0]
    node_no = struct.unpack('i',data[36:40])[0]
    data_size = struct.unpack('i',data[28:32])[0] # ilosc 4-bajtowych liczb
    data_start = struct.unpack('i',data[80:84])[0]
    byte_no = int(struct.unpack('f',data[data_start+4:data_start+8])[0])
    mesh_type = int(struct.unpack('f',data[data_start+12:data_start+16])[0])
    logging.info('Calculation element No.: %i' % (elem_no))
    logging.info('Calculation node No.: %i' % (node_no)) #, data_size, data_start, byte_no, mesh_type
    elem_no = int(data_size / 189)
    logging.info('Real elem No: %i' % (elem_no))

    start = data_start
    mpa = 1000000
    output_node =[[0]*7 for i in range(node_no)]
    real_node_no = 0.0

    for i in xrange(0, elem_no):
       
        elem = int(struct.unpack('f',data[start:start+4])[0])
        dat = struct.unpack('6f',data[start+56:start+80])
        output.append( '%8d %16.6e %16.6e %16.6e %16.6e %16.6e %16.6e \n' % (elem, dat[0]/mpa, dat[1]/mpa, dat[2]/mpa, dat[3]/mpa, dat[4]/mpa, dat[5]/mpa) )
        
        nod_dat = struct.unpack(str(mesh_type*8)+'f',data[start+116:start+116+mesh_type*32])
        
        for k in range (0, mesh_type):
            int_val = int(nod_dat[0+8*k])
            if real_node_no < int_val:
                real_node_no = int_val
                
            nod = output_node[int_val-1]
            nod[0] = nod[0] +1
            
            for j in range(1,7):
                nod[j] = nod[j]+ nod_dat[j+8*k]

        start = start + 4 * byte_no

    logging.info('Real node No: %i' % (real_node_no))
    for i in range(real_node_no):
        nod = output_node[i]
        out_nod.append('%8d %16.6e %16.6e %16.6e %16.6e %16.6e %16.6e \n' % (i+1,  nod[1]/nod[0]/mpa, nod[2]/nod[0]/mpa, nod[3]/nod[0]/mpa, nod[4]/nod[0]/mpa, nod[5]/nod[0]/mpa, nod[6]/nod[0]/mpa))

    t2 = time.time() - t0
    f = open(elements_output_filename,"wb",64*1024)

    f.writelines(output)
    f.close

    f = open(nodes_output_filename,"wb",64*1024)
    f.writelines(out_nod)
    f.close

    t3 = time.time() - t0
    logging.info('Time of extraction: %6.3f sec' % (t3)) #, t1, t2, t3


if __name__ == "__main__":
    main()
