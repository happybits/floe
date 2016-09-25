#!/usr/bin/env python

# std lib imports
from wsgiref.simple_server import make_server
import argparse

# import library
import floe

app = floe.floe_server()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='kick off the help server')
    parser.add_argument('-p', '--port', default=3049, type=int,
                        help="specify the port to listen to")

    args = parser.parse_args()
    httpd = make_server(
        '127.0.0.1',
        args.port,
        app)

    print("starting server on port %s" % args.port)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("done")
