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
        data = self._ste_input.read(84)
        nr_of_elements = struct.unpack_from('i',data,12)[0]
        nr_of_nodes = struct.unpack_from('i',data,36)[0]
        data_size = struct.unpack_from('i',data,28)[0] # 4B numbers count
        data_start = struct.unpack_from('i',data,80)[0]

        # all elements have the same number of nodes
        # the size of a record holding a single element with it's nodes is constant
        self._ste_input.seek(data_start)
        data = self._ste_input.peek(16)
        record_size = int(struct.unpack_from('f',data,4)[0])
        nodes_per_element = int(struct.unpack_from('f',data,12)[0])

        logging.debug('Expecting %i elements' % (nr_of_elements))
        logging.debug('Expecting %i nodes' % (nr_of_nodes)) 
        nr_of_elements = int(data_size / 189)
        logging.debug('Real elem No: %i' % (nr_of_elements))

        mpa = 1000000 # 1MPa = 10**6 Pa
        nodes =[[0]*7 for i in xrange(nr_of_nodes)]

        logging.info("Extracting stress values. Elements are saved. Nodes are computed. (It takes a while)...")
        for i in xrange(0, nr_of_elements):
            data = self._ste_input.read(4*record_size)
           
            # extracting stress values for an element
            element_no = int(struct.unpack_from('f',data,0)[0])
            element_stress = struct.unpack_from('6f',data,56)
            self._save_element(element_no, (element_stress[0]/mpa, element_stress[1]/mpa, 
                                            element_stress[2]/mpa, element_stress[3]/mpa,  
                                            element_stress[4]/mpa, element_stress[5]/mpa))
            
            # extracting stress values for nodes in this element
            raw_nodes = struct.unpack_from(str(nodes_per_element*8)+'f',data,116)
            
            for node_in_element_no in range (0, nodes_per_element):
                node_no = int(raw_nodes[8*node_in_element_no])

                n = nodes[node_no-1] # stress data for this node found so far
                n[0] += 1 # counting elements that share this node
                
                # summing up stress values for this node
                for j in xrange(1,7):
                    n[j] += raw_nodes[j+8*node_in_element_no]

        logging.info("Saving stress values for nodes...")
        # dividing stress values for a node by number of elements that share this node
        for node_no, n in enumerate(nodes):
            if 0 < n[0]:
                self._save_node(node_no+1, (n[1]/n[0]/mpa, n[2]/n[0]/mpa, n[3]/n[0]/mpa, 
                                            n[4]/n[0]/mpa, n[5]/n[0]/mpa, n[6]/n[0]/mpa))

        t3 = time.time() - t0
        logging.debug('Time of extraction: %6.3f sec' % (t3))


if __name__ == "__main__":
    main()
