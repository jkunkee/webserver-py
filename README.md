webserver-py
============

This is my simple CS360 Python HTTP server.

To run it, clone it and simply run 

    ./web.py
    
You can additionally specify a port to listen on with `-p ###`:

    ./web.py -p 3000
    
The default is `8080`.


Structure
=========

The program is very simply tiered.

* `web.py` does all of the argument and config file parsing, passes the appropriate info to the server object, and runs the server.
* `poller.py` contains both the client and server classes.
   * The `Poller` class is responsible for the server socket, creating and collecting client sockets, and epolling on them all.
      * After the poll returns, work is quickly offloaded to the `Client` class.
      * This is where mark-and-sweep socket closing is implemented.
   * The `Client` class is responsible for all I/O on an individual non-server socket. All of the `recv`/`send` and filesystem magic happens here.
      * This should eventually be broken into its own file. Oh well.
* `httpparser.py` provides string and object manipulation tools for dealing with HTTP headers of all sorts.


Known Issues
============

I ran into the same `connection reset by peer` problem that was discussed to no avail on the mailing list; however, it only shows up when I'm running on two separate machines with 100 threads or on the same machine with 1000 threads.

Only HEAD requests and varying Host headers are honored. Partial Content requests are not. :(
