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
import time

class router():
    """
    Rip routing demon class
    """
    
    # Router variables
    # This router's ID
    router_ID = 0
    
    # This router's input ports
    input_ports = []
    
    # This router's output ports {router_ID: (port, metric)}
    output_ports = {}
    
    # This router's input sockets (generated from the input ports)
    input_sockets = []
    
    # This router's routing table {router_ID: (port, metric, timeout, garbage_collection)}
    route_table = {}
    
    
    # Timer Variables
    # Division factor of the standard RIP timer values
    division_factor = 5
    
    # Interval the periodic updates will occur at
    update_interval = 30 / division_factor
    
    # Length of the timeout counter
    timeout_interval = 180 / division_factor
    
    # Length of the garbage collection counter
    garbage_collection_interval = 120 / division_factor
    
    
    # Variable to store the timer for periodic updates in so it can be cancelled later
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
        
        # Add routers own entry to the table for initial send
        self.route_table[self.router_ID] = (0, 0)
        
        # Thread for periodic update
        self.start_periodic_timer()
        
        # Start the infinite loop
        self.loop()

    def router_id_check(self, ID):
        """
        Returns an error if the router id is out of the allowed range
        """
        return True if ID >= 1 and ID <= 64000 else False


    def port_check(self, port):
        """
        Returns an error if the port is out of the allowed range
        """
        return True if port >= 1024 and port <= 64000 else False


    def metric_check(self, metric):
        """
        returns false if the metric is not within the bounds, will also trigger a dead-timer.
        """
        return True if metric >= 0 and metric <= 16 else False


    def rip_version_check(self, value):
        """
        Returns false if the rip version != 2, could indicate transmission error
        """
        return True if value == 2 else False


    def error(self, message, exit_code = 1):
        """
        Print an error message in the console and close the demon
        """
        
        # Cancel threading timers
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
                #temp_socket.settimeout(1.0)
                temp_socket.setblocking(0)
                temp_socket.bind(('127.0.0.1', port))
                
                self.input_sockets.append(temp_socket)
        
        except socket.error:
            self.error("Error creating socket connection")


    def start_periodic_timer(self):
        """
        Starts the periodic timer for threading
        """
        
        # Create a thread timer for a periodic update
        # timerVal is the recommended range given on pg 7 of assignment handout
        timerVal = random.uniform((0.8 * self.update_interval), (1.2 * self.update_interval))
        self.periodic_update_timer = threading.Timer(timerVal, self.periodic_update)
        self.periodic_update_timer.start()


    def start_route_timeout_timer(self, route):
        """
        Starts a timeout timer for a given route in the table.
        """
        
        route_timeout_timer = threading.Timer(self.timeout_interval, self.route_timed_out, (route, ))
        route_timeout_timer.start()
        
        return route_timeout_timer


    def start_garbage_collection_timer(self, route):
        """
        Starts the garbage collection timer when a route timer expires
        """
        
        garbage_collection_timer = threading.Timer(self.garbage_collection_interval, self.delete_route_in_table, (route, ))
        garbage_collection_timer.start()
        
        return garbage_collection_timer


    def loop(self):
        """
        The main loop of the routing demon
        """
        
        # Loop forever
        while True:
            # listen for incoming connection:
            read_sockets, _, _ = select.select(self.input_sockets, [], [], 1.0)
            
            # check that a socket has activity only if a packet has not just been sent
            if len(read_sockets) > 0:
                for socket in read_sockets: # for every socket identified to have activity
                    
                    # This try statement prevents port errors
                    try:
                        # read the packet contents and sender address (port)
                        packet, address = socket.recvfrom(512)
                        
                        # Make sure we're not reading from our own port
                        if address[1] not in self.input_ports:
                            print('Packet recieved from router:', address, '\n')
                            
                            self.process_packet(packet, address)
                            
                            self.print_route_table()
                        
                    except:
                        pass


    def rip_packet_header(self, destination, dest_details):
        """
        Generate a RIP packet header (len = 4 bytes)
        """
        
        # byte array to house the RIP header (4 bytes) and all the RIP entries (20 bytes each)
        packet_to_send = bytearray()
        
        # command field
        command = 2
        packet_to_send += command.to_bytes(1, byteorder="big")
        
        # version field
        version_num = 2
        packet_to_send += version_num.to_bytes(1, byteorder="big")
        
        # Sending router ID
        packet_to_send += self.router_ID.to_bytes(2, byteorder="big")
        
        # rip entry
        packet_to_send += self.rip_entry(destination, dest_details)
        return packet_to_send


    def rip_entry(self, destination, dest_details):
        """
        Function for generating a RIP entries (len = 20 bytes)
        """
        
        # byte array to house each RIP entry (20 bytes each)
        rip_entries = bytearray()
        
        # generate a rip entry for every link in the route table
        for dest_router_id, route_details in self.route_table.items():
            metric = route_details[1]
            
            # split horizon with poisoned reverse:
            if route_details[0] == dest_details[0]:
                
                metric = 16
                
            # address family
            address_family = 2
            rip_entries += address_family.to_bytes(2, byteorder="big")
            
            # must be zero
            must_be_zero = 0
            rip_entries += must_be_zero.to_bytes(2, byteorder="big")
            
            # IPv4 address (we're to use the router ID for this field)
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


    def triggered_update(self):
        """
        For when a route becomes invalid or a better route is found
        """
        
        self.periodic_update(True)


    def periodic_update(self, triggered=False):
        """
        Function to handle periodic updates
        """
        
        if not triggered:
            print('Sending periodic update.\n')
        else:
            print('Sending triggered update.\n')
        
        # generate a packet for each link:
        for destination, route_details in self.output_ports.items():
            
            packet = self.rip_packet_header(destination, route_details)
            
            self.send_packet(packet, route_details[0])
        
        if not triggered:
            # Timers only work once, so they need to be restarted each time
            self.start_periodic_timer()


    def send_packet(self, packet, port):
        """
        Send the packet to the given port number
        """
        
        # Pick this input socket to send from
        sending_socket = self.input_sockets[0]
        
        # Address to send packet to
        address = ('127.0.0.1', port)
        
        # Send data
        sending_socket.sendto(packet, address)


    def add_route_to_table(self, route, details):
        """
        Adding a route to the route table.
        """
        
        if route in self.route_table:
            return True
        else:
            
            if details[1] < 16:
                timer = (self.start_route_timeout_timer(route), time.time() + self.timeout_interval)
                self.route_table[route] = (details[0], details[1], timer, None)
            return False


    def convergence(self, destination, new_route_details):
        """
        Using the current route details from the route table and the given new route details of a given destination,
        see which of the two has the better metric.
        """
        
        # Get current route details from the route table
        route_details = self.route_table[destination]
        
        # If this datagram is from the same router as the existing route, reinitialize the timeout.
        if route_details[0] == new_route_details[0]:
            
            # Cancel route timeout
            route_details[2][0].cancel()
            
            # Cancel route garbage collection
            if route_details[1] != 16 and route_details[3] != None:
                route_details[3][0].cancel()
            
            # Create new route timeout 
            timer = (self.start_route_timeout_timer(destination), time.time() + self.timeout_interval)
            self.route_table[destination] = (route_details[0], route_details[1], timer, None)
        
        
        # If the datagram is from the same router as the existing route, and the new metric is different
        # than the old one; or, if the new metric is lower than the old one; do the following actions:
        if (route_details[0] == new_route_details[0] and route_details[1] != new_route_details[1]) or route_details[1] > new_route_details[1]:
            
            # Addopt the new route details
            self.route_table[destination] = (new_route_details[0], new_route_details[1], self.route_table[destination][2], None)
            
            if new_route_details[1] == 16 and route_details[3] == None:
                # Start deletion process:
                self.drop_route(destination)
            
            
            return True # Trigger an update
        return False # Don't Trigger an update


    def drop_route(self, route):
        """
        Starts the deletion process of the given route
        """
        
        # Retrieve the current routes details form the route table
        route_details = self.route_table[route]
        
        # Start a new garbage collection time for the given route
        timer = (self.start_garbage_collection_timer(route), time.time() + self.garbage_collection_interval)
        
        self.route_table[route] = (route_details[0], 16, route_details[2], timer)


    def delete_route_in_table(self, route):
        """
        Deletes a route from the table
        """
        try:
            if route in self.route_table:
                del self.route_table[route]
        except KeyError:
            return self.error("Route is not in the table")


    def route_timed_out(self, route):
        """
        Function that is called when a function times out
        """
        
        print('Route to router {} timed out.\n'.format(route))
        
        self.drop_route(route)


    def print_route_table(self):
        """
        Prints the contents of the route table in a readable way
        """
        
        timeout = 0 # variable for holding the timout counter
        garbage = 0 # variable for holding the garbage collection counter
        
        print("Current routing table for Router {}:".format(self.router_ID))
        print('=' * 78)
        for route, details in sorted(self.route_table.items()):
            if route != self.router_ID: # don't print the router's own RIP entry
                
                # Get timeout value
                if details[2][1] - time.time() > 0:
                    timeout = details[2][1] - time.time()
                else:
                    timeout = 0
                
                # Get garbage collection value
                if details[3] != None and details[3][1] - time.time() > 0:
                    garbage = details[3][1] - time.time()
                else:
                    garbage = 0
                    
                print("Destination: {} | Via Link: {} | Metric: {} | TimeOut: {:.2f} | Garbage: {:.2f}".format(route, details[0], details[1], timeout, garbage))
        print('=' * 78, '\n')


    def process_packet(self, packet, address):
        """
        Unpack and processes a recieved packet and its RIP entries
        """
        
        trigger_update = False
        
        # Unpack header:
        
        # Command field
        command = int.from_bytes(packet[0:1], byteorder='big')
        #print('command:', command) # <---TEMPORARY LINE FOR TESTING ============
        
        # Version field
        version_num = int.from_bytes(packet[1:2], byteorder='big')
        if not self.rip_version_check(version_num): # Check if the version number is 2 (it should always be 2)
            print("Packet has invalid version number, dropping packet")
            return 
        #print('version_num:', version_num) # <---TEMPORARY LINE FOR TESTING ============
        
        # Sending router's ID
        sender_id = int.from_bytes(packet[2:4], byteorder='big')
        if not self.router_id_check(sender_id): # check if the sending router's ID is valid
            print("Packet sent from router with invalid ID, dropping packet")
            return 
        #print('sender_id:', sender_id) # <---TEMPORARY LINE FOR TESTING ============
        
        # Unpack RIP entries:
        
        # Calculate the number of RIP entries in the packet
        num_entries = int((len(packet[4:]) / 20))
        #print('num_entries:', num_entries) # <---TEMPORARY LINE FOR TESTING ============
        
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
            if not self.router_id_check(destination) or destination == self.router_ID:
                keep_rip_entry = False
                #print("RIP entry has an invalid destination router ID ({}), omitting entry.".format(destination))
            
            # Metric field (cost to reach destination router being advertised)
            metric = int.from_bytes(packet[position + 16 : position + 20], byteorder='big')
            if not self.metric_check(metric):
                keep_rip_entry = False
                print("RIP entry has an invalid metric ({}), omitting entry.".format(metric))
                
            # If there are no issues with the current rip entry
            if keep_rip_entry:
                
                cost = self.output_ports[sender_id][1]
                
                metric = min(metric + cost, 16)
                
                #print('\nRip entry {}:\n\tAddress Family: {}\n\tDestination: {}\n\tCost: {}\n'.format(i+1, address_family, destination, metric)) # <---TEMPORARY LINE FOR TESTING ============
                
                route_details = (self.output_ports[sender_id][0], metric)
                
                if self.add_route_to_table(destination, route_details):
                    if self.convergence(destination, route_details):
                        trigger_update = True
        
        if trigger_update:
            self.triggered_update()




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
