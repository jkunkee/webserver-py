import select
import socket
import sys
import httpparser

class Poller:
    """ Polling server """
    def __init__(self, port):
        self.host = ""
        self.port = port
        self.open_socket()
        self.clients = {}
        self.size = 1024

    def open_socket(self):
        """ Setup the socket for incoming clients """
        try:
            # create the socket
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # do some additional socket configuration
            self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # tell the socket where to listen
            self.server.bind((self.host, self.port))
            # back log size is ignored in Linux anyhow, but Python defaults to 5
            self.server.listen(5)
        except socket.error, (value, message):
            if self.server:
                self.server.close()
            print "Could not open socket: " + message
            sys.exit(1)

    def run(self):
        """ Use poll() to handle each incoming client."""
        self.poller = select.epoll()
        self.pollmask = select.EPOLLIN | select.EPOLLHUP | select.EPOLLERR
        self.poller.register(self.server, self.pollmask)
        while True:
            # poll sockets
            try:
                fds = self.poller.poll(timeout=1)
            except:
                return
            for (fd, event) in fds:
                # handle errors
                if event & (select.POLLHUP | select.POLLERR):
                    self.handleError(fd)
                    continue
                # handle the server socket
                if fd == self.server.fileno():
                    self.handleServer()
                    continue
                # handle client socket
                self.handleClient(fd)

    def handleError(self, fd):
        self.poller.unregister(fd)
        if fd == self.server.fileno():
            # recreate server socket
            self.server.close()
            self.open_socket()
            self.poller.register(self.server, self.pollmask)
        else:
            # close the socket
            self.clients[fd].close()
            del self.clients[fd]

    def handleServer(self):
        # accept the connection, producing a valid socket
        (client, address) = self.server.accept()
        # put it in the map of clients
        self.clients[client.fileno()] = client
        # start epoll listening for events on this socket :)
        self.poller.register(client.fileno(), self.pollmask)
        client.recvBuf = ""

    def handleClient(self, fd):
        # select the client
        client = self.clients[fd]
        # read in a chunk
        data = client.recv(self.size)
        # python allows truthy/falsey values?!
        if data:
            client.recvBuf += data
            pieces = client.recvBuf.split(http)
        else:
            self.poller.unregister(fd)
            self.clients[fd].close()
            del self.clients[fd]
