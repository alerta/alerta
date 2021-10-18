import time
import unittest

from alerta.app import create_app, db
from alerta.models.metrics import Gauge, Timer


class MetricsTestCase(unittest.TestCase):

    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()

    def tearDown(self):
        db.destroy()

    def test_metrics(self):
        with self.app.test_request_context():
            self.app.preprocess_request()

            test_gauge = Gauge(group='test', name='gauge', title='Test gauge',
                               description='total time to process timed events')
            test_gauge.set(500)

            gauge = [g for g in Gauge.find_all() if g.title == 'Test gauge'][0]
            self.assertGreaterEqual(gauge.value, 500)

            test_timer = Timer(group='test', name='timer', title='Test timer',
                               description='total time to process timed events')
            recv_started = test_timer.start_timer()
            time.sleep(1)
            test_timer.stop_timer(recv_started)

            timer = [t for t in Timer.find_all() if t.title == 'Test timer'][0]
            self.assertGreaterEqual(timer.count, 1)
            self.assertGreaterEqual(timer.total_time, 999)

    def test_prometheus(self):
        response = self.client.get('/management/metrics')
        self.assertEqual(response.status_code, 200)

        data = response.data.decode('utf-8')
        self.assertRegex(data, r'alerta_alerts_total \d+')
        self.assertRegex(data, r'alerta_uptime_msecs \d+')
