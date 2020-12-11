#!/usr/bin/env python3

"""
Redis failover test client

Connect to a given redis server, PING it repeatedly and reconnect upon each disconnect.
"""

import argparse
import socket
import time
import ssl
from datetime import datetime


class TestClient(object):
    def __init__(self, args):
        self.host = args.host
        self.port = args.port
        self.connect_timeout = args.connect_timeout
        self.connect_retry_interval = args.connect_retry_interval
        self.heartbeat_socket_timeout = args.heartbeat_socket_timeout
        self.heartbeat_interval = args.heartbeat_interval
        if args.heartbeat_key:
            self.hb_command = '*3\r\n' \
                              '$3\r\n' \
                              'SET\r\n' \
                              '$%d\r\n' \
                              '%s\r\n' \
                              '$5\r\n' \
                              'value\r\n' % (len(args.heartbeat_key),
                                             args.heartbeat_key)
            self.hb_expected_reply = '+OK\r\n'
        else:
            self.hb_command = '*1\r\n' \
                              '$4\r\n' \
                              'PING\r\n'
            self.hb_expected_reply = '+PONG\r\n'

        self.auth_command = None
        if args.password:
            self.auth_command = '*2\r\n' \
                                '$4\r\n' \
                                'AUTH\r\n' \
                                '$%d\r\n' \
                                '%s\r\n' % (len(args.password), args.password)
            self.auth_expected_reply = '+OK\r\n'

        self.sock = None
        self.last_pong_time = None
        self.addrinfo = []
        self.sslcontext = None
        self.ssock = None
        if args.tls:
            self.tls = True

    def log_event(self, text):
        print('[%s] %s' % (datetime.now().strftime('%d-%b-%g %H:%M:%S.%f',), text))

    def resolve_addr(self):
        self.log_event('[I] Resolving %s' % self.host)
        try:
            addrinfo = socket.getaddrinfo(self.host, self.port, 0, 0,
                                          socket.IPPROTO_TCP)
            self.log_event('    -> %s' % ', '.join(
                ai[4][0] for ai in addrinfo))
        except socket.error as err:
            self.log_event('[E] getaddrinfo failed (%s)' % err)
            return

        self.addrinfo = list(addrinfo)

    def connect(self):
        self.sock = None
        while self.sock is None:
            if not self.addrinfo:
                self.resolve_addr()
            while len(self.addrinfo) > 0:
                family, socktype, proto, canonname, sockaddr = self.addrinfo[0]
                addr, port = sockaddr[:2]
                try:
                    self.sock = socket.create_connection((addr, port), 
                        timeout=self.connect_timeout)
                    # currently only supports non-mutual TLS
                    if self.tls:
                        self.log_event('[I] Using non-mutual TLS')
                        self.sslcontext = ssl.SSLContext(ssl.PROTOCOL_TLS)
                        self.sslcontext.verify_mode = ssl.CERT_NONE 
                        self.ssock = self.sslcontext.wrap_socket(
                            self.sock, 
                            server_hostname=self.host, # required for sni
                            do_handshake_on_connect=True)

                    break
                except socket.error as err:
                    self.log_event('[E] cannot connect to %s:%s (%s)' %
                                   (addr, port, err))
                    self.addrinfo.pop(0)

            if self.sock is not None:
                self.log_event('[I] Connection to %s:%d established.' %
                               (addr, port))
                return

            time.sleep(self.connect_retry_interval)

    def heartbeat(self):
        if self.tls:
            self.ssock.settimeout(self.heartbeat_socket_timeout)
        else: 
            self.sock.settimeout(self.heartbeat_socket_timeout)
        
        responses = 0
        while True:
            try:
                if self.tls:
                    self.ssock.send(self.hb_command.encode())
                    response = self.ssock.recv(512).decode()
                else: 
                    self.sock.send(self.hb_command.encode())
                    response = self.sock.recv(512).decode()

                if not response:
                    self.log_event('[E] Server connection dropped')
                    break
                if response != self.hb_expected_reply:
                    self.log_event('[E] Unexpected protocol response: %s' % response)
                    break
            except socket.error as err:
                self.log_event('[E] PING %s' % err)
                break
            now = time.time()
            if responses == 0 and self.last_pong_time:
                self.log_event('[I] First successful response, %.2f after previous one' % (
                    now - self.last_pong_time))
            responses += 1
            self.last_pong_time = now
            time.sleep(self.heartbeat_interval)

    def auth(self):
        try:
            if self.tls:
                self.ssock.send(self.auth_command.encode())
                response = self.ssock.recv(512).decode()
            else: 
                self.sock.send(self.auth_command.encode())
                response = self.sock.recv(512).decode()
            if not response:
                self.log_event('[E] Server connection dropped')
            if response != self.auth_expected_reply:
                self.log_event('[E] Unexpected protocol response: %s' % response)
        except socket.error as err:
            self.log_event('[E] AUTH %s' % err)

    def run(self):
        while True:
            self.connect()
            if self.auth_command:
                self.auth()
            self.heartbeat()
            try:
                self.sock.shutdown(socket.SHUT_RDWR)
            except socket.error:
                pass
            self.sock = None


def main():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description=__doc__)
    parser.add_argument(
        '--host', type=str, help='Server address',
        default='localhost')
    parser.add_argument(
        '--port', type=int, help='Server port',
        default=6379)
    parser.add_argument(
        '--connect-timeout', type=int, help='Timeout (secs) for individual connect attempts',
        default=0.5)
    parser.add_argument(
        '--connect-retry-interval', type=float, help='Connect (secs) retry interval time',
        default=0.1)
    parser.add_argument(
        '--heartbeat-socket-timeout', type=float, help='PING heartbeat socket timeout (secs)',
        default=0.3)
    parser.add_argument(
        '--heartbeat-interval', type=float, help='PING heartbeat interval time (secs)',
        default=0.1)
    parser.add_argument(
        '--heartbeat-key', type=str, help='Redis key name to use for heartbeat',
        default=None)
    parser.add_argument(
        '--password', type=str, help='Password',
        default=None)
    parser.add_argument(
        '--tls', type=bool, help='Use non-mutual TLS: example \"--tls True\"',
        default=False)   
    args = parser.parse_args()
    TestClient(args).run()


if __name__ == '__main__':
    main()

