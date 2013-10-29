
import argparse


class ArgumentsParser:
    def parse_arguments(self):
        ''' parse arguments, which include '-p' for port '''
        parser = argparse.ArgumentParser(
            prog='Jon`s HTTP Server',
            description='A simple echo server that handles one client at a time',
            add_help=True
        )
        parser.add_argument(
            '-p', '--port',
            type=int,
            action='store',
            help='port the server will bind to',
            default=3000
        )
        self.args = parser.parse_args()


if __name__ == "__main__":
    argParser = ArgumentsParser()
    argParser.parse_arguments()
    print("Welcome to Jon's Teensy HTTP Server!")
    print("You have asked me to operate on port %d", argParser.args.port)
    print("Wahoo!")
