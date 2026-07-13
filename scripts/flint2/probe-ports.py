#!/usr/bin/env python3
"""Проверка доступных сервисов Flint2 (192.168.1.99) с HA-хоста."""
import socket
import sys

HOST = sys.argv[1] if len(sys.argv) > 1 else "192.168.1.99"
PORTS = [22, 80, 443, 8080, 8443, 8888, 51820, 53]

for port in PORTS:
    s = socket.socket()
    s.settimeout(2)
    try:
        s.connect((HOST, port))
        print(f"OPEN {port}")
    except OSError as exc:
        print(f"CLOSED {port} ({exc})")
    finally:
        s.close()
