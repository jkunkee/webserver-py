
import argparse
import poller
import os
import sys


def parse_arguments():
    ''' parse arguments, which include '-p' for port '''
    parser = argparse.ArgumentParser(
        prog='Jon`s HTTP Server',
        description='A simple HTTP server that uses asynchronous I/O',
        add_help=True
    )
    parser.add_argument(
        '-p', '--port',
        type=int,
#        required=False,
        action='store',
        help='port the server will bind to',
        default=8080
    )
    return parser.parse_args()


def load_conf_file():
    typeMap = {}
    hostMap = {}
    parmMap = {}
    confFile = None

    confFileName = os.path.abspath("web.conf")

    try:
        confFile = open(confFileName, 'r')
    except BaseException as openErr:
        print("couldn't find config file:", openErr)
        sys.exit(1)

    for line in confFile.readlines():
        fields = line.split(" ")
        if len(fields) != 3:
            if line != "\n":
                print("skipping incomplete line:", line)
            continue
        directive = fields[0]
        key = fields[1]
        value = fields[2][:-1]
        #print("Setting %s[%s] = %s" % (
            #directive,
            #key,
            #value,
        #))

        if directive == "host":
            hostMap[key] = value
        elif directive == "media":
            typeMap[key] = value
        elif directive == "parameter":
            parmMap[key] = value
        else:
            print("unrecognized config directive:", directive, line)
            sys.exit(1)

    confFile.close()

    return (typeMap, hostMap, parmMap)


if __name__ == "__main__":
    args = parse_arguments()
    print("Welcome to Jon's Teensy HTTP Server!")
    print("You have asked me to operate on port", args.port)
    print("Wahoo!")
    (typeMap, hostMap, parmMap) = load_conf_file()
    server = poller.Poller(args.port, typeMap, hostMap, parmMap)
    server.run()
