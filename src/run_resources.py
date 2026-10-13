"""Optional POSIX telemetry; unavailable measurements are None, never zero.

This module is used by experiment drivers only. It is not imported by the
semantic engine, certificate producer, or independent checker.
"""
from __future__ import annotations

import os
import sys

try:
    import resource
except ImportError:
    resource = None

POSIX_LIMITS_AVAILABLE = resource is not None and os.name == 'posix'


def peak_rss_kib() -> int | None:
    if resource is None:
        return None
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(value / 1024) if sys.platform == 'darwin' else int(value)


def child_usage() -> tuple[float, int] | None:
    if resource is None:
        return None
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    rss = usage.ru_maxrss
    if sys.platform == 'darwin':
        rss /= 1024
    return usage.ru_utime + usage.ru_stime, int(rss)


def apply_child_limits() -> None:
    if not POSIX_LIMITS_AVAILABLE:
        raise RuntimeError('POSIX address-space and CPU limits are unavailable')
    resource.setrlimit(resource.RLIMIT_AS, (2500 * 1024 * 1024,) * 2)
    resource.setrlimit(resource.RLIMIT_CPU, (2700,) * 2)
