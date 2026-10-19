import pytest

import main


def test_persistent_database_requires_mounted_directory(tmp_path, monkeypatch):
    db_path = tmp_path / "memo.db"
    monkeypatch.setenv("MEMO_DB_PATH", str(db_path))
    monkeypatch.setenv("MEMO_DB_REQUIRE_PERSISTENT", "true")
    monkeypatch.setattr(main.os.path, "ismount", lambda path: False)

    with pytest.raises(RuntimeError, match="Required persistent database mount"):
        main.validate_db_storage()


def test_persistent_database_allows_initial_database_creation(tmp_path, monkeypatch):
    db_path = tmp_path / "memo.db"
    monkeypatch.setenv("MEMO_DB_PATH", str(db_path))
    monkeypatch.setenv("MEMO_DB_REQUIRE_PERSISTENT", "true")
    monkeypatch.setattr(main.os.path, "ismount", lambda path: True)

    main.validate_db_storage()


def test_startup_initializes_persistent_database_and_marker(tmp_path, monkeypatch):
    db_path = tmp_path / "memo.db"
    monkeypatch.setenv("MEMO_DB_PATH", str(db_path))
    monkeypatch.setenv("MEMO_DB_REQUIRE_PERSISTENT", "true")
    monkeypatch.setattr(main.os.path, "ismount", lambda path: True)

    main.startup()

    assert db_path.is_file()
    assert (tmp_path / "memo.db.initialized").is_file()
    with main.sqlite3.connect(db_path) as conn:
        assert conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='memo_item'"
        ).fetchone() is not None
        conn.execute(
            "INSERT INTO memo_item (user_id, type, text) VALUES (?, ?, ?)",
            ("user-1", "memo", "persistent text"),
        )

    main.startup()
    with main.sqlite3.connect(db_path) as conn:
        assert conn.execute(
            "SELECT text FROM memo_item WHERE user_id = ?",
            ("user-1",),
        ).fetchone() == ("persistent text",)

def test_persistent_database_refuses_missing_database_after_initialization(tmp_path, monkeypatch):
    db_path = tmp_path / "memo.db"
    monkeypatch.setenv("MEMO_DB_PATH", str(db_path))
    monkeypatch.setenv("MEMO_DB_REQUIRE_PERSISTENT", "true")
    monkeypatch.setattr(main.os.path, "ismount", lambda path: True)
    (tmp_path / "memo.db.initialized").touch()

    with pytest.raises(RuntimeError, match="Required database file is missing"):
        main.validate_db_storage()
