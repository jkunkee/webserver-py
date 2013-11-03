# enable using print() as a function
from __future__ import print_function

import select
import socket
import sys
import time
import errno
import os

import httpparser


def Print(*args):
    debug = False
    if debug:
        print(*args)


class Poller:

    """ Polling server """

    def __init__(self, port, types, hosts, parms):
        self.host = ""
        self.port = port
        self.open_socket()
        self.clients = {}
        try:
            self.socketTimeout = float(parms["timeout"])
        except:
            self.socketTimeout = 5.0

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
            # back log size is ignored in Linux anyhow,
            # but Python defaults to 5
            self.server.listen(5)
        except socket.error as err:
            if self.server:
                self.server.close()
            Print("Could not open socket: %s" % (err))
            sys.exit(1)

    def run(self):
        """ Use poll() to handle each incoming client."""
        self.poller = select.epoll()
        self.pollmask = select.EPOLLIN | select.EPOLLHUP | select.EPOLLERR
        self.poller.register(self.server, self.pollmask)

        lastSweep = time.time()
        while True:
            # poll sockets
            try:
                fds = self.poller.poll(timeout=self.socketTimeout / 4)
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
                Print("Got client socket event for", fd)
                self.handleClient(fd)
            now = time.time()
            if now - lastSweep > self.socketTimeout:
                Print("Conducting mark-and-sweep...")
                expired_fds = []
                # find all of the expired file descriptors
                for fd in self.clients.keys():
                    client = self.clients[fd]
                    if now - client.lastActivityTime > self.socketTimeout:
                        expired_fds.append(fd)
                # ...handle them, Jeeves
                for fd in expired_fds:
                    self.handleError(fd)
                # set up to wait until next time.
                lastSweep = time.time()

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
            Print("Got an error, hanging up on", fd, err, self.clients[fd].remoteThreadID)
            self.handleError(fd)


class Client:

    def __init__(self, socket, types, hosts):
        self.socket = socket
        self.recvBuf = b""
        self.header = None
        self.inputChunkSize = 4096
        self.fileChunkSize = 8192
        self.lastActivityTime = time.time()
        self.remoteThreadID = ""

        self.types = types
        self.hosts = hosts

    def handleEvent(self):
        """ Handles any event that might have fired on this Client's socket """

        # keep track of how recently this socket saw traffic
        self.lastActivityTime = time.time()

        # read in all available chunks
        while True:
            try:
                data = self.socket.recv(self.inputChunkSize, socket.MSG_DONTWAIT)
                if not data:
                    # cause socket to be closed
                    return "event fired for fd %d, but no data received. closing socket. %s" % (self.socket.fileno(), data)
                # yay! we got data! put it in the buffer :)
                self.recvBuf += data
            except socket.error as err:
                if err.errno == errno.EAGAIN or err.errno == errno.EWOULDBLOCK:
                    Print("done listening for new data trigger:", err)
                    break
                else:
                    Print("")
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
            if request and not errors:
                Print("successfully parsed header:", request)
                return self.handleRequest(request)
            else:
                Print("error parsing header:", errors)
                return self.handleError(400)

        # don't close the socket
        return None

    def handleRequest(self, request):
        response = httpparser.makeResHeader()

        if "X-Stress" in request.headers:
            self.remoteThreadID = request.headers["X-Stress"]
        # first, figure out what file they actually want
        if "Host" not in request.headers:
            self.handleError(400)
            return None
        host_pcs = request.headers["Host"].split(":")
        hostname = host_pcs[0]
        hostRoot = None

        if not hostname or not (hostname in self.hosts):
            hostRoot = self.hosts["default"]
        else:
            hostRoot = self.hosts[hostname]
        #absHostRoot = os.path.abspath(hostRoot)

        urlpath = request.path
        if urlpath[-1] == "/":
            urlpath = "index.html"
        #joinedpath = os.path.join(urlpath, hostRoot)
        joinedpath = hostRoot + "/" + urlpath
        filepath = os.path.abspath(joinedpath)
        #Print("combined", hostRoot, "with", urlpath, "to get", joinedpath, "which resolves to", filepath)

        # now open the file
        fd = None
        fileStats = None

        try:
            fd = os.open(filepath, os.O_RDONLY)
            fileStats = os.fstat(fd)
        except (OSError, IOError) as e:
            if fd is not None:
                os.close(fd)
                fd = None

            Print ("error accessing file:", filepath, e)

            if e.errno == errno.EACCES:
                self.handleError(403)
                return None
            elif e.errno == errno.ENOENT:
                self.handleError(404)
                return None
            else:
                self.handleError(500)
                return None

        # due to the exhaustive nature of the except: statement, we assume
        # the file exists.
        Print("file exists, fd: %s, stats: %s\n" % (
            fd, fileStats,
        ))
        # test file access
        #if fileExists:
            #Print("line", os.read(fd, 16))

        # inform the user about the size
        response.headers["Content-Length"] = fileStats.st_size
        # TODO make Last-Modified draw from fileStats
        response.headers["Last-Modified"] = httpparser.mkHttpTimestamp()
        # decide on a content type
        ext = filepath.split(".")[-1]
        if ext in self.types:
            contentType = self.types[ext]
        else:
            contentType = self.types["default"]
        response.headers["Content-Type"] = contentType

        # now handle the request per method
        if request.method == "GET" or request.method == "HEAD":
            Print("got", request.method)
            resStr = response.toHttp()
            Print("sending headers", resStr)
            self.send(resStr)
            if request.method == "GET":
                Print("sending file too")
                self.sendfile(fd)
        else:
            Print("got UNSUPPORTED method:", request.method)
            self.handleError(501)

        if fd is not None:
            os.close(fd)
        return None

    def handleError(self, errno=400):
        response = httpparser.makeResHeader(errno)
        body = "<html><head><title>%s</title></head><body>%s</body></html>\n" % (
            "Error",
            "You have encountered error %d (%s) while accessing this resource." % (
                errno,
                response.errCodeDescription(),
            )
        )
        response.headers["Content-Length"] = len(body)
        response.headers["Content-Type"] = self.types["html"]
        self.send(response.toHttp())
        self.send(body)
        return None

    def send(self, string):
        string = bytearray(string, "utf-8")
        while len(string) > 0:
            bytesSent = self.socket.send(string)
            string = string[bytesSent:]

    def sendfile(self, fd):
        while os.sendfile(self.socket.fileno(), fd, None, self.fileChunkSize) > 0:
            True
