import socket
import threading
import marshal
import pickle
import bz2
import pprint
import sys

INTERFACE = ''  # all interfaces
MULTICAST_DEST = '234.254.55.15'
MULTICAST_PORT = 39049  # chosen completely at random
TCP_PORT = 8193


def responder_thread(s: socket.socket, reply_with):
    while True:
        msg, from_ = s.recvfrom(65536)
        if msg == b'\x00\x01\x00':  # something arbitrary that would not ordinarily be transmitted
            s.sendto(reply_with, from_)


def accepter_thread(s, clients):
    while True:
        conn, addr = s.accept()
        #clients[addr[0]] = (bz2.BZ2File(conn.makefile('rb')), bz2.BZ2File(conn.makefile('wb'), 'w'))
        clients[addr[0]] = (conn.makefile('rb'), conn.makefile('wb'))


if __name__=='__main__':
    multicast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    multicast_socket.setsockopt(socket.IPPROTO_IP, socket.SO_REUSEADDR, b'\1')
    multicast_socket.bind((INTERFACE, MULTICAST_PORT))
    multicast_socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, False)
    multicast_socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, socket.inet_aton(MULTICAST_DEST)
                                + socket.inet_aton(multicast_socket.getsockname()[0]))

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((INTERFACE, TCP_PORT))
    server_socket.listen()
    clients = {}
    threading.Thread(target=accepter_thread, args=(server_socket, clients)).start()
    threading.Thread(target=responder_thread, args=(multicast_socket, b'\xff')).start()  # could change this for a hardcoded packed ip

    lines = {}
    # Remote Python interpreter with BASIC style line numbers.
    # If the python code sets the magic variable "output" its value will be returned to the server and displayed.
    while True:
        line = input('> ')
        if not line: continue
        if line[0] == '!':
            if line[1:] == 'list':
                for k in clients:
                    print(' - '+k)
            else:
                client = clients.get(line[1:])
                if not client:
                    print('No such client')
                else:
                    rfile, wfile = client
                    code = '\n'.join(lines[k] for k in sorted(lines))
                    try:
                        code = compile(code, '<remoteexec>', 'exec')
                    except BaseException as e:  # this *should* only raise SyntaxError but you can't be too careful
                        # let the user know they fucked up
                        import traceback
                        formatted_tb = traceback.format_exception(type(e), e, e.__traceback__)
                        # write error output to stdout rather than stderr because it's a console app
                        # and IDEs are weird about what happens when you write to both.
                        # I'm lazy and my solution to this is just to avoid the issue by writing all output to stdout.
                        sys.stdout.writelines(formatted_tb)
                    else:
                        #with bz2.BZ2File(wfile, 'w') as f:
                        marshal.dump(code, wfile)
                        wfile.flush()
                        # was gonna do compression, but it didn't work out
                        # i know how to implement it but i'm too tired right now
                        # i'll do it tomorrow
                        #with bz2.BZ2File(rfile, 'r') as f:
                        output = pickle.load(rfile)
                        if output is not None:
                            pprint.pprint(output)
                        lines.clear()
        else:
            head, sep, tail = line.partition(' ')
            if not sep:
                print('Usage: !list | ![client IP] | [lineno] [line]')
            try:
                head = int(head)
            except ValueError:
                print('lines must begin with a BASIC style line number')
                continue
            lines[head] = tail
