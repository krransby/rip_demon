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
        self.router_ID = int(file.readline().split(' ')[1])
        if self.router_ID < 1 or self.router_ID > 64000:
            self.error("Router ID not within range 1 < x x 64000")
        
        # Set input ports:
        for port in file.readline().split()[1:]:
            tmp = int(port.rstrip(','))
            a = self.port_check(tmp)
            if a == True:
                self.input_ports.append(tmp)
            else:
                self.error("Input port needs to be in the range 1024 <= x <= 65535")

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
        
        self.create_route_table(self.router_ID, self.input_ports,self.output_ports)
        # Start the infinite loop
        self.loop()

        return
    

    def port_check(self, port):
        "Returns an error if the port is out of the allowed range"
        return True if port >= 1024 or port <= 64000 else False


    def metric_check(self, metric):
        "returns false if the metric is not within the bounds, will also trigger a dead-timer."
        return True if metric > 0 and metric < 16 else False
    
    
    def rip_version_check(self, value):
        "Returns false if the rip version != 2, could indicate transmission error"
        return True if value == 2 else False


    def error(self, message, exit_code = 1):
        """
        Print an error message in the console and close the demon
        """
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
                if type(port) != type(1): #Checking to see if 'port' is an integer
                    break

                temp_socket = socket.socket()
                temp_socket.settimeout(5)
                temp_socket.bind(('127.0.0.1', port))
                temp_socket.listen()

                self.input_sockets.append(temp_socket)

        except socket.error:
            self.error("Error creating socket connection")


    def loop(self):
        """
        """
        self.print_route_table()
       # self.error("", 0)
       
        
    
    def rip_packet_header(self, destination):
        "what every packet needs for its header"
        packet_to_send = bytearray()
        command = int(bin(0)[2:].zfill(8))
        packet_to_send += command.to_bytes(1, byteorder="big")
        
        version_num = int(bin(2)[2:].zfill(8))
        packet_to_send += (version_num).to_bytes(1, byteorder="big")
        
        rip_des = int(destination[0]).to_bytes(2, byteorder="big")
        packet_to_send += rip_des
        
        packet_to_send += self.rip_entry(destination)
        return packet_to_send
        
                
    def rip_entry(self, destination):
        new_pkt = bytearray()
        address_family = int(bin(2)[2:].zfill(8))
        new_pkt += address_family.to_bytes(1, byteorder="big")
        must_be_zero = int(bin(0)[2:].zfill(16))
        new_pkt += must_be_zero.to_bytes(2, byteorder="big")
        return new_pkt
    
    
    def triggered_update(self, a):
        """for when a route becomes invalid"""
        result = None
        result = self.rip_packet_header(a)
    
    
    def send_packet(self):
        "sending the packet to the other 'routers'"
        raise NotImplementedError
        
        
    def create_route_table(self, router_ids, input_ports, output_ports):
        "creating the route table"
        route_table = {}
        for port in output_ports:
            value = (port[2], port[0])
            route_table[value] = port[1]
        self.route_table = route_table
    
    
    def add_route_to_table(self, route, metric):
        "adding a route to the route table. The key needs to be (router_id, portnum)"
        self.route_table[route] = metric
        self.triggered_update(route)
    
    
    def modify_route(self, route, n=1):
        "modifys the metric value of a route in the table"
        self.route_table[route] += n
        if self.route_table[route] > 15:
            self.route_table[route] = 'INF'
        #self.triggered_update()
    
    
    def delete_route_in_table(self, route):
        "deleting a route in the table"
        try:
            del route_table[route]
            self.triggered_update()
        except KeyError:
            return self.error("Route is not in the table")
    
    
    def print_route_table(self):
        print("Current routing table for Router {}:".format(self.router_ID))
        for key, metric in self.route_table.items():
            print("Destination: {} | Via Link: {} | Metric: {}".format(key[0], key[1], metric))
    
    
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
    param = ['0', 'conf4.cfg']
    main(param)