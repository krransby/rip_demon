"""
    COSC364: Assignment 1
    RIP routing demon
    Kayle Ransby (34043590)
    Sjaak Flick (36406121)
"""

import os
import sys
import socket
import threading
import random
import select

class router():
    """
    Rip routing demon class
    """

    router_ID = 0
    input_ports = []
    output_ports = {}

    input_sockets = []
    route_table = {}
    #Don't know what the collector was for..
    
    # Variable for threading
    packet_just_sent = False
    periodic_update_timer = 0

    def __init__(self, config):
        """
        Function to read the config file
        """
        
        # Open the given routers config file
        file = open(config)
        
        # List used for ensuring all parameter are applied (only once)
        required_parameters = ['router-id', 'input-ports', 'outputs']
        
        for line in file.readlines():
            if line != '\n' and line[0] != '#': # Allowing for empty lines and comments in config files
                
                currentLine = line.rstrip().split(' ')
                currentParameter = currentLine[0]
                
                # Set router ID
                if currentParameter == 'router-id':
                    
                    if currentParameter in required_parameters: # See if 'router-id' has been recieved yet
                        ID = int(currentLine[1])
                        
                        # Check if the router id is within the allowed range
                        if self.router_id_check(ID):
                            self.router_ID = ID
                        else:
                            self.error("Router ID ({}) not within range 1 <= x <= 64000".format(ID))
                        
                        required_parameters.remove(currentParameter) # remove 'router-id' from the required parameters list
                    else:
                        print("Router ID already set to {}. Omitting repeat declaration\n".format(self.router_ID))
                
                # Set input ports
                elif currentParameter == 'input-ports':
                    
                    if currentParameter in required_parameters: # See if 'input-ports' has been recieved yet
                        for portstr in currentLine[1:]:
                            port = int(portstr.rstrip(','))
                            
                            if self.port_check(port):
                                self.input_ports.append(port)
                            else:
                                self.error("Input port ({}) not within range 1024 <= x <= 65535".format(port))
                        
                        required_parameters.remove(currentParameter) # remove 'input-ports' from the required parameters list
                    
                    else:
                        print("Input ports already set. Omitting repeat declaration\n")
                
                
                # Set output ports
                elif currentParameter == 'outputs':
                    
                    if currentParameter in required_parameters: # See if 'outputs' has been recieved yet
                        for outputstr in currentLine[1:]:
                            
                            portstr, metricstr, idstr = outputstr.rstrip(',').split('-')
                            
                            if self.port_check(int(portstr)):
                                if self.router_id_check(int(idstr)):
                                    
                                    self.output_ports[int(idstr)] = (int(portstr), int(metricstr))
                                else:
                                    self.error("Output router ID ({}) not within range 1 <= x <= 64000".format(int(idstr)))
                            else:
                                self.error("Output port ({}) not within range 1024 <= x <= 65535".format(int(portstr)))
                        
                        required_parameters.remove(currentParameter) # remove 'outputs' from the required parameters list
                    else:
                        print("Output ports already set. Omitting repeat declaration\n")
                    
                    
                else: # Unknown parameter
                    print("'{}' is an unknown parameter, omitting line\n".format(currentParameter))
        
        # Close the demon if the required parameters are not supplied
        if len(required_parameters) > 0:
            self.error("Missing essential parameter(s): {}. shutting down.".format(', '.join(required_parameters)))
        
        # Close configuration file:
        file.close()
        
        # Bind input ports to a socket
        self.start_sockets()
        
        #I was testing adding entries to the route table, it probably shouln't be there..
        # All good, just checking :)
        
        # Start the infinite loop
        self.loop()
        
        return

    def router_id_check(self, ID):
        """
        Returns an error if the router id is out of the allowed range
        """
        return True if ID >= 1 and ID <= 64000 else False


    def port_check(self, port):
        """Returns an error if the port is out of the allowed range"""
        return True if port >= 1024 and port <= 64000 else False


    def metric_check(self, metric):
        """returns false if the metric is not within the bounds, will also trigger a dead-timer."""
        return True if metric > 0 and metric < 16 else False


    def rip_version_check(self, value):
        """Returns false if the rip version != 2, could indicate transmission error"""
        return True if value == 2 else False


    def error(self, message, exit_code = 1):
        """
        Print an error message in the console and close the demon
        """
        
        # Cancel the threading timer
        self.periodic_update_timer.cancel()
        
        if exit_code == 0:
            print("All is well, cya!")
        else:
            print("Error:", message)
        
        # Ensure that all input sockets are closed before exiting
        for sock in self.input_sockets:
            sock.close()
        
        sys.exit(exit_code)


    def start_sockets(self):
        """
        Bind each input port to a socket and add it to the list
        """
        try:
            for port in self.input_ports:
                if type(port) != type(1): # Checking to see if 'port' is an integer
                    break
                
                temp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # create a UDP socket
                temp_socket.settimeout(1.0)
                temp_socket.bind(('127.0.0.1', port))
                
                self.input_sockets.append(temp_socket)
        
        except socket.error:
            self.error("Error creating socket connection")


    def restart_socket(self, sock):
        """
        Starts an individual socket to prevent forcable closing
        """
        
        index = self.input_sockets.index(sock)
        self.input_sockets.remove(sock)
        sock.close()
        portNum = self.input_ports[index]
        
        try:
            
            temp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # create a UDP socket
            temp_socket.settimeout(1.0)
            temp_socket.bind(('127.0.0.1', portNum))
            
            self.input_sockets.insert(index, temp_socket)
            
        except socket.error:
            self.error("Error creating socket connection")


    def start_timers(self):
        """
        Starts the required timers for threading
        """
        
        # Create a thread timer for a periodic update
        # timerVal is the recommended range given on pg 7 of assignment handout
        timerVal = random.uniform((0.8 * 6), (1.2 * 6))
        self.periodic_update_timer = threading.Timer(timerVal, self.periodic_update)
        self.periodic_update_timer.start()


    def loop(self):
        """
        The main loop of the routing demon
        """
        
        # Add routers own entry to the table for initial send
        self.add_route_to_table((self.router_ID, 0000), 0)
        
        # Thread for periodic update
        self.start_timers()
        
        # Loop forever
        while True:
            # listen for incoming connection:
            read_sockets, _, _ = select.select(self.input_sockets, [], [], 1.0)
            
            # check that a socket has activity only if a packet has not just been sent
            if len(read_sockets) > 0 and not self.packet_just_sent:
                for socket in read_sockets: # for every socket identified to have activity
                    
                    # read the packet contents and sender address (port)
                    packet, address = socket.recvfrom(512)
                    print('packet recieved from:', address, '\n')
                    self.process_packet(packet, address)
            
            self.packet_just_sent = False


    def rip_packet_header(self, destination):
        """what every packet needs for its header"""
        
        # byte array to house the RIP header (4 bytes) and all the RIP entries (20 bytes each)
        packet_to_send = bytearray()
        
        # command field
        command = 2
        # I've put in 2 in my version, since we are only implmenting the triggered and periodic updates
        # which send the entire route table for some reason lol
        # Sounds good
        packet_to_send += command.to_bytes(1, byteorder="big")
        
        # version field
        version_num = 2
        packet_to_send += version_num.to_bytes(1, byteorder="big")
        
        # Sending router ID
        packet_to_send += self.router_ID.to_bytes(2, byteorder="big")
        
        # rip entry
        packet_to_send += self.rip_entry(destination)
        return packet_to_send
        
        
    def rip_entry(self, destination):
        """Function for generating a RIP entries (len = 20 bytes)"""
        
        # byte array to house each RIP entry (20 bytes each)
        rip_entries = bytearray()
        
        dest_router_metric = destination[1]
        
        # generate a rip entry for every link in the route table
        for key, metric in self.route_table.items():
            dest_router_id = key[0]
            metric += dest_router_metric
            
            # make sure we're not sending the destination its own link
            if dest_router_id != destination[0]:
        
                # address family
                address_family = 2
                # I've looked, it should be 2
                # Nice
                rip_entries += address_family.to_bytes(2, byteorder="big")
                
                # must be zero
                must_be_zero = 0
                rip_entries += must_be_zero.to_bytes(2, byteorder="big")
                
                # IPv4 address (we're to use the router ID for this field)
                #We've been asked to use the packet header must be zero for the 
                #router_id/sudo ip address, so this field is redudent?
                # Maybe? could we use this for the poisened reverse or something?
                #could do that
                rip_entries += dest_router_id.to_bytes(4, byteorder="big")
                
                # must be zero
                rip_entries += must_be_zero.to_bytes(4, byteorder="big")
                
                # must be zero
                rip_entries += must_be_zero.to_bytes(4, byteorder="big")
                
                # metric
                rip_entries += metric.to_bytes(4, byteorder="big")
        
        if len(rip_entries) % 20 != 0:
            # error in generating rip entries
            self.error("Problem generating RIP entries from table")
        else:
            return rip_entries


    def triggered_update(self, a):
        """for when a route becomes invalid"""
        raise NotImplementedError


    def periodic_update(self):
        """Function to handle periodic updates"""
        
        print('Sending periodic update.\n')
        self.packet_just_sent = True
        
        # generate a packet for each link:
        for destination, route_details in self.output_ports.items():
            
            output_port = route_details[0]
            output_metric = route_details[1]
            
            packet = self.rip_packet_header((destination, output_metric))
            
            self.send_packet(packet, output_port)
        
        # Timers only work once, so they need to be restarted each time
        timerVal = random.uniform((0.8 * 6), (1.2 * 6))
        self.periodic_update_timer = threading.Timer(timerVal, self.periodic_update)
        self.periodic_update_timer.start()


    def send_packet(self, packet, port):
        """Send the packet to the given port number"""
        
        sending_socket = self.input_sockets[0]
        
        address = ('127.0.0.1', port)
        
        # The socket has to be restarted after sending data
        #Why is this the case? It seems really odd..
        try:
            sending_socket.sendto(packet, address)
        finally:
            self.restart_socket(sending_socket)


    def add_route_to_table(self, route, metric):
        """adding a route to the route table. The key needs to be (router_id, portnum)"""
        try:
            self.route_table[route]
            return True
        except KeyError:
            self.route_table[route] = metric


    def convergence(self, sender_id, sender_metric):
        """
        Using the current metirc and a given new metric and sender route_ID, see which of the two
        has the better metric
        """
        current_best = None
        for key, value in self.route_table.items():
            if int(key[1]) == sender_id[1]:
                current_best = self.route_table[key]
        if current_best != None:
            best_route = min(current_best, (1 + sender_metric))
            if best_route < current_best:
                self.route_table[key] = best_route # this was editiied in at 20 past 1, don't judge


    def modify_route(self, route, n=1):
        """modifys the metric value of a route in the table"""
        self.route_table[route] += n
        if self.route_table[route] > 15:
            self.delete_route_in_table(route)
            self.triggered_update()


    def delete_route_in_table(self, route):
        """deleting a route in the table"""
        try:
            del route_table[route]
            self.triggered_update()
        except KeyError:
            return self.error("Route is not in the table")


    def print_route_table(self):
        """Prints the contents of the route table in a readable way"""
        print("Current routing table for Router {}:".format(self.router_ID))
        print('=' * 45)
        for key, metric in self.route_table.items():
            print("Destination: {} | Via Link: {} | Metric: {}".format(key[0], key[1], metric))
        print('=' * 45)
        print()


    def process_packet(self, packet, address):
        """Unpack and processes a recieved packet and its RIP entries"""
        
        # Unpack header:
        
        # Command field
        command = int.from_bytes(packet[0:1], byteorder='big')
        print('command:', command) # <---TEMPORARY LINE FOR TESTING ============
        
        # Version field
        version_num = int.from_bytes(packet[1:2], byteorder='big')
        if not self.rip_version_check(version_num): # Check if the version number is 2 (it should always be 2)
            print("Packet has invalid version number, dropping packet")
            return False
        print('version_num:', version_num) # <---TEMPORARY LINE FOR TESTING ============
        
        # Sending router's ID
        sender_id = int.from_bytes(packet[2:4], byteorder='big')
        if not self.router_id_check(sender_id): # check if the sending router's ID is valid
            print("Packet sent from router with invalid ID, dropping packet")
            return False
        print('sender_id:', sender_id) # <---TEMPORARY LINE FOR TESTING ============
        
        # Unpack RIP entries:
        
        # Calculate the number of RIP entries in the packet
        num_entries = int((len(packet[4:]) / 20))
        print('num_entries:', num_entries) # <---TEMPORARY LINE FOR TESTING ============
        
        # Retrieve data from each RIP entry
        for i in range(num_entries):
            
            # Position is the index in the RIP entry
            position = (i * 20) + 4
            
            # Bool for keeping track of RIP entry problems
            keep_rip_entry = True
            
            # Address family field
            address_family = int.from_bytes(packet[position : position + 2], byteorder='big')
            
            # IPv4 address field (destination router being advertised)
            destination = int.from_bytes(packet[position + 4 : position + 8], byteorder='big')
            if not self.router_id_check(destination):
                keep_rip_entry = False
                print("RIP entry has an invalid destination router ID ({}), omitting entry.".format(destination))
            
            # Metric field (cost to reach destination router being advertised)
            metric = int.from_bytes(packet[position + 16 : position + 20], byteorder='big')
            
            # check the metric value
            if not self.metric_check(metric) and keep_rip_entry:
                if metric == 16: # metric of infinity
                    print("RIP entry for router {} has metric 16 (infinity), removing from routing table.".format(destination))
                    # Remove the route from the table
                    keep_rip_entry = False
                    #self.delete_route_in_table()
                else:
                    print("RIP entry for router {} has an invalid metric ({}), omitting entry.".format(destination, metric))
                    keep_rip_entry = False
            # If there are no issues with the current rip entry
            if keep_rip_entry:
                port_num = address[1]
                router_key = (destination, port_num)
                self.add_route_to_table(router_key, metric)  #see if it's already in the route_table
                self.print_route_table()
                
                # Code to compare to routing table goes here.
                pass
            print('\nRip entry {}:\n\tAddress Family: {}\n\tDestination: {}\n\tCost: {}\n'.format(i+1, address_family, destination, metric)) # <---TEMPORARY LINE FOR TESTING ============


    
def main(param):
    """
    Main exicution function
    """
    
    config = param[1]

    if len(param) != 2:
        print("Usage: RIP_demon.py <conf.cfg>")
        sys.exit(1)
    
    # initialize the router class
    router(config)

if __name__ == "__main__":
    param = sys.argv
    main(param)
