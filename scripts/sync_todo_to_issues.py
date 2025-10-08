#!/usr/bin/env python3
import argparse
import os
import re
from typing import Dict, Iterable, List, Optional, Tuple

import requests

API = "https://api.github.com"

TASK_RE = re.compile(r"^- \[( |x|X)\] (.*?)(?:\s*\(#?(\d+)\)|\s+#(\d+))?\s*$")
RELATED_ISSUE_LINE_RE = re.compile(r"^(\s*関連Issue:\s*)(.*)\s*$")
FRONT_MATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
TODO_MARKER_RE = re.compile(r"<!--\s*todo-path:\s*(.*?)\s*-->")


def read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write_text(path: str, content: str):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def parse_tasks(md_path: str):
    tasks = []
    with open(md_path, "r", encoding="utf-8") as f:
        for line in f:
            m = TASK_RE.match(line)
            if not m:
                continue
            checked = (m.group(1).lower() == "x")
            title = m.group(2).strip()
            num = m.group(3) or m.group(4)
            issue_number = int(num) if num else None
            tasks.append({
                "title": title,
                "checked": checked,
                "issue_number": issue_number,
            })
    return tasks


def gh(method: str, url: str, token: str, **kwargs):
    headers = kwargs.pop("headers", {})
    headers.update({
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    })
    r = requests.request(method, url, headers=headers, **kwargs)
    if r.status_code >= 400:
        raise RuntimeError(f"GitHub API error {r.status_code}: {r.text}")
    return r.json() if r.text else {}


def ensure_label(owner: str, repo: str, token: str, label: str, desc: str) -> None:
    if not label:
        return
    try:
        gh("GET", f"{API}/repos/{owner}/{repo}/labels/{label}", token)
    except Exception:
        gh(
            "POST",
            f"{API}/repos/{owner}/{repo}/labels",
            token,
            json={"name": label, "color": "0e8a16", "description": desc},
        )


def list_issues_by_label(owner: str, repo: str, token: str, label: str):
    issues = []
    page = 1
    while True:
        params = {"state": "all", "per_page": 100, "page": page}
        if label:
            params["labels"] = label
        data = gh(
            "GET",
            f"{API}/repos/{owner}/{repo}/issues",
            token,
            params=params,
        )
        if not data:
            break
        for it in data:
            if "pull_request" in it:
                continue
            issues.append(it)
        if len(data) < 100:
            break
        page += 1
    return issues


def extract_front_matter_fields(content: str) -> Dict[str, str]:
    m = FRONT_MATTER_RE.match(content)
    fields: Dict[str, str] = {}
    if not m:
        return fields
    body = m.group(1)
    for line in body.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            fields[k.strip()] = v.strip()
    return fields


def extract_tasks_and_notes(content: str) -> Tuple[str, str]:
    lines = content.splitlines()
    tasks: List[str] = []
    notes: List[str] = []
    in_tasks = False
    notes_start = None
    for idx, line in enumerate(lines):
        if not in_tasks:
            if TASK_RE.match(line):
                in_tasks = True
                tasks.append(line)
        else:
            if line.startswith("## "):
                notes_start = idx
                break
            tasks.append(line)
    if notes_start is not None:
        notes = lines[notes_start:]
    elif in_tasks:
        notes = []
    else:
        notes = lines
    tasks_section = "\n".join(tasks).strip()
    notes_section = "\n".join(notes).strip()
    return tasks_section, notes_section


def extract_marker(body: Optional[str]) -> Optional[str]:
    if not body:
        return None
    m = TODO_MARKER_RE.search(body)
    return m.group(1).strip() if m else None


def ensure_issue_labels(owner: str, repo: str, token: str, issue, labels: Iterable[str]):
    desired = [lbl for lbl in labels if lbl]
    if not desired:
        return
    current = {lbl["name"] for lbl in issue.get("labels", [])}
    missing = [lbl for lbl in desired if lbl not in current]
    if missing:
        updated_labels = gh(
            "POST",
            f"{API}/repos/{owner}/{repo}/issues/{issue['number']}/labels",
            token,
            json={"labels": missing},
        )
        issue["labels"] = updated_labels


def build_issue_body(rel_path: str, fields: Dict[str, str], tasks: str, notes: str) -> str:
    lines: List[str] = []
    title = fields.get("目的") or rel_path
    lines.append(f"## {title}")
    lines.append("")
    lines.append(f"- パス: `{rel_path}`")
    for key in ("目的", "担当者", "関連ブランチ", "期限"):
        if key in fields:
            lines.append(f"- {key}: {fields[key]}")
    if "関連Issue" in fields:
        lines.append(f"- 関連Issue: {fields['関連Issue']}")
    lines.append("")
    lines.append("### タスク")
    lines.append(tasks or "_(タスク未設定)_")
    if notes:
        lines.append("")
        lines.append(notes)
    lines.append("")
    lines.append(f"<!-- todo-path: {rel_path} -->")
    return "\n".join(lines).strip() + "\n"


def upsert_related_issue_number_line(content: str, number: int) -> Tuple[str, bool]:
    changed = False
    lines = content.splitlines()
    for i, line in enumerate(lines):
        m = RELATED_ISSUE_LINE_RE.match(line)
        if m:
            prefix, rest = m.group(1), m.group(2)
            stripped = rest.strip()
            if stripped in {"未作成", ""} or not stripped.startswith("#"):
                lines[i] = f"{prefix}#{number}"
                changed = True
            break
    else:
        inset = f"関連Issue: #{number}"
        fm = FRONT_MATTER_RE.match(content)
        if fm:
            endpos = fm.end()
            content = content[:endpos] + inset + "\n" + content[endpos:]
        else:
            content = inset + "\n" + content
        return content, True

    updated = "\n".join(lines)
    if content.endswith("\n"):
        updated += "\n"
    return updated, changed


def normalize_repo_path(path: str) -> str:
    rel = os.path.relpath(path, start=".")
    return rel.replace(os.sep, "/")


def collect_todo_paths(todo_paths: List[str], todo_dir: Optional[str], template_name: str, include_template: bool) -> List[str]:
    paths: List[str] = []
    for p in todo_paths:
        if not p:
            continue
        norm = os.path.normpath(p)
        if os.path.basename(norm) == "README.md":
            continue
        if os.path.isfile(norm):
            paths.append(norm)

    if todo_dir:
        for root, _dirs, files in os.walk(todo_dir):
            for fname in files:
                if not fname.endswith(".md"):
                    continue
                if fname == "README.md":
                    continue
                if not include_template and fname == template_name:
                    continue
                paths.append(os.path.normpath(os.path.join(root, fname)))

    unique = []
    seen = set()
    for p in sorted(paths):
        basename = os.path.basename(p)
        if basename == "README.md":
            continue
        if not include_template and basename == template_name:
            continue
        if p not in seen:
            unique.append(p)
            seen.add(p)
    return unique


def find_issue_by_path(issues: List[dict], rel_path: str) -> Optional[dict]:
    for issue in issues:
        marker = extract_marker(issue.get("body"))
        if marker == rel_path:
            return issue
    return None


def is_legacy_issue(issue: dict, rel_path: str, keep_number: int) -> bool:
    if issue["number"] == keep_number:
        return False
    body = issue.get("body") or ""
    marker = extract_marker(body)
    if marker != rel_path:
        return False
    if "### タスク" in body:
        return False
    legacy_indicators = ("This issue is managed by", "Parent card for")
    return any(indicator in body for indicator in legacy_indicators)


def remove_label(owner: str, repo: str, token: str, issue_number: int, label: str):
    if not label:
        return
    try:
        gh(
            "DELETE",
            f"{API}/repos/{owner}/{repo}/issues/{issue_number}/labels/{label}",
            token,
        )
    except Exception:
        pass


def retire_legacy_issues(
    owner: str,
    repo: str,
    token: str,
    rel_path: str,
    keep_issue: dict,
    cached_issues: List[dict],
    global_label: str,
    parent_label: str,
):
    keep_number = keep_issue["number"]
    retired: List[int] = []
    for issue in list(cached_issues):
        if not is_legacy_issue(issue, rel_path, keep_number):
            continue
        number = issue["number"]
        comment = f"この ToDo は issue #{keep_number} に統合されたため、本 Issue はクローズします。"
        try:
            gh(
                "POST",
                f"{API}/repos/{owner}/{repo}/issues/{number}/comments",
                token,
                json={"body": comment},
            )
        except Exception:
            pass

        if issue.get("state") != "closed":
            try:
                gh(
                    "PATCH",
                    f"{API}/repos/{owner}/{repo}/issues/{number}",
                    token,
                    json={"state": "closed"},
                )
            except Exception:
                pass
        remove_label(owner, repo, token, number, global_label)
        remove_label(owner, repo, token, number, parent_label)
        retired.append(number)
        cached_issues[:] = [it for it in cached_issues if it["number"] != number]
    if retired:
        print(f"Retired legacy issues for {rel_path}: {', '.join(map(str, retired))}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--todo-path", action="append", default=[], help="ToDo Markdown ファイルのパス")
    ap.add_argument("--todo-dir", help="ToDo ファイルを探索するディレクトリ")
    ap.add_argument("--template-name", default="template.md", help="テンプレートファイル名")
    ap.add_argument("--include-template", action="store_true", help="テンプレートも同期対象に含める")
    ap.add_argument("--global-label", default="todo-sync", help="Issue に付与する共通ラベル")
    ap.add_argument("--parent-label", default="todo-card", help="識別用ラベル (任意)")
    args = ap.parse_args()

    repo = os.environ.get("GITHUB_REPOSITORY")
    token = os.environ.get("GITHUB_TOKEN")
    if not repo or not token:
        raise SystemExit("GITHUB_REPOSITORY and GITHUB_TOKEN are required")
    owner, repo_name = repo.split("/")

    todo_files = collect_todo_paths(args.todo_path, args.todo_dir, args.template_name, args.include_template)
    if not todo_files:
        print("No ToDo files found. Nothing to sync.")
        return

    ensure_label(owner, repo_name, token, args.global_label, "Synced from docs/todo files")
    ensure_label(owner, repo_name, token, args.parent_label, "ToDo tracking issue")

    cached_issues = list_issues_by_label(owner, repo_name, token, args.global_label)

    for path in todo_files:
        if not os.path.isfile(path):
            continue

        rel = normalize_repo_path(path)
        content = read_text(path)
        fields = extract_front_matter_fields(content)
        tasks_section, notes_section = extract_tasks_and_notes(content)
        issue_title = f"ToDo: {fields['目的']}" if fields.get("目的") else f"ToDo: {rel}"
        body = build_issue_body(rel, fields, tasks_section, notes_section)

        issue = find_issue_by_path(cached_issues, rel)
        created = False
        if not issue:
            labels = [lbl for lbl in [args.global_label, args.parent_label] if lbl]
            issue = gh(
                "POST",
                f"{API}/repos/{owner}/{repo_name}/issues",
                token,
                json={
                    "title": issue_title,
                    "labels": labels,
                    "body": body,
                },
            )
            cached_issues.append(issue)
            created = True

        ensure_issue_labels(owner, repo_name, token, issue, [args.global_label, args.parent_label])

        updates = {}
        desired_title = issue_title
        if issue.get("title") != desired_title:
            updates["title"] = desired_title
        if issue.get("body") != body:
            updates["body"] = body

        if updates:
            issue = gh(
                "PATCH",
                f"{API}/repos/{owner}/{repo_name}/issues/{issue['number']}",
                token,
                json=updates,
            )
            for idx, it in enumerate(cached_issues):
                if it["number"] == issue["number"]:
                    cached_issues[idx] = issue
                    break

        retire_legacy_issues(
            owner,
            repo_name,
            token,
            rel,
            issue,
            cached_issues,
            args.global_label,
            args.parent_label,
        )

        new_content, changed = upsert_related_issue_number_line(content, issue["number"])
        if changed:
            write_text(path, new_content)

        action = "created" if created else ("updated" if updates else "unchanged")
        print(f"Synced {rel} -> issue #{issue['number']} ({action})")


if __name__ == "__main__":
    main()
