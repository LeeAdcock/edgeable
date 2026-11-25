import collections
import datetime
import decimal
import gzip
import os
import pickle
import stat
import tempfile
import unittest
import uuid

from edgeable import GraphDatabase, GraphNode, GraphEdge


class _Exploit:
    """Pickles into a call of os.mkdir(path) when loaded with pickle.load."""

    def __init__(self, path):
        self.path = path

    def __reduce__(self):
        return (os.mkdir, (self.path,))


class _Custom:
    pass


def _write_legacy_file(db, filename):
    """Write a file the way releases before the format change did: the graph
    dict pickled as is, dragging the GraphDatabase along with every node."""
    with gzip.open(filename, "wb") as f:
        pickle.dump(db._graph, f, protocol=4)


class _TempDirTestCase(unittest.TestCase):
    def setUp(self):
        self._tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tempdir.cleanup)
        self.dir = self._tempdir.name
        self.filename = os.path.join(self.dir, "graph.db")


class TestRestrictedLoad(_TempDirTestCase):
    def test_malicious_top_level_pickle_is_rejected(self):
        marker = os.path.join(self.dir, "pwned")
        with gzip.open(self.filename, "wb") as f:
            pickle.dump(_Exploit(marker), f, protocol=4)

        with self.assertRaises(pickle.UnpicklingError):
            GraphDatabase(filename=self.filename)
        self.assertFalse(os.path.exists(marker))

    def test_malicious_property_is_rejected_and_database_unchanged(self):
        marker = os.path.join(self.dir, "pwned")
        other = GraphDatabase(filename=os.path.join(self.dir, "other.db"))
        other.put_node("A")._properties["payload"] = _Exploit(marker)
        _write_legacy_file(other, self.filename)

        db = GraphDatabase(filename=os.path.join(self.dir, "missing.db"))
        db.put_node("keep")
        db.set_property("k", "v")
        db._filename = self.filename

        with self.assertRaises(pickle.UnpicklingError) as context:
            db.reload()
        self.assertIn("mkdir", str(context.exception))
        self.assertFalse(os.path.exists(marker))
        self.assertTrue(db.has_node("keep"))
        self.assertFalse(db.has_node("A"))
        self.assertEqual(db.get_properties(), {"k": "v"})

    def test_unknown_class_is_rejected(self):
        with gzip.open(self.filename, "wb") as f:
            pickle.dump({"A": _Custom()}, f, protocol=4)

        with self.assertRaises(pickle.UnpicklingError):
            GraphDatabase(filename=self.filename)

    def test_non_graph_content_is_rejected(self):
        for content in ["text", {"A": "not a node"}, ("edgeable", 2, [], {})]:
            with gzip.open(self.filename, "wb") as f:
                pickle.dump(content, f, protocol=4)
            with self.assertRaises(pickle.UnpicklingError):
                GraphDatabase(filename=self.filename)

    def test_database_class_in_file_is_never_constructed(self):
        # a file must not be able to make the loader open another file
        target = os.path.join(self.dir, "target.db")
        with gzip.open(target, "wb") as f:
            pickle.dump(_Custom(), f, protocol=4)

        class Reference:
            def __reduce__(self):
                return (GraphDatabase, (target,))

        with gzip.open(self.filename, "wb") as f:
            pickle.dump({"A": Reference()}, f, protocol=4)

        # rejected because the content is not a graph, not because loading
        # target.db was attempted and failed on _Custom
        with self.assertRaises(pickle.UnpicklingError) as context:
            GraphDatabase(filename=self.filename)
        self.assertNotIn("_Custom", str(context.exception))

    def test_safe_property_types_round_trip(self):
        properties = {
            "none": None,
            "bool": True,
            "int": 2**80,
            "float": 1.5,
            "complex": complex(1, 2),
            "str": "text",
            "bytes": b"\x00\x01",
            "bytearray": bytearray(b"ab"),
            "list": [1, [2, 3]],
            "tuple": (1, "a"),
            "dict": {"nested": {"k": 1}},
            "set": {1, 2},
            "frozenset": frozenset(["a"]),
            "range": range(3),
            "datetime": datetime.datetime(
                2020, 1, 2, 3, 4, tzinfo=datetime.timezone.utc
            ),
            "date": datetime.date(2020, 1, 2),
            "time": datetime.time(1, 2, 3),
            "timedelta": datetime.timedelta(seconds=5),
            "decimal": decimal.Decimal("1.10"),
            "uuid": uuid.UUID(int=5),
            "ordered": collections.OrderedDict([("b", 1), ("a", 2)]),
            "deque": collections.deque([1, 2]),
            "counter": collections.Counter("aab"),
        }
        db = GraphDatabase(filename=self.filename)
        A = db.put_node("A", properties)
        B = db.put_node(7, {})
        A.attach(B, properties)
        db.set_properties(properties)
        db.save()

        loaded = GraphDatabase(filename=self.filename)
        self.assertEqual(loaded.get_node("A").get_properties(), properties)
        self.assertEqual(
            loaded.get_node("A").get_edge(loaded.get_node(7)).get_properties(),
            properties,
        )
        self.assertEqual(loaded.get_properties(), properties)

    def test_save_refuses_values_which_could_not_be_reloaded(self):
        db = GraphDatabase(filename=self.filename)
        db.put_node("A")
        db.save()

        for value in [_Custom(), len, lambda: 1, int]:
            db.get_node("A").set_property("bad", value)
            with self.assertRaises(pickle.PicklingError):
                db.save()

        # the previous file is intact and no temporary file is left behind
        self.assertEqual(os.listdir(self.dir), ["graph.db"])
        loaded = GraphDatabase(filename=self.filename)
        self.assertEqual(loaded.get_node("A").get_properties(), {})


class TestReloadBinding(_TempDirTestCase):
    def _build(self, filename):
        db = GraphDatabase(filename=filename)
        A = db.put_node("A", {"k": 1})
        B = db.put_node("B")
        C = db.put_node("C")
        A.attach(B, {"w": 2})
        B.attach(C)
        return db

    def _assert_bound_and_callbacks_fire(self, db):
        for node in db.get_nodes():
            self.assertIs(node._db, db)
            for edge in node.get_edges():
                self.assertIs(edge._db, db)
                self.assertIs(edge.get_source(), node)

        events = []
        db.on_create_edge(lambda edge: events.append(("create", str(edge))))
        db.on_delete_edge(lambda edge: events.append(("delete", str(edge))))
        db.on_delete_node(lambda node: events.append(("delete", node.get_id())))

        A, B, C = db.get_node("A"), db.get_node("B"), db.get_node("C")
        A.attach(C, directed=True)
        self.assertIn(("create", "A->C"), events)
        A.detach(B)
        self.assertIn(("delete", "A->B"), events)
        self.assertIn(("delete", "B->A"), events)
        C.delete()
        self.assertIn(("delete", "C"), events)
        self.assertFalse(db.has_node("C"))

    def test_callbacks_fire_after_reload(self):
        self._build(self.filename).save()

        db = GraphDatabase(filename=self.filename)
        self.assertEqual(db.get_node_count(), 3)
        self.assertEqual(db.get_edge_count(), 4)
        self._assert_bound_and_callbacks_fire(db)

    def test_cancelling_callback_applies_after_reload(self):
        self._build(self.filename).save()

        db = GraphDatabase(filename=self.filename)
        db.on_delete_node(lambda node: False)
        db.get_node("A").delete()
        self.assertTrue(db.has_node("A"))

    def test_explicit_reload_keeps_callbacks_and_rebinds(self):
        db = self._build(self.filename)
        db.save()
        created = []
        db.on_create_node(lambda node: created.append(node.get_id()))
        db.get_node("A").delete()

        db.reload()
        self.assertTrue(db.has_node("A"))
        db.put_node("D")
        self.assertEqual(created, ["D"])
        self._assert_bound_and_callbacks_fire(db)

    def test_database_and_lock_are_not_serialized(self):
        self._build(self.filename).save()

        with gzip.open(self.filename, "rb") as f:
            raw = f.read()
        self.assertNotIn(b"edgeable.database", raw)
        self.assertNotIn(b"_filename", raw)
        self.assertNotIn(b"_lock", raw)
        self.assertNotIn(b"_on_create_node", raw)

    def test_database_is_picklable_without_lock_or_callbacks(self):
        db = self._build(self.filename)
        db.on_create_node(lambda node: None)

        copy = pickle.loads(pickle.dumps(db))
        self.assertEqual(copy.get_node_count(), 3)
        self.assertIsNot(copy._lock, db._lock)
        self.assertEqual(copy._on_create_node, {})
        copy.put_node("D")

    def test_legacy_file_loads_with_working_callbacks(self):
        old = self._build(os.path.join(self.dir, "old.db"))
        old.set_property("ignored", True)
        _write_legacy_file(old, self.filename)
        with gzip.open(self.filename, "rb") as f:
            self.assertIn(b"GraphDatabase", f.read())

        db = GraphDatabase(filename=self.filename)
        self.assertEqual(sorted(n.get_id() for n in db.get_nodes()), ["A", "B", "C"])
        self.assertEqual(db.get_node("A").get_properties(), {"k": 1})
        self.assertEqual(
            db.get_node("A").get_edge(db.get_node("B")).get_properties(), {"w": 2}
        )
        self.assertEqual(db.get_properties(), {})
        self.assertIs(type(db.get_node("A")), GraphNode)
        self.assertIs(type(db.get_node("A").get_edges()[0]), GraphEdge)
        self._assert_bound_and_callbacks_fire(db)

    def test_legacy_file_is_upgraded_on_save(self):
        _write_legacy_file(self._build(os.path.join(self.dir, "old.db")), self.filename)

        db = GraphDatabase(filename=self.filename, properties={"p": 1})
        db.save()
        with gzip.open(self.filename, "rb") as f:
            self.assertNotIn(b"_filename", f.read())

        db = GraphDatabase(filename=self.filename)
        self.assertEqual(db.get_node_count(), 3)
        self.assertEqual(db.get_properties(), {"p": 1})

    def test_legacy_reload_keeps_current_properties(self):
        _write_legacy_file(self._build(os.path.join(self.dir, "old.db")), self.filename)
        db = GraphDatabase(filename=self.filename)
        db.set_property("p", 1)
        db.reload()
        self.assertEqual(db.get_properties(), {"p": 1})


class TestDatabasePropertiesPersistence(_TempDirTestCase):
    def test_properties_are_persisted(self):
        with GraphDatabase(filename=self.filename) as db:
            db.set_property("version", 3)
            db.put_node("A")

        db = GraphDatabase(filename=self.filename)
        self.assertEqual(db.get_properties(), {"version": 3})
        self.assertTrue(db.has_node("A"))

    def test_reload_restores_properties(self):
        db = GraphDatabase(filename=self.filename, properties={"a": 1})
        db.save()
        db.set_property("a", 2)
        db.set_property("b", 3)

        db.reload()
        self.assertEqual(db.get_properties(), {"a": 1})

    def test_constructor_properties_override_loaded(self):
        with GraphDatabase(filename=self.filename) as db:
            db.set_properties({"a": 1, "b": 2})

        db = GraphDatabase(filename=self.filename, properties={"b": 20, "c": 30})
        self.assertEqual(db.get_properties(), {"a": 1, "b": 20, "c": 30})

    def test_default_properties_are_not_shared(self):
        one = GraphDatabase(filename=os.path.join(self.dir, "one.db"))
        two = GraphDatabase(filename=os.path.join(self.dir, "two.db"))
        one.set_property("k", "v")
        self.assertEqual(two.get_properties(), {})

    def test_constructor_properties_are_copied(self):
        supplied = {"k": "v"}
        db = GraphDatabase(filename=self.filename, properties=supplied)
        db.set_property("other", 1)
        self.assertEqual(supplied, {"k": "v"})
        supplied["k"] = "changed"
        self.assertEqual(db.get_property("k"), "v")

    def test_constructor_properties_validated(self):
        with self.assertRaises(RuntimeError):
            GraphDatabase(filename=self.filename, properties=[("k", "v")])
        with self.assertRaises(RuntimeError):
            GraphDatabase(filename=self.filename, properties={1: "v"})


class TestSave(_TempDirTestCase):
    def test_relative_path_with_directory(self):
        os.mkdir(os.path.join(self.dir, "data"))
        previous = os.getcwd()
        os.chdir(self.dir)
        try:
            with GraphDatabase(filename="data/g.db") as db:
                db.put_node("A")
            self.assertEqual(os.listdir("data"), ["g.db"])
            self.assertTrue(GraphDatabase(filename="data/g.db").has_node("A"))

            with GraphDatabase(filename="bare.db") as db:
                db.put_node("A")
            self.assertTrue(os.path.exists("bare.db"))
        finally:
            os.chdir(previous)

    def test_absolute_path_leaves_no_temp_files(self):
        db = GraphDatabase(filename=self.filename)
        db.put_node("A")
        db.save()
        db.save()
        self.assertEqual(os.listdir(self.dir), ["graph.db"])

    def test_no_file_descriptor_leak(self):
        if not os.path.isdir("/proc/self/fd"):
            self.skipTest("requires /proc")
        db = GraphDatabase(filename=self.filename)
        db.put_node("A")
        db.save()
        before = len(os.listdir("/proc/self/fd"))
        for _ in range(20):
            db.save()
        self.assertEqual(len(os.listdir("/proc/self/fd")), before)

    def test_missing_directory_raises_and_leaves_nothing(self):
        db = GraphDatabase(filename=os.path.join(self.dir, "missing", "g.db"))
        with self.assertRaises(OSError):
            db.save()
        self.assertEqual(os.listdir(self.dir), [])

    def test_failed_save_keeps_existing_file_and_removes_temp_file(self):
        db = GraphDatabase(filename=self.filename)
        db.put_node("A")
        db.save()

        db.put_node("B").set_property("bad", _Custom())
        with self.assertRaises(Exception):
            db.save()

        self.assertEqual(os.listdir(self.dir), ["graph.db"])
        loaded = GraphDatabase(filename=self.filename)
        self.assertTrue(loaded.has_node("A"))
        self.assertFalse(loaded.has_node("B"))

    @unittest.skipIf(os.name == "nt", "POSIX permission bits")
    def test_existing_permissions_are_preserved(self):
        db = GraphDatabase(filename=self.filename)
        db.save()
        os.chmod(self.filename, 0o640)

        db.put_node("A")
        db.save()
        self.assertEqual(stat.S_IMODE(os.stat(self.filename).st_mode), 0o640)
        self.assertTrue(GraphDatabase(filename=self.filename).has_node("A"))


if __name__ == "__main__":
    unittest.main()
