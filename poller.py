import select
import socket
import sys
import time
import errno

import httpparser


class Poller:

    """ Polling server """

    def __init__(self, port, types, hosts, parms):
        self.host = ""
        self.port = port
        self.open_socket()
        self.clients = {}
        try:
            self.timeout = float(parms["timeout"])
        except:
            self.timeout = 5.0

        self.types = types
        self.hosts = hosts

    def open_socket(self):
        """ Setup the socket for incoming clients """
        try:
            # create the socket
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # do some additional socket configuration
            self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # tell the socket where to listen
            self.server.bind((self.host, self.port))
            # back log size is ignored in Linux anyhow, but Python defaults to
            # 5
            self.server.listen(5)
        except socket.error as err:
            if self.server:
                self.server.close()
            print("Could not open socket: %s" % (err))
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
                print("Got client socket event for", fd)
                self.handleClient(fd)

    def handleError(self, fd):
        # stop listening for I/O
        self.poller.unregister(fd)
        if fd == self.server.fileno():
            # recreate server socket
            self.server.close()
            self.open_socket()
            self.poller.register(self.server, self.pollmask)
        else:
            # close the socket
            # tell the other end and the OS that we're done
            # TODO: move this into __del__
            self.clients[fd].socket.close()
            # let garbage collector Do Its Thang
            del self.clients[fd]

    def handleServer(self):
        # accept the connection, producing a valid socket
        (socket, address) = self.server.accept()
        # make a handy wrapper object
        client = Client(socket, self.types, self.hosts)
        # put it in the map of clients
        self.clients[client.socket.fileno()] = client
        # start epoll listening for events on this socket :)
        self.poller.register(client.socket.fileno(), self.pollmask)

    def handleClient(self, fd):
        err = self.clients[fd].handleEvent()
        if err:
            # Oh Clap, it sleems we have to die!
            print("Got an error, hanging up on", fd)
            self.handleError(fd)


class Client:

    def __init__(self, socket, types, hosts):
        self.socket = socket
        self.recvBuf = b""
        self.header = None
        self.size = 4096
        self.lastActivityTime = time.time()

        self.types = types
        self.hosts = hosts

    def handleEvent(self):
        """ Handles any event that might have fired on this Client's socket """
        # read in all available chunks
        while True:
            try:
                data = self.socket.recv(self.size, socket.MSG_DONTWAIT)
                if not data:
                    # cause socket to be closed
                    return "event fired for fd %d, but no data received. closing socket" % (self.socket.fileno())
                # yay! we got data! put it in the buffer :)
                self.recvBuf += data
            except socket.error as err:
                if err.errno == errno.EAGAIN or err.errno == errno.EWOULDBLOCK:
                    break
                else:
                    return err

        # if we don't have a header, try to find one
        messages = self.recvBuf.split(
            httpparser.HTTP_MSG_END,
        )
        # save the last entry as the remainder
        self.recvBuf = messages[-1]
        # everything else are messages
        messages = messages[:-1]
        # handle each message in sequence
        for msg in messages:
            # try to parse it
            (request, errors) = httpparser.parseReqHeader(
                msg + httpparser.HTTP_MSG_END,
            )
            # get mad if we failed, work if we succeeded
            if request:
                print("successfully parsed header:", request)
                return self.handleRequest(request)
            else:
                print("error parsing header:", errors)
                return self.handleError(400)

        # don't close the socket
        return None

    def handleRequest(self, request):
        response = httpparser.makeResHeader()
        if request.method == "GET":
            print("got GET")
        elif request.method == "HEAD":
            print("got HEAD")
        else:
            print("got UNSUPPORTED")
        print(response)
        return None

    def handleError(self, errno=400):
        response = httpparser.makeResHeader(errno)
        self.socket.write(response)
        return None

    def send(string):
        print("TODO: send", string)

    def sendfile(filename):
        print("TODO: send file", filename)
        #with os.open(filename) as f:
            #os.sendfile(self.socket.fd, )
