from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from scripts.lint_todo_completion import lint_todo_directory


def _write_todo(path: Path, roadmap_item: str) -> None:
    path.write_text(
        f"""目的: サンプルタスク
関連ブランチ: docs/rm999-sample
関連Issue: 未作成
roadmap_item: {roadmap_item}
---
- [ ] ブランチ作成と初期コミット
- [ ] PR 作成
""",
        encoding="utf-8",
    )


def test_lint_passes_with_valid_roadmap_item(tmp_path):
    docs_dir = tmp_path / "docs"
    todo_dir = docs_dir / "todo"
    todo_dir.mkdir(parents=True)
    roadmap_path = docs_dir / "roadmap" / "roadmap.md"
    roadmap_path.parent.mkdir(parents=True)

    todo_path = todo_dir / "20251122-rm123-valid.md"
    _write_todo(todo_path, "RM-123 テストテーマ")

    roadmap_path.write_text(
        """# 開発ロードマップ

<a id="rm-123"></a>
### RM-123 テストテーマ
- 状況: 未着手
""",
        encoding="utf-8",
    )

    result = lint_todo_directory(todo_dir, roadmap_path)
    assert result == {}


def test_lint_detects_missing_roadmap_entry(tmp_path):
    docs_dir = tmp_path / "docs"
    todo_dir = docs_dir / "todo"
    todo_dir.mkdir(parents=True)
    roadmap_path = docs_dir / "roadmap" / "roadmap.md"
    roadmap_path.parent.mkdir(parents=True)

    todo_path = todo_dir / "20251122-rm321-missing.md"
    _write_todo(todo_path, "RM-321 不足テーマ")

    roadmap_path.write_text("# 開発ロードマップ\n", encoding="utf-8")

    result = lint_todo_directory(todo_dir, roadmap_path)
    assert todo_path in result
    assert any("RM-321" in issue for issue in result[todo_path])


def test_lint_detects_invalid_format(tmp_path):
    docs_dir = tmp_path / "docs"
    todo_dir = docs_dir / "todo"
    todo_dir.mkdir(parents=True)
    roadmap_path = docs_dir / "roadmap" / "roadmap.md"
    roadmap_path.parent.mkdir(parents=True)
    roadmap_path.write_text("# 開発ロードマップ\n", encoding="utf-8")

    todo_path = todo_dir / "20251122-rm999-invalid.md"
    _write_todo(todo_path, "invalid")

    result = lint_todo_directory(todo_dir, roadmap_path)
    assert todo_path in result
    assert any("RM-xxx" in issue for issue in result[todo_path])


def test_lint_detects_invalid_branch(tmp_path):
    docs_dir = tmp_path / "docs"
    todo_dir = docs_dir / "todo"
    todo_dir.mkdir(parents=True)
    roadmap_path = docs_dir / "roadmap" / "roadmap.md"
    roadmap_path.parent.mkdir(parents=True)
    roadmap_path.write_text(
        """# 開発ロードマップ

<a id="rm-456"></a>
""",
        encoding="utf-8",
    )

    todo_path = todo_dir / "20251122-rm456-branch.md"
    todo_path.write_text(
        """---
目的: ブランチ検証
関連ブランチ: feature/missing-rm
関連Issue: 未作成
roadmap_item: RM-456 ブランチ検証
---
- [ ] ブランチ作成と初期コミット
- [ ] PR 作成
""",
        encoding="utf-8",
    )

    result = lint_todo_directory(todo_dir, roadmap_path)
    assert todo_path in result
    assert any("関連ブランチ" in issue for issue in result[todo_path])
