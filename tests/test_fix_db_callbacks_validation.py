import functools
import logging
import os
import subprocess
import sys
import tempfile
import unittest

from edgeable import GraphDatabase

REPOSITORY = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class _DatabaseTestCase(unittest.TestCase):
    def setUp(self):
        self._tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tempdir.cleanup)
        self.db = GraphDatabase(filename=os.path.join(self._tempdir.name, "graph.db"))

    def registrations(self):
        return [
            (self.db.on_create_node, self.db._on_create_node),
            (self.db.on_delete_node, self.db._on_delete_node),
            (self.db.on_create_edge, self.db._on_create_edge),
            (self.db.on_delete_edge, self.db._on_delete_edge),
        ]


class TestCallbackRegistration(_DatabaseTestCase):
    def test_remove_unknown_id_is_noop(self):
        for register, callbacks in self.registrations():
            self.assertEqual(register(None, id="never-registered"), "never-registered")
            self.assertEqual(callbacks, {})

    def test_remove_without_id_is_noop(self):
        for register, callbacks in self.registrations():
            self.assertIsNone(register(None))
            self.assertEqual(callbacks, {})

    def test_remove_twice(self):
        for register, callbacks in self.registrations():
            id = register(lambda item: None)
            register(None, id)
            register(None, id)
            self.assertEqual(callbacks, {})

    def test_graph_usable_after_bogus_removal(self):
        for register, _ in self.registrations():
            register(None, id="never-registered")

        A = self.db.put_node("A")
        B = self.db.put_node("B")
        self.assertTrue(A.attach(B))
        self.assertTrue(A.detach(B))
        A.delete()
        self.assertFalse(self.db.has_node("A"))

    def test_falsy_ids_are_kept(self):
        for register, callbacks in self.registrations():
            for id in (0, "", False):
                callbacks.clear()
                first, second = (lambda item: None), (lambda item: None)
                self.assertEqual(register(first, id), id)
                self.assertEqual(register(second, id), id)
                self.assertEqual(list(callbacks.values()), [second])
                register(None, id)
                self.assertEqual(callbacks, {})

    def test_generated_ids_are_unique(self):
        for register, callbacks in self.registrations():
            ids = {register(lambda item: None) for _ in range(5)}
            self.assertEqual(len(ids), 5)
            self.assertNotIn(None, ids)
            self.assertEqual(len(callbacks), 5)

    def test_callback_must_be_callable(self):
        for register, callbacks in self.registrations():
            for fn in ("not callable", 5, {}):
                with self.assertRaises(RuntimeError):
                    register(fn)
                with self.assertRaises(RuntimeError):
                    register(fn, "id")
            self.assertEqual(callbacks, {})

    def test_any_callable_is_accepted(self):
        class Callback:
            def __init__(self):
                self.calls = []

            def __call__(self, node):
                self.calls.append(node.get_id())

        callback = Callback()
        seen = []
        self.db.on_create_node(callback)
        self.db.on_create_node(functools.partial(lambda out, n: out.append(n), seen))
        self.db.put_node("A")
        self.assertEqual(callback.calls, ["A"])
        self.assertEqual(len(seen), 1)

    def test_all_create_node_callbacks_run_after_cancel(self):
        calls = []

        def cancel(node):
            calls.append("cancel")
            return False

        self.db.on_create_node(cancel)
        self.db.on_create_node(lambda node: calls.append("second"))
        self.db.on_create_node(lambda node: calls.append("third"))

        self.assertIsNone(self.db.put_node("A"))
        self.assertEqual(calls, ["cancel", "second", "third"])
        self.assertFalse(self.db.has_node("A"))

    def test_only_false_cancels(self):
        for value in (None, True, 1, "", [], 0):
            self.db.on_create_node(lambda node, value=value: value, "id")
            name = "node-%r" % (value,)
            self.assertIsNotNone(self.db.put_node(name))
            self.assertTrue(self.db.has_node(name))


class TestValidation(_DatabaseTestCase):
    def test_set_property_requires_string_key(self):
        for key in (5, None, 1.5, ("a",), b"a"):
            with self.assertRaises(RuntimeError):
                self.db.set_property(key, "x")
        self.assertEqual(self.db.get_properties(), {})

    def test_set_properties_requires_string_keys(self):
        with self.assertRaises(RuntimeError):
            self.db.set_properties({"ok": 1, 5: 2})
        self.assertEqual(self.db.get_properties(), {})

    def test_filters_accept_any_callable(self):
        class Matcher:
            def __call__(self, item):
                return True

            def method(self, item):
                return True

        A = self.db.put_node("A")
        B = self.db.put_node("B")
        A.attach(B)

        for fn in (Matcher(), Matcher().method, functools.partial(lambda a, b: a, 1)):
            self.assertEqual(len(self.db.get_nodes(fn)), 2)
            self.assertEqual(len(self.db.get_edges(fn)), 2)
            self.assertEqual(len(self.db.get_edges(node_filter_fn=fn)), 2)
        self.assertEqual(len(self.db.get_nodes(bool)), 2)

    def test_node_filter_is_applied(self):
        A = self.db.put_node("A")
        B = self.db.put_node("B")
        A.attach(B)
        edges = self.db.get_edges(node_filter_fn=lambda node: node.get_id() == "A")
        self.assertEqual([str(edge) for edge in edges], ["A->B"])

    def test_filters_must_be_callable(self):
        for fn in (None, "text", 5):
            with self.assertRaises(RuntimeError):
                self.db.get_nodes(fn)
            with self.assertRaises(RuntimeError):
                self.db.get_edges(fn)
            with self.assertRaises(RuntimeError):
                self.db.get_edges(node_filter_fn=fn)

    def test_put_node_requires_dict_properties(self):
        for properties in (None, [("k", "v")], "text", 5):
            with self.assertRaises(RuntimeError):
                self.db.put_node("A", properties)
            self.assertFalse(self.db.has_node("A"))

        self.db.put_node("A", {"k": "v"})
        for properties in (None, [("k", "v")], "text", 5):
            with self.assertRaises(RuntimeError):
                self.db.put_node("A", properties)
        self.assertEqual(self.db.get_node("A").get_properties(), {"k": "v"})

    def test_put_node_copies_properties(self):
        properties = {"k": "v"}
        A = self.db.put_node("A", properties)
        A.set_property("other", 1)
        self.assertEqual(properties, {"k": "v"})
        self.assertEqual(self.db.put_node("B").get_properties(), {})


class TestPackaging(unittest.TestCase):
    def test_import_does_not_configure_root_logger(self):
        code = (
            "import logging, edgeable, edgeable.database;"
            "root = logging.getLogger();"
            "print(len(root.handlers), root.level == logging.WARNING)"
        )
        environment = dict(os.environ, PYTHONPATH=REPOSITORY)
        output = subprocess.check_output(
            [sys.executable, "-c", code], env=environment, cwd=tempfile.gettempdir()
        )
        self.assertEqual(output.decode().split(), ["0", "True"])

    def test_library_logger_has_null_handler(self):
        handlers = logging.getLogger("edgeable").handlers
        self.assertTrue(any(isinstance(h, logging.NullHandler) for h in handlers))

    def test_pytest_is_not_a_runtime_dependency(self):
        with open(os.path.join(REPOSITORY, "setup.py")) as f:
            setup = f.read()
        self.assertNotIn("pytest", setup)


if __name__ == "__main__":
    unittest.main()
