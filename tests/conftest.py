"""Every test runs against a throwaway workspace, so no test can read or write your real files."""

import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: renders real PDFs; `jobhunt doctor` skips these, plain pytest runs them")


@pytest.fixture(autouse=True)
def workspace(tmp_path, monkeypatch):
    ws = tmp_path / "workspace"
    ws.mkdir()
    shutil.copy(ROOT / "templates" / "profile.yaml", ws / "profile.yaml")
    monkeypatch.setenv("JOBHUNT_WORKSPACE", str(ws))
    from jobhunt import config
    config._CACHE.clear()
    yield ws
    config._CACHE.clear()
