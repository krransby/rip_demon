"""
    COSC364: Assignment 1
    RIP routing demon

    Kayle Ransby (34043590)
    Sjaak Flick (36406121)

"""

import os
import sys
import socket
import datetime

class router():
    """
    
    """

    router_ID = 0
    input_ports = []
    output_ports = []

    input_sockets = []
    route_table = None
    trash_panda_collector = 0

    def __init__(self, config):
        """
        Function to read the config file
        """
            
        file = open(config)

        # Set router ID:
        self.router_ID = int(file.readline().split()[1])
        if self.router_ID < 1 or self.router_ID > 64000:
            self.error("Router ID not within range 1 < x x 64000")
        
        # Set input ports:
        for port in file.readline().split()[1:]:
            tmp = int(port.rstrip(','))
            self.input_ports.append(tmp)
            self.port_check(tmp)

        # Set output ports:
        for port in file.readline().split()[1:]:
            tmp = port.rstrip(',').split('-')
            for i in range(3):
                tmp[i] = int(tmp[i])
            self.output_ports.append(tmp)
            self.port_check(tmp[0])


        # Close configuration file:
        file.close()

        # Bind input ports to a socket
        self.start_sockets()

        # Start the infinite loop
        self.loop()

        return
    

    def port_check(self, port):
        "Returns an error if the port is out of the allowed range"
        return 0 if port >= 1024 or port <= 64000 else self.error("Port outside range 1024 <= x <= 64000")


    def metric_check(self, metric):
        "returns false if the metric is not within the bounds, will also trigger a dead-timer."
        return True if metric > 0 and metric < 16 else False
    
    
    def rip_version_check(self, value):
        "Returns false if the rip version != 2, might indicate transmission error"
        return True if value == 2 else False


    def error(self, message, exit_code = 1):
        """
        Print an error message in the console and close the demon
        """
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
                if type(port) != type(1):
                    break

                temp_socket = socket.socket()
                temp_socket.settimeout(1.0)
                temp_socket.bind(('127.0.0.1', port))

                self.input_sockets.append(temp_socket)

        except socket.error:
            self.error("Error creating socket connection")


    def loop(self):
        """
        """
        raise NotImplementedError("This isn't working yet, pls come back later")
    
    
    
    def rip_packet_header(self):
        "what every packet needs for its header"
        packet_to_send = bytearray()
        command = int(bin(0).zfill(8),1) 
        packet_to_send += (command).to_bytes(1, byteorder="big")
        version_num = int(bin(2).zfill(8),1)
        packet_to_send += (version_num).to_bytes(1, byteorder="big")
        THIS_HAS_TO_BE_ZERO = int(bin(0).zfill(16),2)
        packet_to_send += (THIS_HAS_TO_BE_ZERO).to_bytes(2, byteorder="big")
        
        
    def send_packet(self):
        "sending the packet to the other 'routers'"
        raise NotImplementedError
        
        
    def create_route_table(self, router_ids, input_ports, output_ports):
        "creating the route table"
        route_table = {}
        for port in output_ports:
            port = port.split('-')
            value = (port[2], port[0])
            route_table[value] = port[1]
        self.route_table = route_table
    
    
    def add_route_to_table(self, route, metric):
        "adding a route to the route table. The key needs to be (router_id, portnum)"
        route_table[route] += metric
    
    
    def modify_route_in_table(self, route, n=1):
        "modifying a route in the table"
        route_table[route] += n
    
    
    def delete_route_in_table(self, route):
        "deleting a route in the table"
        try:
            route_table.delete(route)
        except:
            return self.error("Route is not in the table")
    
    def print_route_table(self):
        for key, metric in route_table.items():
            print("Router ID: {} | Port Number: {} | Metric: {}".format(key[0], key[1], metric))
    
    
    def process_packet(self, packet):
        #prehaps "decode" the packet
        #then do error checking on each of the fixed fields, 
        #
        good_value = metric_check(value)
        if good_value is False:
            self.error("Route is gone")
        
    
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
