"""
    COSC364: Assignment 1
    RIP routing demon

    Kayle Ransby (34043590)

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

    def __init__(self, config):
        """
        Function to read the config file
        """

        # Open configuration file:
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
        """
        """
        return 0 if port >= 1024 or port <= 64000 else self.error("Port outside range 1024 <= x <= 64000")


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