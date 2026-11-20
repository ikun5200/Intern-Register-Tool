"""`ledger.save_txt` 的契约测试 —— 两个 TXT 的路径、行格式、成功过滤。

背景（2026-11-20）：注册结果除了 JSON 台账，还要给人两个 TXT：
  · `accounts-<时间戳>.txt`  email----password----username----sso_uid----api_key
  · `keys-<时间戳>.txt`      只有 api_key

这两个文件是**人直接拿去用**的，所以格式和"只写成功账号"必须钉住；
JSON 台账仍是程序内部读源，`save_txt` 不改变它。
"""

from pathlib import Path

import src.ledger as ledger


def _rec(**over):
    base = {
        "email": "a@example.com",
        "password": "pw-a",
        "username": "user-a",
        "sso_uid": "1001",
        "api_key": "sk-aaa",
        "status": "success",
    }
    base.update(over)
    return base


def _snap(tmp_path: Path, name: str = "results-20261120-230128.json") -> Path:
    p = tmp_path / "runs" / "2026-11-20" / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("[]", encoding="utf-8")
    return p


def test_save_txt_writes_successful_accounts_and_keys(tmp_path, monkeypatch):
    monkeypatch.setattr(ledger, "LEDGER_DIR", tmp_path)
    snap = _snap(tmp_path)

    batch = [
        _rec(),
        _rec(email="b@example.com", username="user-b", sso_uid="1002", api_key=""),
        _rec(
            email="c@example.com",
            password="pw-c",
            username="user-c",
            sso_uid="1003",
            api_key="sk-ccc",
        ),
    ]

    acc, keys, latest_acc, latest_keys, n = ledger.save_txt(snap, batch)

    assert n == 2
    assert acc == snap.with_name("accounts-20261120-230128.txt")
    assert keys == snap.with_name("keys-20261120-230128.txt")
    assert acc.read_text(encoding="utf-8").splitlines() == [
        "a@example.com----pw-a----user-a----1001----sk-aaa",
        "c@example.com----pw-c----user-c----1003----sk-ccc",
    ]
    assert keys.read_text(encoding="utf-8").splitlines() == ["sk-aaa", "sk-ccc"]
    assert latest_acc.read_text(encoding="utf-8") == acc.read_text(encoding="utf-8")
    assert latest_keys.read_text(encoding="utf-8") == keys.read_text(encoding="utf-8")


def test_save_txt_with_no_successes_writes_empty_files(tmp_path, monkeypatch):
    """没有成功账号时也要**覆盖** latest，不能留着上一批的旧内容。"""
    monkeypatch.setattr(ledger, "LEDGER_DIR", tmp_path)
    (tmp_path / "latest_accounts.txt").write_text("old\n", encoding="utf-8")
    (tmp_path / "latest_keys.txt").write_text("old-key\n", encoding="utf-8")
    snap = _snap(tmp_path)

    acc, keys, latest_acc, latest_keys, n = ledger.save_txt(
        snap, [_rec(api_key=""), _rec(email="b@example.com", api_key="  ")]
    )

    assert n == 0
    assert acc.read_text(encoding="utf-8") == ""
    assert keys.read_text(encoding="utf-8") == ""
    assert latest_acc.read_text(encoding="utf-8") == ""
    assert latest_keys.read_text(encoding="utf-8") == ""


def test_save_txt_flattens_newlines_in_fields(tmp_path, monkeypatch):
    """一行一个账号 —— 字段里的换行必须压成空格，否则行会被拆坏。"""
    monkeypatch.setattr(ledger, "LEDGER_DIR", tmp_path)
    snap = _snap(tmp_path)

    ledger.save_txt(snap, [_rec(password="pw\nwith\r\nnewlines")])

    line = (snap.with_name("accounts-20261120-230128.txt")).read_text(
        encoding="utf-8"
    )
    assert line.count("\n") == 1
    assert "pw with  newlines" in line


def test_save_txt_uses_snapshot_timestamp_not_current_time(tmp_path, monkeypatch):
    monkeypatch.setattr(ledger, "LEDGER_DIR", tmp_path)
    snap = _snap(tmp_path, "results-20260101-010203.json")

    acc, keys, *_ = ledger.save_txt(snap, [_rec()])

    assert acc.name == "accounts-20260101-010203.txt"
    assert keys.name == "keys-20260101-010203.txt"
