import unittest, threading, queue, time

from edgeable import GraphModifyLock, GraphReadLock


class TestThreadLock(unittest.TestCase):
    def setUp(self):

        self.q = queue.Queue()
        self.readers = 0
        self.writers = 0

        def do_writing():
            self.writers = self.writers + 1
            self.assertEqual(self.readers, 0)
            self.assertGreaterEqual(self.writers, 1)
            time.sleep(0.25)
            self.writers = self.writers - 1

        def do_reading():
            self.readers = self.readers + 1
            self.assertEqual(self.writers, 0)
            self.assertGreaterEqual(self.readers, 1)
            time.sleep(0.25)
            self.readers = self.readers - 1

        def do_fail():
            raise Exception()

        self.do_safe_writing = GraphModifyLock(do_writing)
        self.do_safe_reading = GraphReadLock(do_reading)

        self.do_safe_writing_fail = GraphModifyLock(do_fail)
        self.do_safe_reading_fail = GraphReadLock(do_fail)

        def worker():
            while True:
                try:
                    task = self.q.get()
                    task[0]()
                except Exception as e:
                    pass
                finally:
                    self.q.task_done()

        for i in range(3):
            threading.Thread(target=worker, daemon=True).start()

    def test_write_than_read(self):

        self.q.put((self.do_safe_writing, ()))
        self.q.put((self.do_safe_writing, ()))
        self.q.put((self.do_safe_reading, ()))
        self.q.put((self.do_safe_reading, ()))
        self.q.join()

    def test_failed_write_than_read(self):

        self.q.put((self.do_safe_writing, ()))
        self.q.put((self.do_safe_writing_fail, ()))
        self.q.put((self.do_safe_reading, ()))
        self.q.put((self.do_safe_reading, ()))
        self.q.join()

    def test_read_than_writes(self):

        self.q.put((self.do_safe_reading, ()))
        self.q.put((self.do_safe_reading, ()))
        self.q.put((self.do_safe_writing, ()))
        self.q.put((self.do_safe_writing, ()))
        self.q.join()

    def test_failed_read_than_writes(self):

        self.q.put((self.do_safe_reading, ()))
        self.q.put((self.do_safe_reading_fail, ()))
        self.q.put((self.do_safe_writing, ()))
        self.q.put((self.do_safe_writing, ()))
        self.q.join()

    def test_mix(self):

        self.q.put((self.do_safe_reading, ()))
        self.q.put((self.do_safe_writing, ()))
        self.q.put((self.do_safe_reading, ()))
        self.q.put((self.do_safe_writing, ()))
        self.q.put((self.do_safe_reading, ()))
        self.q.put((self.do_safe_writing, ()))
        self.q.join()
