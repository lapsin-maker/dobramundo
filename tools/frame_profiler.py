"""Instrumentação aninhada: tempo inclusivo e exclusivo, sem somar escopos."""

from __future__ import annotations

import time
from functools import wraps


class FrameProfiler:
    def __init__(self, clock=time.perf_counter):
        self.clock = clock
        self.samples = {}
        self.exclusive = {}
        self.stack = []

    def clear(self):
        self.samples.clear()
        self.exclusive.clear()

    def instrument(self, obj, name, key):
        original = getattr(obj, name)

        @wraps(original)
        def measured(*args, **kwargs):
            start = self.clock()
            children = [0.0]
            self.stack.append(children)
            try:
                return original(*args, **kwargs)
            finally:
                elapsed = self.clock() - start
                self.stack.pop()
                if self.stack:
                    self.stack[-1][0] += elapsed
                self.samples.setdefault(key, []).append(elapsed * 1000)
                self.exclusive.setdefault(key, []).append(max(0.0, elapsed - children[0]) * 1000)

        setattr(obj, name, measured)
