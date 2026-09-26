"""Check the public library workflow without touching a user's images."""

import io
import shutil
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from PIL import Image

import personal_library as library


@contextmanager
def workspace_temp():
    workspace = Path(__file__).resolve().parents[1]
    directory = workspace / f"test_data_{uuid4().hex}"
    directory.mkdir()
    try:
        yield directory
    finally:
        if not directory.resolve().is_relative_to(workspace.resolve()):
            raise RuntimeError("Refusing to remove a directory outside this repository")
        shutil.rmtree(directory)


class LibraryWorkflowTests(unittest.TestCase):
    def test_import_deduplicates_and_keeps_three_categories(self):
        with workspace_temp() as root:
            with patch.multiple(
                library,
                DATA_DIR=root,
                IMAGE_DIR=root / "images",
                THUMB_DIR=root / "thumbnails",
                RUN_DIR=root / "runs",
                DB_PATH=root / "library.sqlite3",
            ):
                buffer = io.BytesIO()
                Image.new("RGB", (100, 80), "#A4C5DA").save(buffer, "PNG")
                first, created = library.add_reference(
                    buffer.getvalue(), "sample.png", figure_type="framework"
                )
                second, duplicate = library.add_reference(
                    buffer.getvalue(), "sample.png", figure_type="framework"
                )
                self.assertTrue(created)
                self.assertFalse(duplicate)
                self.assertEqual(first, second)
                self.assertEqual(len(library.list_references()), 1)
                self.assertEqual(
                    set(library.CATEGORY_LABELS),
                    {"framework", "mechanism", "experiment"},
                )
                self.assertTrue(Path(library.list_references()[0]["image_path"]).is_file())
                library.set_category(first, "mechanism")
                self.assertEqual(len(library.list_references("mechanism")), 1)
                library.delete_reference(first)
                self.assertEqual(library.list_references(), [])


if __name__ == "__main__":
    unittest.main()
