#!/usr/bin/python
# -*- coding: utf8 -*-

import logging

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
                        "(error,warn,INFO,debug)")

    (options, args) = parser.parse_args()

    # handling options

    # assuming loglevel is bound to the string value obtained from the
    # command line argument. Convert to upper case to allow the user to
    # specify --log=DEBUG or --log=debug
    numeric_loglevel = getattr(logging, options.loglevel.upper(), None)
    if not isinstance(numeric_loglevel, int):
        logging.warn('Can not set log level "{}" (is not: error, warn, info or debug). Falling back to info.'.format(options.loglevel))
        numeric_loglevel = getattr(logging, 'info', None)
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
    stress_extractor = STE_StressExtractor()
    stress_extractor.extract_stress_to_files(ste_input_filename=ste_filename)

    sys.exit(0)


# required by the extraction procedure not by the command line frontend

import struct
import time
import datetime
import io

class STE_StressExtractor:
    '''STE_StressExtractor extracts stress values for nodes and elements from STE files'''

    # configuration
    nodes_filename_suffix = ".nodes"
    elements_filename_suffix = ".elements"
    read_buffer_size = 64*1024
    write_buffer_size = 64*1024

    def __init__(self):
        self._ste_input = None
        self._elements_output = None
        self._nodes_output = None

    def extract_stress_to_files(self, ste_input_filename, elements_output_filename="", nodes_output_filename=""):
        '''Extracts stress from ste_input_filename file and saves it into 2 files:
           - stress values for nodes are saved in nodes_output_filename file
           - stress values for elements are saved in elements_output_filename file

           If no output file name was specified a suffixed ste_input_filename will be used. 
        '''
        
        logging.info("Opening files...")
        self._ste_input = io.open(ste_input_filename, "rb", self.read_buffer_size)

        if ("" == elements_output_filename):
            elements_output_filename = ste_input_filename+self.elements_filename_suffix
        self._elements_output = io.open(elements_output_filename, "wb", self.write_buffer_size)
        self._elements_output.write('%8s %16s %16s %16s %16s %16s %16s\n'%('Element','SX','SY','SZ','TXY','TXZ','TYZ'))

        if ("" == nodes_output_filename):
            nodes_output_filename = ste_input_filename+self.nodes_filename_suffix
        self._nodes_output = io.open(nodes_output_filename, "wb", self.write_buffer_size)
        self._nodes_output.write('%8s %16s %16s %16s %16s %16s %16s\n'%('Node','SX','SY','SZ','TXY','TXZ','TYZ'))

        self._extract_stress()

        logging.info("Closing files...")
        self._ste_input.close()
        self._elements_output.close()
        self._nodes_output.close()


    def _element_formater(self, element_nr, element_stress):
        '''Formats stress values for an element into a string'''
        return '%8d %16.6e %16.6e %16.6e %16.6e %16.6e %16.6e\n' % (element_nr, element_stress[0], element_stress[1], element_stress[2], element_stress[3], element_stress[4], element_stress[5])


    def _save_element(self, element_nr, element_stress):
        '''Formats and saves stress values for an element into _elements_output'''
        self._elements_output.write(self._element_formater(element_nr, element_stress))


    def _node_formater(self, node_nr, node_stress):
        '''Formats stress values for a node into a string'''
        return "%8d %16.6e %16.6e %16.6e %16.6e %16.6e %16.6e\n" % (node_nr, node_stress[0], node_stress[1], node_stress[2], node_stress[3], node_stress[4], node_stress[5])


    def _save_node(self, node_nr, node_stress):
        '''Formats and saves stress values for a node into _nodes_output'''
        self._nodes_output.write(self._node_formater(node_nr, node_stress))


    def _extract_stress(self):
        '''Extracts stress values from _ste_input stream for:
           - nodes (saved by _save_node)
           - elements (saved by _save_element)
        '''

        t0 = time.time()

        logging.info("Reading header...")
        data = self._ste_input.read(-1) #read whole file

        elem_no = struct.unpack('i',data[12:16])[0]
        node_no = struct.unpack('i',data[36:40])[0]
        data_size = struct.unpack('i',data[28:32])[0] # ilosc 4-bajtowych liczb
        data_start = struct.unpack('i',data[80:84])[0]
        byte_no = int(struct.unpack('f',data[data_start+4:data_start+8])[0])
        mesh_type = int(struct.unpack('f',data[data_start+12:data_start+16])[0])
        logging.debug('Calculation element No.: %i' % (elem_no))
        logging.debug('Calculation node No.: %i' % (node_no)) #, data_size, data_start, byte_no, mesh_type
        elem_no = int(data_size / 189)
        logging.debug('Real elem No: %i' % (elem_no))

        start = data_start
        mpa = 1000000
        output_node =[[0]*7 for i in range(node_no)]
        real_node_no = 0.0

        logging.info("Extracting stress values. Elements are saved. Nodes are computed. (It takes a while)...")
        for i in xrange(0, elem_no):
           
            elem = int(struct.unpack('f',data[start:start+4])[0])
            dat = struct.unpack('6f',data[start+56:start+80])
            self._save_element(elem, (dat[0]/mpa, dat[1]/mpa, dat[2]/mpa, dat[3]/mpa, dat[4]/mpa, dat[5]/mpa) )
            
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

        logging.info("Saving stress values for nodes...")
        logging.debug('Real node No: %i' % (real_node_no))
        for i in range(real_node_no):
            nod = output_node[i]
            self._save_node(i+1, (nod[1]/nod[0]/mpa, nod[2]/nod[0]/mpa, nod[3]/nod[0]/mpa, nod[4]/nod[0]/mpa, nod[5]/nod[0]/mpa, nod[6]/nod[0]/mpa))

        t3 = time.time() - t0
        logging.debug('Time of extraction: %6.3f sec' % (t3))


if __name__ == "__main__":
    main()
