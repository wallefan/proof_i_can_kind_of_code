import socket
import threading
import marshal
import pickle
import bz2
import types
import pickletools
import io

MULTICAST_INTERFACE = ''
MULTICAST_DEST = '234.254.55.15'
MULTICAST_PORT = 39049  # chosen completely at random
TCP_PORT = 8193


def responder_thread(s: socket.socket, reply_with):
    while True:
        msg, from_ = s.recvfrom(65536)
        if msg == b'\x00\x01\x00':  # something arbitrary that would not ordinarily be transmitted
            s.sendto(reply_with, from_)


if __name__ == '__main__':
    multicast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    multicast_socket.setsockopt(socket.IPPROTO_IP, socket.SO_REUSEADDR, True)
    multicast_socket.bind((MULTICAST_INTERFACE, 0))
    # multicast_socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, False)  # don't route our own messages back at us
    # multicast_socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, socket.inet_aton(MULTICAST_DEST)
    #                             + socket.inet_aton(multicast_socket.getsockname()[0]))
    multicast_socket.sendto(b'\x00\x01\x00', (MULTICAST_DEST, MULTICAST_PORT))
    server_ip, from_ = multicast_socket.recvfrom(4)
    if server_ip == b'\xff':
        server_ip = socket.inet_aton(from_[0])
    # threading.Thread(target=responder_thread, args=(multicast_socket, server_ip)).start()
    # pycharm autoformatting is wack but i don't care enough to argue with it.
    with socket.create_connection((socket.inet_ntoa(server_ip), TCP_PORT)) as sock, sock.makefile('rb') as rfile,\
            sock.makefile('wb') as wfile:
        print('found a master at', sock.getsockname()[0])
        locals_ = {}
        while True:  # terminate this loop by making it call exit() idfc
            code = marshal.load(rfile)
            exec(code, locals_)
            pickle.dump(locals_.get('output', None), wfile)
            wfile.flush()
