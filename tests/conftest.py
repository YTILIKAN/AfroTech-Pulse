import pytest

import archive.search as search_module


@pytest.fixture(autouse=True)
def index_archive_isole(monkeypatch, tmp_path):
    """Isole l'index Whoosh de chaque test.

    Depuis que publish.py réindexe après une publication réussie, n'importe quel test qui
    publie (test_publish.py, test_workflows.py...) écrirait ses données factices dans le
    vrai archive/index_whoosh du repo sans cette redirection.
    """
    monkeypatch.setattr(search_module, "INDEX_DIR", str(tmp_path / "index_whoosh"))
