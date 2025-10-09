from __future__ import annotations

import datetime as dt
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from scripts.auto_complete_todo import process_todo, update_roadmap


def _sample_todo_content() -> str:
    return """---
目的: テストタスク
関連ブランチ: test/branch
関連Issue: 未作成
roadmap_item: RM-002 サンプルテーマ
---

- [ ] 作業 1
  - メモ: 作業詳細
- [ ] PR 作成
  - メモ: PR を作成したら番号と URL を記入する

## メモ
- テスト用データ
"""


def _sample_roadmap_content(todo_filename: str) -> str:
    return f"""# 開発ロードマップ（大項目）

## アクティブテーマ
- テーマごとに `RM-xxx` 番号を付与し、ToDo フロントマターの `roadmap_item` と一致させる。

<a id="rm-001"></a>
### RM-001 別テーマ（優先度: P2）
- ゴール: dummy
- 参照 ToDo: [docs/todo/archive/old.md](../todo/archive/old.md)
- 状況: 完了（2025-10-01 更新）

<a id="rm-002"></a>
### RM-002 サンプルテーマ（優先度: P1）
- ゴール: サンプルゴール
- 参照 ToDo: [docs/todo/{todo_filename}](../todo/{todo_filename})
- 状況: 4/5 件完了（2025-10-09 更新）
- 次のアクション: PR のマージ

## 完了テーマ

### PDF 自動生成対応
- ゴール: dummy
- 参照 ToDo: [docs/todo/archive/completed.md](../todo/archive/completed.md)
- 状況: 完了（2025-10-06 更新）
- 成果: 既存

"""


def test_process_todo_without_full_completion(tmp_path):
    docs_dir = tmp_path / "docs"
    todo_dir = docs_dir / "todo"
    todo_dir.mkdir(parents=True)
    archive_dir = todo_dir / "archive"
    roadmap_dir = docs_dir / "roadmap"
    roadmap_dir.mkdir(parents=True)

    todo_path = todo_dir / "20251009-sample.md"
    todo_path.write_text(_sample_todo_content(), encoding="utf-8")

    roadmap_path = roadmap_dir / "README.md"
    roadmap_path.write_text(_sample_roadmap_content(todo_path.name), encoding="utf-8")

    pr_number = 123
    pr_url = "https://github.com/org/repo/pull/123"
    today = dt.date.today().isoformat()

    result_path, fields, archived = process_todo(todo_path, archive_dir, pr_number, pr_url, dry_run=False)
    assert fields["roadmap_item"] == "RM-002 サンプルテーマ"
    assert not archived
    assert result_path == todo_path
    archived_content = result_path.read_text(encoding="utf-8")
    assert "- [ ] 作業 1" in archived_content
    assert "- [x] PR 作成" in archived_content
    assert f"PR #{pr_number} {pr_url}（{today} 完了）" in archived_content
    # 未完タスクが残るためロードマップ更新は行わない
    before_content = roadmap_path.read_text(encoding="utf-8")
    update_triggered = False
    if archived:
        update_triggered = update_roadmap(
            roadmap_path=roadmap_path,
            roadmap_item=fields["roadmap_item"],
            todo_filename=result_path.name,
            pr_number=pr_number,
            pr_url=pr_url,
            date_str=today,
            dry_run=False,
        )
    assert not update_triggered
    assert roadmap_path.read_text(encoding="utf-8") == before_content


def test_process_todo_with_full_completion(tmp_path):
    docs_dir = tmp_path / "docs"
    todo_dir = docs_dir / "todo"
    todo_dir.mkdir(parents=True)
    archive_dir = todo_dir / "archive"
    roadmap_dir = docs_dir / "roadmap"
    roadmap_dir.mkdir(parents=True)

    todo_path = todo_dir / "20251009-complete.md"
    todo_path.write_text(
        """---
目的: 完了テスト
関連ブランチ: test/complete
関連Issue: 未作成
roadmap_item: RM-002 サンプルテーマ
---

- [x] 作業 1
  - メモ: 作業詳細
- [ ] PR 作成
  - メモ: PR を作成したら番号と URL を記入する
""",
        encoding="utf-8",
    )

    roadmap_path = roadmap_dir / "README.md"
    roadmap_path.write_text(_sample_roadmap_content(todo_path.name), encoding="utf-8")

    pr_number = 999
    pr_url = "https://github.com/org/repo/pull/999"
    today = dt.date.today().isoformat()

    result_path, fields, archived = process_todo(todo_path, archive_dir, pr_number, pr_url, dry_run=False)
    assert archived
    assert result_path.parent == archive_dir
    archived_content = result_path.read_text(encoding="utf-8")
    assert "- [x] 作業 1" in archived_content
    assert "- [x] PR 作成" in archived_content

    updated = update_roadmap(
        roadmap_path=roadmap_path,
        roadmap_item=fields["roadmap_item"],
        todo_filename=result_path.name,
        pr_number=pr_number,
        pr_url=pr_url,
        date_str=today,
        dry_run=False,
    )
    assert updated
