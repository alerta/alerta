
import time
import unittest

from alerta.app.metrics import Gauge, Timer


class MetricsTestCase(unittest.TestCase):

    def setUp(self):

        pass

    def test_metrics(self):

        test_gauge = Gauge(group='test', name='gauge', title='Test gauge', description='total time to process timed events')
        test_gauge.set(500)

        gauge = [g for g in Gauge.get_gauges() if g.title == 'Test gauge'][0]
        self.assertGreaterEqual(gauge.value, 500)

        test_timer = Timer(group='test', name='timer', title='Test timer', description='total time to process timed events')
        recv_started = test_timer.start_timer()
        time.sleep(1)
        test_timer.stop_timer(recv_started)

        timer = [t for t in Timer.get_timers() if t.title == 'Test timer'][0]
        self.assertGreaterEqual(timer.count, 1)
        self.assertGreaterEqual(timer.total_time, 999)
