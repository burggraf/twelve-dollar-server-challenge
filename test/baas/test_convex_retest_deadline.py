"""Real native signal/blocked-IO tests. No serving process or load is started."""
import importlib.util
import math
import os
from pathlib import Path
import signal
import sys
import time
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
if importlib.util.find_spec('convex_retest_deadline'):
    import convex_retest_deadline as deadline
else:deadline=None


class NativeHardDeadline(unittest.TestCase):
    def create(self):
        factory=getattr(deadline,'HardDeadline',None)
        self.assertTrue(callable(factory),'Missing whole-sequence native hard interruption')
        value=factory();self.addCleanup(value.close);return value

    def block(self):
        reader,writer=os.pipe()
        try:os.read(reader,1)
        finally:os.close(reader);os.close(writer)

    def test_arming_interrupts_blocking_stdin_without_polling_or_another_command(self):
        timer=self.create();start=time.monotonic();timer.arm(start+.03)
        with self.assertRaises(deadline.DeadlineExpired):self.block()
        self.assertLess(time.monotonic()-start,1.)

    def test_timeout_is_not_swallowed_by_ordinary_operation_exception_handlers(self):
        timer=self.create();timer.arm(time.monotonic()+.03)
        with self.assertRaises(deadline.DeadlineExpired):
            try:self.block()
            except Exception:self.fail('Deadline must reach outer finally cleanup')

    def test_invalid_nonfinite_or_excessive_budget_cannot_install_a_timer(self):
        timer=self.create()
        for value in [True,None,float('nan'),float('inf'),time.monotonic()+14401]:
            with self.subTest(value=value),self.assertRaises(ValueError):timer.arm(value)
        self.assertEqual(signal.getitimer(signal.ITIMER_REAL),(0.,0.))

    def test_already_expired_sequence_does_not_get_a_new_allowance(self):
        timer=self.create()
        with self.assertRaises(deadline.DeadlineExpired):timer.arm(time.monotonic()-1)
        with self.assertRaises(RuntimeError):timer.arm(time.monotonic()+5)

    def test_review_or_capacity_phase_cannot_rearm_and_reset_the_sequence(self):
        timer=self.create();timer.arm(time.monotonic()+5)
        before=signal.getitimer(signal.ITIMER_REAL)[0]
        with self.assertRaises(RuntimeError):timer.arm(time.monotonic()+20)
        self.assertLessEqual(signal.getitimer(signal.ITIMER_REAL)[0],before)

    def test_close_restores_the_previous_handler_and_does_not_reauthorize_arm(self):
        previous=signal.getsignal(signal.SIGALRM);timer=self.create();timer.arm(time.monotonic()+5)
        timer.close();self.assertEqual(signal.getsignal(signal.SIGALRM),previous)
        self.assertEqual(signal.getitimer(signal.ITIMER_REAL),(0.,0.))
        with self.assertRaises(RuntimeError):timer.arm(time.monotonic()+5)

    def test_existing_native_timer_is_not_silently_overwritten(self):
        timer=self.create();signal.setitimer(signal.ITIMER_REAL,5)
        try:
            with self.assertRaises(RuntimeError):timer.arm(time.monotonic()+20)
            self.assertGreater(signal.getitimer(signal.ITIMER_REAL)[0],4.)
        finally:signal.setitimer(signal.ITIMER_REAL,0)

    def test_construction_does_not_start_the_four_hour_diagnostic_clock(self):
        self.create();self.assertEqual(signal.getitimer(signal.ITIMER_REAL),(0.,0.))


if __name__=='__main__':unittest.main(verbosity=2)
