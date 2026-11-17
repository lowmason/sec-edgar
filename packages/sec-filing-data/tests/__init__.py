"""Tests read only tests/fixtures/ and temporary folders. They never reach the network."""

import socket


def _refuse(*args, **kwargs):
    raise OSError("network access is blocked in tests")


socket.socket.connect = _refuse
socket.socket.connect_ex = _refuse
socket.getaddrinfo = _refuse
