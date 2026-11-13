import gzip
import json

from brawlify.fetch.history import History
from brawlify.fetch.schema import column_changes


def test_column_changes(tmp_path):
    local = tmp_path / "t.json"
    local.write_text(json.dumps({"metadata": {"types": {"A": "int", "B": "str", "C": "int"}}}))
    payload = {"metadata": {"types": {"A": "str", "C": "int", "D": "bool"}}}
    assert column_changes(local, payload) == "+D -B ~A int->str"


def test_history_archives_then_indexes(tmp_path):
    history = History(tmp_path, "run1")
    assert history.needs_archive("csv/a.json", changed=False)
    history.archive("csv/a.json", b"data")

    index = json.loads((tmp_path / "index.json").read_text())
    assert index["runs"] == [{"run": "run1", "generatedAt": [], "files": ["csv/a.json"]}]
    assert gzip.decompress((tmp_path / "run1" / "csv/a.json.gz").read_bytes()) == b"data"
    assert not History(tmp_path, "run2").needs_archive("csv/a.json", changed=False)
