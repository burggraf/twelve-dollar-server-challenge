"""One main-thread Linux wall timer covering load AND blocking review stdin.

Arm once from the durable ledger's absolute monotonic deadline, never per hold.
DeadlineExpired deliberately bypasses ordinary Exception handlers; the concrete
controller's outer finally must stop only recorded exact-owned child containers.
"""
import math
import signal
import time


class DeadlineExpired(BaseException):
    pass


class HardDeadline:
    def __init__(self):
        self.used=False;self.installed=False;self.previous=None

    def arm(self,absolute_monotonic):
        if self.used:raise RuntimeError('Whole-sequence timer cannot be reset or reauthorized')
        now=time.monotonic()
        if type(absolute_monotonic) not in (int,float) or not math.isfinite(absolute_monotonic) or absolute_monotonic-now>14400:
            raise ValueError('Finite approved absolute deadline required')
        if signal.getitimer(signal.ITIMER_REAL)!=(0.,0.):
            raise RuntimeError('Existing native timer must not be overwritten')
        self.used=True
        remaining=absolute_monotonic-now
        if remaining<=0:raise DeadlineExpired('Shared diagnostic/full sequence expired')
        self.previous=signal.getsignal(signal.SIGALRM)
        signal.signal(signal.SIGALRM,self._expired);self.installed=True
        signal.setitimer(signal.ITIMER_REAL,remaining)

    def _expired(self,number,frame):
        raise DeadlineExpired('Shared diagnostic/full sequence expired')

    def close(self):
        if self.installed:
            signal.setitimer(signal.ITIMER_REAL,0)
            signal.signal(signal.SIGALRM,self.previous);self.installed=False
