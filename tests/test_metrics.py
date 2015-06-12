
import time
import unittest

from alerta.app.metrics import Timer


class MetricsTestCase(unittest.TestCase):

    def setUp(self):

        pass

    def test_metrics(self):

        test_timer = Timer('alerts', 'test', 'Test timer', 'total time to process timed events')
        recv_started = test_timer.start_timer()
        time.sleep(1)
        test_timer.stop_timer(recv_started)

        result = [t for t in Timer.get_timers() if t['title'] == 'Test timer'][0]

        self.assertGreaterEqual(result['count'], 1)
        self.assertGreaterEqual(result['totalTime'], 999)