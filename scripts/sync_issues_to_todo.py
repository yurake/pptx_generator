#!/usr/bin/env python3
import argparse
import os
import re
from typing import List, Optional

import requests

API = "https://api.github.com"
BEGIN = "<!-- BEGIN: issues-sync -->"
END = "<!-- END: issues-sync -->"
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
        data = gh(
            "GET",
            f"{API}/repos/{owner}/{repo}/issues",
            token,
            params={"state": "all", "labels": label, "per_page": 100, "page": page},
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


def render_block(issues):
    lines = ["## Synced Issues\n"]
    for it in issues:
        mark = "x" if it["state"] == "closed" else " "
        lines.append(f"- [{mark}] {it['title']} (#{it['number']})\n")
    return "".join(lines)


def upsert_block(md_path, new_block):
    if not os.path.exists(md_path):
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(f"{BEGIN}\n{new_block}{END}\n")
        return True

    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()

    start = content.find(BEGIN)
    end = content.find(END)

    if start == -1 or end == -1 or end < start:
        updated = content
        if not content.endswith("\n"):
            updated += "\n"
        updated += f"\n{BEGIN}\n{new_block}{END}\n"
    else:
        updated = content[: start + len(BEGIN)] + "\n" + new_block + content[end:]

    if updated != content:
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(updated)
        return True
    return False


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


def select_issues_for_path(issues: List[dict], todo_path: str):
    rel_path = normalize_repo_path(todo_path)
    res = []
    for issue in issues:
        body = issue.get("body")
        marker = None
        if body:
            m = TODO_MARKER_RE.search(body)
            if m:
                marker = m.group(1).strip()
        if marker == rel_path:
            res.append(issue)
    res.sort(key=lambda i: (i["state"] != "open", i["number"]))
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--todo-path", action="append", default=[], help="ToDo Markdown ファイルのパス")
    ap.add_argument("--todo-dir", help="ToDo ファイルを探索するディレクトリ")
    ap.add_argument("--template-name", default="template.md", help="テンプレートファイル名")
    ap.add_argument("--include-template", action="store_true", help="テンプレートも同期対象に含める")
    ap.add_argument("--global-label", default="todo-sync", help="全 ToDo に共通で付与するラベル")
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

    all_issues = list_issues_by_label(owner, repo_name, token, args.global_label) if args.global_label else []

    for path in todo_files:
        if not os.path.isfile(path):
            continue
        issues = select_issues_for_path(all_issues, path)
        block = render_block(issues)
        changed = upsert_block(path, block)
        rel = normalize_repo_path(path)
        print(f"Synced issues block for {rel}: changed={changed}")


if __name__ == "__main__":
    main()
