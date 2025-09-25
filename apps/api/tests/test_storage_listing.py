"""Tests for storage listing helpers."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from app.services.storage import list_objects_tree


def test_list_objects_tree_builds_hierarchy() -> None:
    objects = [
        SimpleNamespace(object_name="Dream/Sky/chapter1.txt", size=10),
        SimpleNamespace(object_name="Dream/Sky/notes/readme.md", size=5),
    ]
    client = MagicMock()
    client.list_objects.return_value = objects

    tree = list_objects_tree(client, "books", "Dream/Sky/")

    assert tree["path"] == "Dream/Sky/"
    children = {child["path"]: child for child in tree["children"]}
    assert "Dream/Sky/chapter1.txt" in children
    assert children["Dream/Sky/chapter1.txt"]["type"] == "file"

    notes_folder = next(child for child in tree["children"] if child["path"].endswith("notes/"))
    assert notes_folder["type"] == "folder"
    assert notes_folder["children"][0]["path"].endswith("notes/readme.md")
