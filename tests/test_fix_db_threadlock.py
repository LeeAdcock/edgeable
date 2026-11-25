import os
import tempfile
import threading
import time
import unittest

from edgeable import GraphDatabase, GraphModifyLock, GraphReadLock

TIMEOUT = 10


def run_with_timeout(test, fn, timeout=TIMEOUT):
    """Run fn on a daemon thread, failing the test if it does not finish, and
    returning its result or re-raising its exception."""
    outcome = {}

    def target():
        try:
            outcome["value"] = fn()
        except BaseException as e:  # reported to the test thread
            outcome["error"] = e

    thread = threading.Thread(target=target, daemon=True)
    thread.start()
    thread.join(timeout)
    if thread.is_alive():
        test.fail("Deadlock: call did not complete within %s seconds." % timeout)
    if "error" in outcome:
        raise outcome["error"]
    return outcome.get("value")


class _DatabaseTestCase(unittest.TestCase):
    def setUp(self):
        self._tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tempdir.cleanup)
        self.filename = os.path.join(self._tempdir.name, "graph.db")
        self.db = GraphDatabase(filename=self.filename)


class TestReentrancy(_DatabaseTestCase):
    def test_callback_reads_graph(self):
        db = self.db
        seen = []

        def callback(node):
            seen.append(len(db.get_nodes()))
            seen.append(len(db.get_edges()))
            seen.append(db.get_node_count())
            seen.append(db.has_node(node.get_id()))
            db.save()

        db.on_create_node(callback)
        node = run_with_timeout(self, lambda: db.put_node("A"))
        self.assertIsNotNone(node)
        self.assertEqual(seen, [0, 0, 0, False])

    def test_edge_callback_reads_and_routes(self):
        db = self.db
        A, B, C = db.put_node("A"), db.put_node("B"), db.put_node("C")
        A.attach(B)
        routes = []
        db.on_create_edge(lambda edge: routes.append(A.find_route_to(B)))
        db.on_delete_edge(lambda edge: routes.append(A.find_neighbors()))

        run_with_timeout(self, lambda: B.attach(C))
        run_with_timeout(self, lambda: B.detach(C))
        self.assertEqual(routes[0], [A, B])
        self.assertEqual(len(routes), 4)

    def test_filter_modifies_graph(self):
        db = self.db
        db.put_node("A")
        db.put_node("B")

        nodes = run_with_timeout(
            self, lambda: db.get_nodes(lambda n: n.set_property("seen", 1) or True)
        )
        self.assertEqual(len(nodes), 2)
        self.assertEqual(db.get_node("A").get_property("seen"), 1)

    def test_filter_adds_nodes_while_iterating(self):
        db = self.db
        db.put_node("A")
        db.put_node("B")

        def filter_fn(node):
            db.put_node(node.get_id() + "2")
            return True

        nodes = run_with_timeout(self, lambda: db.get_nodes(filter_fn))
        self.assertEqual(sorted(n.get_id() for n in nodes), ["A", "B"])
        self.assertEqual(db.get_node_count(), 4)

    def test_callback_registers_callback(self):
        db = self.db
        db.on_create_node(lambda node: db.on_create_node(lambda n: None) and None)
        run_with_timeout(self, lambda: db.put_node("A"))
        self.assertTrue(db.has_node("A"))

    def test_reload_inside_callback(self):
        db = self.db
        db.put_node("A")
        db.save()
        db.on_delete_node(lambda node: db.reload())
        run_with_timeout(self, lambda: db.get_node("A").delete())


class TestExceptions(_DatabaseTestCase):
    def test_keyboard_interrupt_propagates_from_modify(self):
        def callback(node):
            raise KeyboardInterrupt()

        self.db.on_create_node(callback)
        with self.assertRaises(KeyboardInterrupt):
            self.db.put_node("Z")
        self.assertFalse(self.db.has_node("Z"))

    def test_base_exceptions_propagate_from_read(self):
        self.db.put_node("A")
        for exception in (KeyboardInterrupt, SystemExit, GeneratorExit, ValueError):

            def filter_fn(node, exception=exception):
                raise exception()

            with self.assertRaises(exception):
                self.db.get_nodes(filter_fn)

    def test_lock_released_after_exception(self):
        db = self.db

        def callback(node):
            raise KeyboardInterrupt()

        id = db.on_create_node(callback)
        with self.assertRaises(KeyboardInterrupt):
            db.put_node("Z")
        db.on_create_node(None, id)

        # another thread can still use the database
        node = run_with_timeout(self, lambda: db.put_node("A"))
        self.assertEqual(node.get_id(), "A")

    def test_plain_function_exceptions(self):
        def fail():
            raise SystemExit(3)

        for decorator in (GraphModifyLock, GraphReadLock):
            with self.assertRaises(SystemExit):
                decorator(fail)()
            self.assertEqual(decorator(lambda: 5)(), 5)


class TestWraps(unittest.TestCase):
    def test_metadata_is_preserved(self):
        self.assertEqual(GraphDatabase.put_node.__name__, "put_node")
        self.assertIn("Create a node", GraphDatabase.put_node.__doc__)
        self.assertEqual(GraphDatabase.get_nodes.__name__, "get_nodes")
        self.assertIn("Return all nodes", GraphDatabase.get_nodes.__doc__)

        @GraphReadLock
        def documented():
            """Docs."""

        self.assertEqual(documented.__name__, "documented")
        self.assertEqual(documented.__doc__, "Docs.")


class TestThreads(_DatabaseTestCase):
    def _run_threads(self, targets):
        errors = []

        def guard(target):
            def run():
                try:
                    target()
                except BaseException as e:
                    errors.append(e)

            return run

        threads = [threading.Thread(target=guard(t), daemon=True) for t in targets]
        for thread in threads:
            thread.start()
        deadline = time.time() + TIMEOUT
        for thread in threads:
            thread.join(max(0, deadline - time.time()))
        if any(thread.is_alive() for thread in threads):
            self.fail("Deadlock: threads did not complete.")
        if errors:
            raise errors[0]

    def test_writers_are_mutually_exclusive(self):
        db = self.db
        state = {"active": 0, "max": 0}
        guard = threading.Lock()

        def callback(node):
            with guard:
                state["active"] += 1
                state["max"] = max(state["max"], state["active"])
            time.sleep(0.05)
            with guard:
                state["active"] -= 1

        db.on_create_node(callback)
        self._run_threads([lambda i=i: db.put_node("n%d" % i) for i in range(4)])

        self.assertEqual(state["max"], 1)
        self.assertEqual(db.get_node_count(), 4)

    def test_readers_and_writers_are_mutually_exclusive(self):
        db = self.db
        db.put_node("A")
        state = {"writing": False, "overlap": False}

        def callback(node):
            state["writing"] = True
            time.sleep(0.05)
            state["writing"] = False

        def filter_fn(node):
            if state["writing"]:
                state["overlap"] = True
            time.sleep(0.01)
            return True

        db.on_create_node(callback)
        self._run_threads(
            [lambda i=i: db.put_node("n%d" % i) for i in range(3)]
            + [lambda: db.get_nodes(filter_fn) for _ in range(3)]
        )
        self.assertFalse(state["overlap"])

    def test_no_lost_updates(self):
        db = self.db
        db.set_property("count", 0)
        node = db.put_node("A")

        def work():
            for i in range(200):
                name = "%s-%d" % (threading.current_thread().name, i)
                db.set_properties({name: i})
                node.set_properties({name: i})

        self._run_threads([work for _ in range(4)])
        self.assertEqual(len(db.get_properties()), 801)
        self.assertEqual(len(node.get_properties()), 800)

    def test_counts_and_reload_during_concurrent_writes(self):
        db = self.db
        hub = db.put_node("hub")
        db.save()
        stop = threading.Event()

        def write():
            try:
                for i in range(300):
                    name = "%s-%d" % (threading.current_thread().name, i)
                    # A reload() between the calls replaces every node, which
                    # leaves the handles stale; attach then refuses them.
                    while True:
                        try:
                            db.put_node(name).attach(db.put_node("hub"))
                            break
                        except RuntimeError as e:
                            if "does not exist in graph" not in str(e):
                                raise
            finally:
                stop.set()

        def count():
            while not stop.is_set():
                db.get_edge_count()
                db.get_node_count()
                len(db.get_edges())

        def persist():
            while not stop.is_set():
                db.save()
                db.reload()
                time.sleep(0.001)

        self._run_threads([write, write, count, count, persist])
        self.assertTrue(db.has_node("hub"))
        self.assertEqual(db.get_edge_count() % 2, 0)

    def test_databases_do_not_block_each_other(self):
        other = GraphDatabase(filename=os.path.join(self._tempdir.name, "other.db"))
        entered = threading.Event()
        release = threading.Event()

        def callback(node):
            entered.set()
            release.wait(TIMEOUT)

        self.db.on_create_node(callback)
        blocked = threading.Thread(target=lambda: self.db.put_node("A"), daemon=True)
        blocked.start()
        try:
            self.assertTrue(entered.wait(TIMEOUT))
            # self.db is locked by the other thread, an unrelated database is not
            node = run_with_timeout(self, lambda: other.put_node("B"))
            self.assertEqual(node.get_id(), "B")
            self.assertIsNot(self.db._lock, other._lock)
        finally:
            release.set()
            blocked.join(TIMEOUT)
        self.assertFalse(blocked.is_alive())

    def test_node_and_edge_methods_use_database_lock(self):
        db = self.db
        A, B = db.put_node("A"), db.put_node("B")
        A.attach(B)
        edge = A.get_edge(B)
        done = []

        with db._lock:
            threads = [
                threading.Thread(
                    target=lambda: done.append(A.set_property("k", 1)), daemon=True
                ),
                threading.Thread(
                    target=lambda: done.append(edge.set_property("k", 1)), daemon=True
                ),
            ]
            for thread in threads:
                thread.start()
            time.sleep(0.2)
            self.assertEqual(done, [])
        for thread in threads:
            thread.join(TIMEOUT)
        self.assertEqual(len(done), 2)


if __name__ == "__main__":
    unittest.main()
