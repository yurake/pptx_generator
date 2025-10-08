#!/usr/bin/env python3
import argparse
import os
import re
from typing import Dict, List, Optional

import requests

API = "https://api.github.com"
TASK_RE = re.compile(r"^- \[( |x|X)\] (.*?)(?:\s*\(#?(\d+)\)|\s+#(\d+))?\s*$")
TODO_MARKER_RE = re.compile(r"<!--\s*todo-path:\s*(.*?)\s*-->")


def gh(method, url, token, **kwargs):
    headers = kwargs.pop("headers", {})
    headers.update({"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"})
    r = requests.request(method, url, headers=headers, **kwargs)
    if r.status_code >= 400:
        raise RuntimeError(f"GitHub API error {r.status_code}: {r.text}")
    return r.json() if r.text else {}


def list_issues_by_label(owner, repo, token, label):
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


def extract_marker(body: Optional[str]) -> Optional[str]:
    if not body:
        return None
    m = TODO_MARKER_RE.search(body)
    return m.group(1).strip() if m else None


def parse_task_states(text: str) -> Dict[str, bool]:
    states: Dict[str, bool] = {}
    if not text:
        return states
    for line in text.splitlines():
        m = TASK_RE.match(line)
        if not m:
            continue
        title = m.group(2).strip()
        states[title] = (m.group(1).lower() == "x")
    return states


def apply_task_states(content: str, states: Dict[str, bool]) -> tuple[str, bool]:
    if not states:
        return content, False
    lines = content.splitlines()
    changed = False
    for idx, line in enumerate(lines):
        m = TASK_RE.match(line)
        if not m:
            continue
        title = m.group(2).strip()
        if title not in states:
            continue
        desired_checked = states[title]
        current_checked = (m.group(1).lower() == "x")
        if current_checked == desired_checked:
            continue
        marker = "x" if desired_checked else " "
        lines[idx] = f"- [{marker}] {m.group(2)}"
        if m.group(3):
            lines[idx] += f" (#{m.group(3)})"
        elif m.group(4):
            lines[idx] += f" #{m.group(4)}"
        changed = True
    updated = "\n".join(lines)
    if content.endswith("\n"):
        updated += "\n"
    return updated, changed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--todo-path", action="append", default=[], help="ToDo Markdown ファイルのパス")
    ap.add_argument("--todo-dir", help="ToDo ファイルを探索するディレクトリ")
    ap.add_argument("--template-name", default="template.md", help="テンプレートファイル名")
    ap.add_argument("--include-template", action="store_true", help="テンプレートも同期対象に含める")
    ap.add_argument("--global-label", default="todo-sync", help="Issue に付与された共通ラベル")
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

    issues = list_issues_by_label(owner, repo_name, token, args.global_label)
    issues_by_path = {extract_marker(issue.get("body")): issue for issue in issues if extract_marker(issue.get("body"))}

    for path in todo_files:
        if not os.path.isfile(path):
            continue
        rel = normalize_repo_path(path)
        issue = issues_by_path.get(rel)
        if not issue:
            print(f"Skip {rel}: related issue not found")
            continue

        states = parse_task_states(issue.get("body", ""))
        if not states:
            print(f"Skip {rel}: no tasks found in issue #{issue['number']}")
            continue

        content = read_text(path)
        updated, changed = apply_task_states(content, states)
        if changed:
            write_text(path, updated)
            print(f"Updated {rel} from issue #{issue['number']}")
        else:
            print(f"No changes for {rel}")


def read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write_text(path: str, content: str):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


if __name__ == "__main__":
    main()
