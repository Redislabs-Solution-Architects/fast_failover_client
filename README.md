Redis failover test client
===

Connect to a redis server, PING it repeatedly, and reconnect upon each disconnect.

    ./fast_failover_client.py --help

    usage: fast_failover_client.py [-h] [--host HOST] [--port PORT]
                                   [--connect-timeout CONNECT_TIMEOUT]
                                   [--connect-retry-interval CONNECT_RETRY_INTERVAL]
                                   [--heartbeat-socket-timeout HEARTBEAT_SOCKET_TIMEOUT]
                                   [--heartbeat-interval HEARTBEAT_INTERVAL]
                                   [--heartbeat-key HEARTBEAT_KEY]
                                   [--password PASSWORD]
                                   [--tls TLS]]

    optional arguments:
      -h, --help            show this help message and exit
      --host HOST           Server address (default: localhost)
      --port PORT           Server port (default: 6379)
      --connect-timeout CONNECT_TIMEOUT
                            Timeout (secs) for individual connect attempts
                            (default: 0.5)
      --connect-retry-interval CONNECT_RETRY_INTERVAL
                            Connect (secs) retry interval time (default: 0.1)
      --heartbeat-socket-timeout HEARTBEAT_SOCKET_TIMEOUT
                            PING heartbeat socket timeout (secs) (default: 0.3)
      --heartbeat-interval HEARTBEAT_INTERVAL
                            PING heartbeat interval time (secs) (default: 0.1)
      --heartbeat-key HEARTBEAT_KEY
                            Redis key name to use for heartbeat (default: None)
      --password PASSWORD   Password (default: None)
      --tls <boolean>       Use non-mutual TLS (default: False)

What's New
---
* python3 support
* AUTH password support
* ipv6 localhost resolution
* Support for non-mutual TLS (w/SNI)
