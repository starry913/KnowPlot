"""Local, compact reference library for KnowPlot."""

from __future__ import annotations

import hashlib
import io
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "personal_data"
IMAGE_DIR = DATA_DIR / "images"
THUMB_DIR = DATA_DIR / "thumbnails"
RUN_DIR = DATA_DIR / "runs"
DB_PATH = DATA_DIR / "library.sqlite3"
CATEGORY_LABELS = {
    "framework": "方法框架图",
    "mechanism": "关键机制示意图",
    "experiment": "实验数据图",
}


@contextmanager
def _database():
    db = sqlite3.connect(DB_PATH)
    try:
        yield db
        db.commit()
    finally:
        db.close()


def initialize() -> None:
    for directory in (DATA_DIR, IMAGE_DIR, THUMB_DIR, RUN_DIR):
        directory.mkdir(parents=True, exist_ok=True)
    with _database() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS reference_items (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT '',
            figure_type TEXT NOT NULL DEFAULT 'diagram',
            tags TEXT NOT NULL DEFAULT '',
            notes TEXT NOT NULL DEFAULT '',
            analysis TEXT NOT NULL DEFAULT '',
            image_path TEXT NOT NULL,
            thumb_path TEXT NOT NULL,
            created_at TEXT NOT NULL
        )""")
        db.execute("UPDATE reference_items SET figure_type='framework' WHERE figure_type='diagram'")
        db.execute("UPDATE reference_items SET figure_type='experiment' WHERE figure_type='plot'")


def add_reference(
    raw: bytes, filename: str, *, title: str = "", source: str = "",
    figure_type: str = "framework", tags: str = "", notes: str = "",
    keep_original: bool = False,
) -> tuple[str, bool]:
    """Import an image. Returns (id, created); duplicate content is stored once."""
    if figure_type not in CATEGORY_LABELS:
        raise ValueError("请选择有效的图片类别。")
    initialize()
    if not raw or len(raw) > 40 * 1024 * 1024:
        raise ValueError("图片为空或超过 40 MB。")
    digest = hashlib.sha256(raw).hexdigest()
    with _database() as db:
        if db.execute("SELECT 1 FROM reference_items WHERE id=?", (digest,)).fetchone():
            return digest, False
    try:
        with Image.open(io.BytesIO(raw)) as opened:
            if opened.width * opened.height > 70_000_000:
                raise ValueError("图片像素过大。")
            image = ImageOps.exif_transpose(opened).convert("RGB")
    except (OSError, SyntaxError) as exc:
        raise ValueError("无法读取图片，请使用 PNG、JPEG 或 WEBP。") from exc
    image.thumbnail((2600, 2600), Image.Resampling.LANCZOS)
    if keep_original:
        suffix = Path(filename).suffix.lower()
        if suffix not in {".png", ".jpg", ".jpeg", ".webp"}:
            suffix = ".png"
            image_path = IMAGE_DIR / f"{digest}{suffix}"
            image.save(image_path, "PNG")
        else:
            image_path = IMAGE_DIR / f"{digest}{suffix}"
            image_path.write_bytes(raw)
    else:
        image_path = IMAGE_DIR / f"{digest}.webp"
        image.save(image_path, "WEBP", quality=92, method=6)
    thumb = image.copy()
    thumb.thumbnail((750, 750), Image.Resampling.LANCZOS)
    thumb_path = THUMB_DIR / f"{digest}.webp"
    thumb.save(thumb_path, "WEBP", quality=80, method=6)
    with _database() as db:
        db.execute(
            """INSERT INTO reference_items VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (digest, title.strip() or Path(filename).stem, source.strip(),
             figure_type, tags.strip(), notes.strip(), "", str(image_path),
             str(thumb_path), datetime.now(timezone.utc).isoformat()),
        )
    return digest, True


def list_references(figure_type: str | None = None) -> list[dict]:
    initialize()
    query = "SELECT * FROM reference_items"
    params: tuple = ()
    if figure_type:
        query += " WHERE figure_type=?"
        params = (figure_type,)
    query += " ORDER BY created_at DESC"
    with _database() as db:
        db.row_factory = sqlite3.Row
        return [dict(row) for row in db.execute(query, params)]


def update_reference(ref_id: str, *, title: str, source: str, tags: str,
                     notes: str, analysis: str) -> None:
    initialize()
    with _database() as db:
        db.execute("""UPDATE reference_items SET title=?, source=?, tags=?, notes=?,
                   analysis=? WHERE id=?""",
                   (title, source, tags, notes, analysis, ref_id))


def set_category(ref_id: str, category: str) -> None:
    if category not in CATEGORY_LABELS:
        raise ValueError("请选择有效的图片类别。")
    initialize()
    with _database() as db:
        db.execute("UPDATE reference_items SET figure_type=? WHERE id=?",
                   (category, ref_id))


def delete_reference(ref_id: str) -> None:
    initialize()
    with _database() as db:
        row = db.execute("SELECT image_path, thumb_path FROM reference_items WHERE id=?",
                         (ref_id,)).fetchone()
        if not row:
            return
        db.execute("DELETE FROM reference_items WHERE id=?", (ref_id,))
    for path in row:
        file = Path(path)
        if file.resolve().is_relative_to(DATA_DIR.resolve()):
            file.unlink(missing_ok=True)


def disk_usage() -> dict[str, int]:
    initialize()
    return {
        "library": sum(p.stat().st_size for folder in (IMAGE_DIR, THUMB_DIR)
                       for p in folder.iterdir() if p.is_file()) + DB_PATH.stat().st_size,
        "runs": sum(p.stat().st_size for p in RUN_DIR.rglob("*") if p.is_file()),
    }


def export_manifest() -> bytes:
    """Metadata backup; images remain local and are not embedded in JSON."""
    rows = list_references()
    for row in rows:
        row["image_path"] = Path(row["image_path"]).name
        row["thumb_path"] = Path(row["thumb_path"]).name
    return json.dumps(rows, ensure_ascii=False, indent=2).encode("utf-8")
