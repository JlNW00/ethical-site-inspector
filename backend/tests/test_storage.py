"""Tests for app.providers.storage – LocalStorageProvider."""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from app.providers.storage import LocalStorageProvider


class TestLocalStorageProviderSaveText:
    def test_save_text_creates_file(self, tmp_path):
        provider = LocalStorageProvider(root=tmp_path)
        result = provider.save_text("reports/test.txt", "hello world")
        file_path = tmp_path / "reports" / "test.txt"
        assert file_path.exists()
        assert file_path.read_text(encoding="utf-8") == "hello world"

    def test_save_text_returns_correct_relative_key(self, tmp_path):
        provider = LocalStorageProvider(root=tmp_path)
        result = provider.save_text("reports/test.txt", "content")
        assert result.relative_key == "reports/test.txt"

    def test_save_text_returns_absolute_path(self, tmp_path):
        provider = LocalStorageProvider(root=tmp_path)
        result = provider.save_text("reports/test.txt", "content")
        assert result.absolute_path is not None
        assert Path(result.absolute_path).exists()

    def test_save_text_returns_public_url(self, tmp_path):
        provider = LocalStorageProvider(root=tmp_path)
        result = provider.save_text("reports/test.html", "<h1>Report</h1>")
        assert result.public_url == "/artifacts/reports/test.html"

    def test_save_text_creates_nested_directories(self, tmp_path):
        provider = LocalStorageProvider(root=tmp_path)
        provider.save_text("a/b/c/deep.txt", "deep content")
        file_path = tmp_path / "a" / "b" / "c" / "deep.txt"
        assert file_path.exists()
        assert file_path.read_text(encoding="utf-8") == "deep content"


class TestLocalStorageProviderSaveBytes:
    def test_save_bytes_creates_file(self, tmp_path):
        provider = LocalStorageProvider(root=tmp_path)
        content = b"\x89PNG\r\n\x1a\n"
        result = provider.save_bytes("screenshots/shot.png", content, "image/png")
        file_path = tmp_path / "screenshots" / "shot.png"
        assert file_path.exists()
        assert file_path.read_bytes() == content

    def test_save_bytes_returns_storage_object(self, tmp_path):
        provider = LocalStorageProvider(root=tmp_path)
        result = provider.save_bytes("data/file.bin", b"\x00\x01", "application/octet-stream")
        assert result.relative_key == "data/file.bin"
        assert result.public_url == "/artifacts/data/file.bin"
        assert result.absolute_path is not None

    def test_save_bytes_normalises_backslash_keys(self, tmp_path):
        provider = LocalStorageProvider(root=tmp_path)
        result = provider.save_bytes("screenshots\\img.png", b"data", "image/png")
        assert "\\" not in result.relative_key
        assert "\\" not in result.public_url
