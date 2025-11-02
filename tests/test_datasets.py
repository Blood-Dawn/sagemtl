from __future__ import annotations

import json

from sagemtl.datasets import registry as registry_module
from sagemtl.datasets.registry import get_dataset_registry


def test_dataset_add_and_export(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    monkeypatch.setenv("SAGEMTL_DATA_DIR", str(data_dir))
    registry_module._registry_singleton = None  # type: ignore[attr-defined]
    registry = get_dataset_registry()
    source = tmp_path / "sample.jsonl"
    source.write_text(json.dumps({"id": "1", "src": "hello"}) + "\n", encoding="utf-8")
    record = registry.add("sample", source)
    assert record.name == "sample"
    assert record.path.exists()
    out_csv = tmp_path / "export.csv"
    registry.export("sample", "csv", out_csv)
    content = out_csv.read_text(encoding="utf-8")
    assert "id,src" in content
