"""Test-only network/provider denial with scoped, exact loopback fixture origins.

This module is outside the installed package. The runner installs it before test
imports; support imports install it for focused runs and spawned fixture helpers.
"""
from __future__ import annotations

import builtins
import importlib
import socket
import sys
from collections import Counter
from contextlib import contextmanager
from functools import wraps
from threading import RLock
from urllib.parse import urlsplit

_INSTALLED = False
_ORIGINS: Counter[tuple[str, int]] = Counter()
_LOCK = RLock()
_AUTH_CLASSES: set[type] = set()
_IMPORT = builtins.__import__


def _deny_auth(*args, **kwargs):
    raise AssertionError('offline tests forbid credential construction and token activity')


def _guard_loaded_auth() -> None:
    for name, module in tuple(sys.modules.items()):
        if module is None or not (name.startswith('azure.identity') or name == 'msal'):
            continue
        for label, value in tuple(vars(module).items()):
            if not isinstance(value, type) or value in _AUTH_CLASSES:
                continue
            is_credential = name.startswith('azure.identity') and label.endswith('Credential') and value.__module__.startswith('azure.identity')
            is_msal_provider = name == 'msal' and (label.endswith('Application') or label == 'ManagedIdentityClient') and value.__module__.startswith('msal')
            if not (is_credential or is_msal_provider):
                continue
            _AUTH_CLASSES.add(value)
            value.__init__ = _deny_auth
            for method in dir(value):
                if method in ('get_token', 'get_token_info', 'initiate_auth_code_flow') or method.startswith('acquire_token'):
                    setattr(value, method, _deny_auth)


def _guarded_import(name, *args, **kwargs):
    module = _IMPORT(name, *args, **kwargs)
    imported = getattr(module, '__name__', '')
    if name.startswith(('azure.identity', 'msal')) or imported.startswith(('azure.identity', 'msal')):
        _guard_loaded_auth()
    return module


def _require_address(address) -> None:
    if not isinstance(address, tuple) or len(address) < 2:
        raise AssertionError('offline tests allow only selected loopback fixture addresses')
    host, port = address[:2]
    if isinstance(port, str) and port.isdecimal():
        port = int(port)
    with _LOCK:
        allowed = type(port) is int and _ORIGINS[(host, port)] > 0
    if not allowed:
        raise AssertionError('offline tests refuse an unselected network address')


def _require_host(host) -> None:
    with _LOCK:
        allowed = host in ('127.0.0.1', '::1') and any(key[0] == host and count > 0 for key, count in _ORIGINS.items())
    if not allowed:
        raise AssertionError('offline tests refuse unselected name resolution')


def _connection_guard(operation):
    @wraps(operation)
    def guarded(sock, address, *args, **kwargs):
        _require_address(address)
        return operation(sock, address, *args, **kwargs)
    return guarded


def _lookup_guard(operation):
    @wraps(operation)
    def guarded(host, port, *args, **kwargs):
        _require_address((host, port))
        return operation(host, port, *args, **kwargs)
    return guarded


def _host_guard(operation):
    @wraps(operation)
    def guarded(host, *args, **kwargs):
        _require_host(host)
        return operation(host, *args, **kwargs)
    return guarded


def _sendto_guard(operation):
    @wraps(operation)
    def guarded(sock, data, *args):
        _require_address(args[-1] if args else None)
        return operation(sock, data, *args)
    return guarded


def _sendmsg_guard(operation):
    @wraps(operation)
    def guarded(sock, buffers, ancdata=(), flags=0, address=None):
        _require_address(address)
        return operation(sock, buffers, ancdata, flags, address)
    return guarded


def install() -> None:
    """Deny real Python socket/DNS and Azure/MSAL provider work before tests run."""
    global _INSTALLED
    if _INSTALLED:
        return
    _INSTALLED = True
    socket.socket.connect = _connection_guard(socket.socket.connect)
    socket.socket.connect_ex = _connection_guard(socket.socket.connect_ex)
    socket.socket.sendto = _sendto_guard(socket.socket.sendto)
    if hasattr(socket.socket, 'sendmsg'):
        socket.socket.sendmsg = _sendmsg_guard(socket.socket.sendmsg)
    socket.getaddrinfo = _lookup_guard(socket.getaddrinfo)
    original_nameinfo = socket.getnameinfo
    @wraps(original_nameinfo)
    def getnameinfo(address, flags):
        _require_address(address)
        return original_nameinfo(address, flags)
    socket.getnameinfo = getnameinfo
    for name in ('gethostbyname', 'gethostbyname_ex', 'gethostbyaddr'):
        setattr(socket, name, _host_guard(getattr(socket, name)))
    # These imports load code only. Constructors and token methods are blocked
    # before returning; later Azure identity imports are guarded as well.
    builtins.__import__ = _guarded_import
    importlib.import_module('azure.identity')
    importlib.import_module('msal')
    _guard_loaded_auth()


@contextmanager
def selected_origin(origin: str):
    """Authorize one explicit fixture port until its bounded fixture is closed."""
    parsed = urlsplit(origin)
    if (parsed.scheme != 'http' or parsed.hostname not in ('127.0.0.1', '::1') or
            parsed.port is None or not 1 <= parsed.port <= 65535 or parsed.username or
            parsed.password or parsed.path or parsed.query or parsed.fragment):
        raise ValueError('test origin must be an exact literal loopback HTTP origin')
    address = parsed.hostname, parsed.port
    with _LOCK:
        _ORIGINS[address] += 1
    try:
        yield
    finally:
        with _LOCK:
            _ORIGINS[address] -= 1
            if not _ORIGINS[address]:
                del _ORIGINS[address]


def guarded_transport_child(transport, cancellation, channel, *, target, origin):
    """Spawn carries only this selected fixture origin and its original target."""
    install()
    with selected_origin(origin):
        return target(transport, cancellation, channel)


def main(argv=None) -> None:
    install()
    import unittest
    unittest.main(module=None, argv=['unittest', *(sys.argv[1:] if argv is None else argv)])


if __name__ in ('__main__', '__mp_main__'):
    # Support and spawn targets share one guard instance when run as a file.
    sys.modules.setdefault('network_guard', sys.modules[__name__])
if __name__ == '__main__':
    main()
