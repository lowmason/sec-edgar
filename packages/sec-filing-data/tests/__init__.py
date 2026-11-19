"""Tests read only tests/fixtures/ and temporary folders. They never reach the network."""

import socket

from sec_filing_data import version


def _refuse(*args, **kwargs):
    raise OSError("network access is blocked in tests")


socket.socket.connect = _refuse
socket.socket.connect_ex = _refuse
socket.getaddrinfo = _refuse

# The suite runs on a tree with edits in progress, so every test sees one clean commit.
TEST_COMMIT = "5ca1ab1e" * 5
TEST_CHECKOUT = version.Checkout(TEST_COMMIT, True, None)
version.current_checkout = lambda: TEST_CHECKOUT
