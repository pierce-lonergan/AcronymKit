"""A pytest plugin that makes every outbound network primitive raise.

``acronymkit`` claims to perform no network I/O. This module is the mechanism
that turns that claim into a build failure when it stops being true: loaded as
a pytest plugin, it replaces the standard library's network entry points with
functions that raise :class:`AirGapError`, then runs the suite. A test that
opens a socket does not hang or quietly succeed against a live host -- it fails,
naming the call site.

Run it with::

    PYTHONPATH=tests python -m pytest -p airgap_socket_guard

``-p`` is not decoration. It is the whole point: see "Why plugin load time"
below.

Why hand-rolled rather than pytest-socket
-----------------------------------------
``pytest-socket`` is the obvious off-the-shelf answer and it was rejected for
two specific reasons, neither of them stylistic.

* **Version floor.** ``pytest-socket`` 0.8.0 requires Python >= 3.10. This
  project supports 3.9 and CI has 3.9 cells; a gate that cannot run on part of
  the support matrix is not a gate for that part of the matrix.
* **It patches too late.** ``pytest-socket`` installs its block in
  ``pytest_runtest_setup``, which runs after plugin loading, after conftest
  import and after collection -- so imports performed while collecting a test
  module are outside its coverage. "Phones home at import time" is precisely
  the behaviour an air-gap gate exists to catch, so a tool that cannot see
  import time is answering a different question.

Why plugin load time
--------------------
The patches are applied by a module-level :func:`install` call, i.e. the moment
pytest imports this module as a plugin, which is before conftest.py is
imported and before a single test module is collected. Everything that happens
after that point -- collection, import, fixtures, tests, teardown -- is covered.
That is also why the module must be loaded with ``-p`` rather than by being
imported from a conftest: ``-p`` plugins are loaded first.

The one exemption, and why it exists
------------------------------------
Sockets created *inside* :func:`socket.socketpair` are allowed, as are AF_UNIX
sockets anywhere. An exemption nobody can see is a hole, so here it is in full.

Windows has no ``socketpair(2)``. CPython's ``socket.py`` therefore defines
``_fallback_socketpair``, which synthesises one from a real TCP socket: it binds
a listener on ``127.0.0.1``, connects a second socket to it, accepts, and hands
back the pair. ``asyncio``'s ``ProactorEventLoop`` -- the default event loop on
Windows -- builds its self-pipe from exactly that call, so a blanket block stops
this suite's async tests dead: 28 of them, all in ``tests/test_batch.py``,
measured by deleting the exemption and rerunning on Windows/3.13. On Linux and
macOS the same call reaches ``AF_UNIX`` and the situation does not arise, which
is why this is a Windows-shaped hole rather than a general one.

The exemption is kept as narrow as the mechanism allows:

* it applies only while a frame belonging to CPython's own ``socketpair`` (or
  ``_fallback_socketpair``) code object is on the stack, within
  :data:`_FRAMES_TO_SEARCH` frames -- an alias captured before this module was
  imported still hits it, because the test is the code object, not the name;
* the only address a connect may reach under it is IPv4/IPv6 loopback; and
* AF_UNIX is allowed unconditionally because an AF_UNIX socket addresses a
  filesystem path, not a host, and cannot leave the machine.

Everything else -- every AF_INET/AF_INET6 socket, every ``connect``, every name
lookup in :mod:`socket`, every TLS wrap, every ``http.client`` connection --
raises.

Name resolution is guarded separately from the socket methods, and all five
entry points are patched rather than only ``getaddrinfo``. A DNS lookup creates
no socket object, so nothing else in this module can see it: a call to
``gethostbyname`` leaves the machine on its own. It is also an outbound event
in its own right, which is why it is refused rather than merely noted -- a
resolver answering from cache would otherwise hide half of a phone-home.

For the socket methods the constructor is the choke point, which is why
``connect_ex``, ``sendto`` and friends are left alone: they need a socket
object, and every way of getting one through the :mod:`socket` module runs
through the patched ``__init__``.

Two things the guard cannot reach, stated rather than glossed:

* ``_socket.socket`` is an immutable C type -- assigning to its ``__init__``
  raises ``TypeError`` -- so code that imports the accelerator module directly
  and builds a socket from it bypasses every patch here. Only the pure-Python
  ``socket.socket`` subclass, which is what all normal code uses, is covered.
* A C extension that calls ``connect(2)`` without going through CPython at all
  is invisible too, and for a harder reason: there is no Python-level call to
  patch in the first place.

Neither is a gap being waved away: both are the reason the ``air-gap`` CI job
also runs the public API inside a network namespace with no route, where the
kernel is what says no.

The positive control
--------------------
A guard with no positive control proves nothing: a typo in a patch name yields
a green suite that checks nothing, which is worse than no gate because it reads
as evidence. :func:`self_check` therefore performs real outbound attempts --
including a ``connect`` to RFC 5737 TEST-NET-1 on a genuine AF_INET socket
built through CPython's own unpatched constructor -- and fails the session if
any of them is *not* blocked. It runs in ``pytest_configure`` on every session
and its result is printed in the pytest header, so the evidence is in the log
rather than in a comment. ``python tests/airgap_socket_guard.py`` runs the same
control standalone, for anyone re-verifying this outside CI.
"""

from __future__ import annotations

import http.client
import socket
import ssl
import sys
from functools import partial
from typing import Any, Callable, Optional

__all__ = ["AirGapError", "install", "self_check"]


class AirGapError(RuntimeError):
    """Raised when guarded code reaches for the network.

    A dedicated type rather than ``OSError`` on purpose: library code that
    catches ``OSError`` around a socket call -- which is the normal, correct
    thing for library code to do -- would swallow the evidence and turn a
    violation into a silently degraded result. This inherits from
    ``RuntimeError`` so it travels through those handlers untouched.
    """


#: How far up the stack to look for CPython's ``socketpair`` when deciding
#: whether a socket is part of the self-pipe exemption, counted in ``f_back``
#: hops from the guarded call. Measured on Windows/3.13 by instrumenting
#: ``socket.socket.__init__``: the deepest real case is two hops, when
#: ``_fallback_socketpair`` calls ``socket.accept()`` and ``accept`` calls the
#: constructor. Four leaves margin for a CPython refactor while still stopping
#: well short of ``socketpair``'s own caller, which must not be exempt.
_FRAMES_TO_SEARCH = 4

#: Code objects belonging to CPython's ``socketpair`` implementation, captured
#: before anything is patched. Matching on the code object rather than on the
#: module attribute means an alias taken earlier (``asyncio.windows_utils``
#: binds one at import) is recognised too.
_SOCKETPAIR_CODES = frozenset(
    function.__code__
    for function in (socket.socketpair, getattr(socket, "_fallback_socketpair", None))
    if function is not None
)

#: ``AF_UNIX`` where the platform has it, ``None`` on Windows.
_AF_UNIX = getattr(socket, "AF_UNIX", None)

#: RFC 5737 TEST-NET-1. Reserved for documentation and guaranteed not to be
#: routed, so if a positive-control probe ever escapes the guard it reaches
#: nothing and fails fast rather than talking to a real host.
_BLACKHOLE_HOST = "192.0.2.1"
_BLACKHOLE_PORT = 80

#: Every name-resolution entry point :mod:`socket` exposes, mapped to arguments
#: that would make a real lookup, so :func:`self_check` can prove each one
#: refuses. ``getaddrinfo`` is what modern code uses, but the older helpers are
#: still exported, still resolve, and create no socket object on the way -- so
#: with only ``getaddrinfo`` patched, a lookup through ``gethostbyname`` would
#: leave the machine with nothing in this module able to see it. The host is a
#: real one because a probe that cannot resolve anyway proves nothing about
#: whether the guard is what stopped it.
_NAME_LOOKUP_PROBES: dict[str, tuple[Any, ...]] = {
    "getaddrinfo": ("pypi.org", 443),
    "gethostbyname": ("pypi.org",),
    "gethostbyname_ex": ("pypi.org",),
    "gethostbyaddr": ("pypi.org",),
    "getnameinfo": ((_BLACKHOLE_HOST, _BLACKHOLE_PORT), 0),
}

#: The unpatched callables, kept so the exemption can delegate and so
#: :func:`self_check` can build a genuine socket without going through the
#: guard it is testing.
_ORIGINALS: dict[str, Any] = {}

_INSTALLED = False
_CONTROL_RESULTS: tuple[str, ...] = ()


def _offender(depth: int = 3) -> str:
    """Describe the call site that tripped the guard.

    Args:
        depth: Stack depth of the offending frame, counted from this function.

    Returns:
        ``file:line in function()``, or ``"<unknown>"`` if the frame is gone.
    """
    try:
        frame = sys._getframe(depth)
    except ValueError:  # pragma: no cover - only if the stack is shorter
        return "<unknown>"
    return f"{frame.f_code.co_filename}:{frame.f_lineno} in {frame.f_code.co_name}()"


def _blocked(primitive: str, detail: str) -> AirGapError:
    """Build the exception for a blocked call.

    Args:
        primitive: The stdlib entry point that was called.
        detail: What it was asked to reach.

    Returns:
        An :class:`AirGapError` naming the primitive, the target and the
        caller, so the failure identifies the offender without a debugger.
    """
    return AirGapError(
        f"air-gap guard blocked {primitive} -> {detail}; called from {_offender()}. "
        "acronymkit performs no network I/O; see tests/airgap_socket_guard.py."
    )


def _under_socketpair() -> bool:
    """Return whether CPython's ``socketpair`` is on the calling stack."""
    frame: Optional[Any] = sys._getframe(1)
    for _ in range(_FRAMES_TO_SEARCH):
        frame = None if frame is None else frame.f_back
        if frame is None:
            return False
        if frame.f_code in _SOCKETPAIR_CODES:
            return True
    return False


def _is_loopback(address: Any) -> bool:
    """Return whether ``address`` is an IPv4/IPv6 loopback endpoint tuple."""
    if not isinstance(address, tuple) or not address:
        return False
    host = address[0]
    return isinstance(host, str) and (host.startswith("127.") or host == "::1")


def _guarded_socket_init(
    self: Any, family: int = -1, type: int = -1, proto: int = -1, fileno: Any = None
) -> None:
    """Refuse to construct a socket unless it falls under the exemption.

    Patched onto :class:`socket.socket` itself rather than rebound as the
    module attribute ``socket.socket``: rebinding the attribute only catches
    callers who go through the ``socket`` namespace and misses everything that
    did ``from socket import socket``, while the class is shared by all of them.

    Args:
        self: The socket being initialised.
        family: Address family; ``-1`` means ``AF_INET``.
        type: Socket type.
        proto: Protocol number.
        fileno: Existing descriptor to wrap, if any.

    Raises:
        AirGapError: For any socket outside the documented exemption.
    """
    exempt = (_AF_UNIX is not None and family == _AF_UNIX) or _under_socketpair()
    if not exempt:
        raise _blocked("socket.socket()", f"family={family} type={type} proto={proto}")
    _ORIGINALS["socket_init"](self, family, type, proto, fileno)


def _guarded_connect(self: Any, address: Any) -> Any:
    """Refuse to connect a socket to anything but an exempt loopback pair.

    Args:
        self: The socket being connected.
        address: The endpoint, in whatever shape the family uses.

    Returns:
        Whatever :meth:`socket.socket.connect` returns, for exempt calls.

    Raises:
        AirGapError: For every non-exempt endpoint.
    """
    exempt = (_AF_UNIX is not None and getattr(self, "family", None) == _AF_UNIX) or (
        _under_socketpair() and _is_loopback(address)
    )
    if not exempt:
        raise _blocked("socket.socket.connect()", repr(address))
    return _ORIGINALS["connect"](self, address)


def _guarded_create_connection(address: Any, *args: Any, **kwargs: Any) -> Any:
    """Refuse :func:`socket.create_connection` outright.

    Raises:
        AirGapError: Always. Nothing in the exemption goes through here.
    """
    raise _blocked("socket.create_connection()", repr(address))


def _guarded_name_lookup(primitive: str) -> Callable[..., Any]:
    """Build a replacement for one of :mod:`socket`'s name-resolution helpers.

    One factory rather than five near-identical functions because the only
    thing that varies is the name in the message, and five copies of a two-line
    body is five places for the next one to be forgotten.

    Args:
        primitive: The attribute of :mod:`socket` being replaced, used verbatim
            in the error so the failure names the call the offender made rather
            than whichever one happened to be patched first.

    Returns:
        A function that refuses whatever it is given.
    """

    def refuse(*args: Any, **kwargs: Any) -> Any:
        target = ", ".join([*(repr(a) for a in args), *(f"{k}={v!r}" for k, v in kwargs.items())])
        raise _blocked(f"socket.{primitive}()", target or "<no arguments>")

    refuse.__name__ = f"_guarded_{primitive}"
    refuse.__qualname__ = refuse.__name__
    return refuse


def _guarded_wrap_socket(self: Any, sock: Any, *args: Any, **kwargs: Any) -> Any:
    """Refuse :meth:`ssl.SSLContext.wrap_socket` outright.

    Redundant in principle -- there is no socket to wrap once the constructor
    is guarded -- and patched anyway, because "redundant in principle" is how
    coverage gaps are argued into existence.

    Raises:
        AirGapError: Always.
    """
    raise _blocked("ssl.SSLContext.wrap_socket()", repr(sock))


def _guarded_http_connect(self: Any) -> Any:
    """Refuse :meth:`http.client.HTTPConnection.connect` outright.

    Raises:
        AirGapError: Always.
    """
    host = getattr(self, "host", "?")
    port = getattr(self, "port", "?")
    raise _blocked("http.client.HTTPConnection.connect()", f"{host}:{port}")


def install() -> bool:
    """Patch every guarded network primitive. Idempotent.

    Called at module scope so the patches are in force from plugin load, before
    conftest import and collection.

    Returns:
        ``True`` if this call installed the patches, ``False`` if they were
        already in place.
    """
    global _INSTALLED
    if _INSTALLED:
        return False
    _ORIGINALS.update(
        socket_init=socket.socket.__init__,
        connect=socket.socket.connect,
        create_connection=socket.create_connection,
        wrap_socket=ssl.SSLContext.wrap_socket,
        http_connect=http.client.HTTPConnection.connect,
    )
    socket.socket.__init__ = _guarded_socket_init  # type: ignore[method-assign]
    socket.socket.connect = _guarded_connect  # type: ignore[method-assign]
    socket.create_connection = _guarded_create_connection  # type: ignore[assignment]
    ssl.SSLContext.wrap_socket = _guarded_wrap_socket  # type: ignore[method-assign]
    http.client.HTTPConnection.connect = _guarded_http_connect  # type: ignore[method-assign]
    for primitive in _NAME_LOOKUP_PROBES:
        _ORIGINALS[primitive] = getattr(socket, primitive)
        setattr(socket, primitive, _guarded_name_lookup(primitive))
    _INSTALLED = True
    return True


def _expect_blocked(description: str, probe: Callable[[], Any]) -> str:
    """Run one positive-control probe and require the guard to stop it.

    Args:
        description: What the probe attempts, for the report line.
        probe: A zero-argument callable performing the attempt.

    Returns:
        A one-line record of the block, for the pytest header.

    Raises:
        AirGapError: If the probe succeeded, or failed for any reason other
            than the guard -- both mean the guard did not do the blocking.
    """
    try:
        probe()
    except AirGapError:
        return f"{description}: blocked"
    except Exception as exc:
        # Anything else -- a real OSError from a real connection attempt, a
        # TypeError from a signature drift -- means the guard was not what
        # stopped the call, which is the failure this control exists to catch.
        raise AirGapError(
            f"positive control failed: {description} raised {exc!r} instead of being "
            "blocked by the guard, so the guard is not what stopped it"
        ) from exc
    raise AirGapError(
        f"positive control failed: {description} was not blocked. The guard is inert -- "
        "a patch target has been renamed or install() did not run."
    )


def self_check() -> tuple[str, ...]:
    """Prove the guard blocks real outbound calls, and that the exemption lives.

    Every patched primitive is probed and must refuse; the one documented
    exemption is probed and must still work. Probing all of them rather than a
    representative sample is the point: a patch that was never applied and a
    patch that was applied to the wrong name look identical from the outside,
    and the only difference between them and a working guard is a probe.

    The exemption probe is not a formality either: if the ``socketpair``
    exemption stopped working the async tests would fail with an
    unrelated-looking error on Windows, and the reason should be stated here
    rather than discovered there.

    Returns:
        One line per probe, in order, for the pytest report header.

    Raises:
        AirGapError: If any probe behaves differently.
    """
    blackhole = (_BLACKHOLE_HOST, _BLACKHOLE_PORT)

    # A genuine AF_INET socket, built through CPython's own constructor so the
    # guard under test cannot be the reason it exists, then asked to connect.
    # This is the probe that matters: an actual outbound connection attempt on
    # a real descriptor, stopped by the patched connect and nothing else.
    live = socket.socket.__new__(socket.socket)
    _ORIGINALS["socket_init"](live, socket.AF_INET, socket.SOCK_STREAM, 0, None)
    try:
        results = [
            _expect_blocked(
                "socket.socket.connect() on a real AF_INET descriptor",
                lambda: live.connect(blackhole),
            ),
            _expect_blocked(
                "socket.socket(AF_INET, SOCK_STREAM)",
                lambda: socket.socket(socket.AF_INET, socket.SOCK_STREAM),
            ),
            _expect_blocked(
                "socket.create_connection()",
                lambda: socket.create_connection(blackhole, timeout=1),
            ),
            _expect_blocked(
                "ssl.SSLContext.wrap_socket()",
                lambda: ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT).wrap_socket(None),
            ),
            _expect_blocked(
                "http.client.HTTPConnection.connect()",
                lambda: http.client.HTTPConnection(
                    _BLACKHOLE_HOST, _BLACKHOLE_PORT, timeout=1
                ).connect(),
            ),
        ]
    finally:
        live.close()  # close() is not patched; the descriptor is real and must go back

    # Every name-resolution entry point, not just getaddrinfo. These create no
    # socket, so nothing else in this module would notice if one were missed.
    for primitive, arguments in _NAME_LOOKUP_PROBES.items():
        results.append(
            _expect_blocked(
                f"socket.{primitive}()",
                partial(getattr(socket, primitive), *arguments),
            )
        )

    # The documented exemption, exercised end to end: asyncio's self-pipe is
    # built from this call and must still work.
    left, right = socket.socketpair()
    # `.name`, not repr: AddressFamily is an IntEnum, so str() renders it as the
    # bare number on 3.11+ and repr() as `<AddressFamily.AF_INET: 2>`. The name
    # is the part a reader of the CI log needs.
    family = getattr(left.family, "name", left.family)
    try:
        left.sendall(b"x")
        if right.recv(1) != b"x":  # pragma: no cover - would be a broken platform
            raise AirGapError("socketpair exemption is broken: the pair does not round-trip")
    finally:
        left.close()
        right.close()
    results.append(f"socket.socketpair() (documented exemption, family={family}): allowed")
    return tuple(results)


# --------------------------------------------------------------------------
# pytest hooks
# --------------------------------------------------------------------------
def pytest_configure(config: Any) -> None:
    """Run the positive control once the plugin is loaded.

    The patches themselves went in at import; this only proves they took.

    Args:
        config: The pytest config object. Unused.

    Raises:
        AirGapError: If the guard is not actually blocking.
    """
    global _CONTROL_RESULTS
    install()
    _CONTROL_RESULTS = self_check()


def pytest_report_header(config: Any) -> list[str]:
    """Print the guard's status and its positive control in the run header.

    Args:
        config: The pytest config object. Unused.

    Returns:
        Header lines, so the evidence lands in the CI log next to the results
        it is meant to qualify.
    """
    return ["air-gap socket guard: active", *(f"  {line}" for line in _CONTROL_RESULTS)]


# Patch on import -- see "Why plugin load time" in the module docstring.
install()


if __name__ == "__main__":  # pragma: no cover - standalone re-verification
    for line in self_check():
        print(line)
    print("air-gap socket guard: positive control passed")
