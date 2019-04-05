# -*- coding: utf-8 -*-


# ICT1010 Assignment 2

# Lab Group: P4
# Rack Number: 14

# Team Members:
# Tan Jia Le 1802988
# Lee Xian Da 1802972
# Tan Rong Hao 1802990
# Sim Yi Jian 1802984


import socket
from thread import start_new_thread
import select

CRLF = b"\r\n"

class HTTPProxy:
    def __init__(self, addr = "", port = 8888, max_conn = 50, max_buffer = 8192):
        # IP address to point the browser to
        self.addr = addr
        self.port = port
        # Maximum number of concurrent clients
        self.max_conn = max_conn
        # Maximum request length
        self.max_buffer = max_buffer
        # Socket that accepts connections
        self.serversocket = None
    
    def start(self):
        # Create socket
        self.serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Bind to interface
        self.serversocket.bind((self.addr, self.port))
        # Set max number of connections
        self.serversocket.listen(self.max_conn)
        try:
            # Keep accepting connections
            while True:
                # Accept client connection
                client, _ = self.serversocket.accept()
                # Start a thread for that client
                start_new_thread(self.proxy, (client,))
        except KeyboardInterrupt:
            # Ctrl-C and terminate proxy
            self.serversocket.close()

    # Used to bind a buffer to a connection
    class Client:
        def __init__(self, connection, max_buffer):

            self.connection = connection
            self.buffer = b''
            self.max_buffer = max_buffer
        
        # Send contents of buffer and empty it
        def send(self):
            self.connection.send(self.buffer)
            self.buffer = b''
        
        # Receive contents from connection
        def recv(self):
            return self.connection.recv(self.max_buffer)

        # Terminate connection
        def close(self):
            self.connection.close()    

    def proxy(self, client):
        # Create a Client from the client's connection
        proxyclient = self.Client(client, self.max_buffer)
        # a Client to hold the proxy's connection to the website
        proxyserver = None
        # Used to check whether connection to website has ended
        terminated = False
        # Method field of client's web request
        method = b''

        while True:
            rlist, wlist, _ = [proxyclient.connection], [], []
            # If buffer contains something, means its ready for sending to client
            if proxyclient.buffer != b'':
                wlist.append(proxyclient.connection)
            # Only if a connection to website has already been started
            if proxyserver and not terminated:
                # If buffer contains something, means its ready for sending to website
                if proxyserver.buffer != b'':
                    wlist.append(proxyserver.connection)

                rlist.append(proxyserver.connection)
            
            r, w, _ = select.select(rlist, wlist, _, 1)

            # Process w
            # If client connection ready for writing
            if proxyclient.connection in w:
                # Send buffer contents to client browser
                proxyclient.send()
            # If connection to website ready for writing
            if proxyserver and not terminated and proxyserver.connection in w:
                # Send buffer contents to website
                proxyserver.send()
            
            # Process r
            # If client connection ready for reading
            if proxyclient.connection in r:
                # Read from connection
                data = proxyclient.recv()
                # If received nothing, terminate
                if data == b'':
                    break
                # If connection to website already started
                if proxyserver and not terminated:
                    # Just append to buffer
                    proxyserver.buffer += data
                else:
                    # If connection not yet already started
                    if proxyserver == None:
                        # Extract hostname , port , method
                        host, port, method = self.parse(data)
                        # Start connection to website
                        proxyconnection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        proxyconnection.connect((host, port))    
                        proxyserver = self.Client(proxyconnection, self.max_buffer)

                    # If method is CONNECT, handle it
                    if method == b'CONNECT':
                        proxyclient.buffer += b'HTTP/1.1 200 Connection established' + CRLF + CRLF

                    # If method is GET/POST etc, just append buffer
                    else:
                        proxyserver.buffer += data

            # If connection to website is ready for reading
            if proxyserver and not terminated and proxyserver.connection in r:
                # Read from connection
                data = proxyserver.recv()
                # Append to buffer
                proxyclient.buffer += data
    
    # Parse HTTP request and return host,port,method
    def parse(self, data):
        # Split into lines
        content = data.split(CRLF)

        host, port = b'',b''
        method, uri = b'', b''

        # Split into method, uri, version
        
        request_line = content[0].split(b' ')
        method += request_line[0] 
        uri += request_line[1]
        
        # If method is CONNECT, extract host and port from URI
        if method == b'CONNECT':
            host, port = uri.split(b':')
        else:
            # Check if URI contains the protocol
            if uri.find(b"://") != -1:
                # If URI contains http, means port 80
                if uri.find(b"http://") != -1:
                    protocol_pos = uri.find(b"http://")
                    port = b"80"
                    host_pos = protocol_pos+len(b"http://")
                # If URI contains https, means port 443
                if uri.find(b"https://") != -1:
                    protocol_pos = uri.find(b"https://")
                    port = b"443"
                    host_pos = protocol_pos+len(b"https://")
                # If port is specified in URI, use that port instead
                if uri[host_pos:].find(b':') != -1:
                    port_pos = host_pos + uri[host_pos:].find(b':') +1
                    end_pos = port_pos + uri[port_pos:].find(b"/")
                    host = uri[host_pos: port_pos-1]
                    port = uri[port_pos:end_pos]
                # Else, extract host normally
                else:
                    end_pos = host_pos + uri[host_pos:].find(b"/")
                    host = uri[host_pos:end_pos]
            # Host and Port in Host header
            else:
                hostheader_pos = content[1].find(b"Host: ") + len(b"Host: ")
                host, port = content[1][hostheader_pos:].split(b':')
        

        # Type cast port to integer
        port = int(port)
        return host, port, method


def main():
    # Instantiate a HTTP Proxy (Default on all interfaces and port 8899. Refer to HTTPProxy
    # class constructor for more information )
    newProxy = HTTPProxy()
    # Start proxy server
    newProxy.start()


if __name__ == "__main__":
    main()