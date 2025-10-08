#!/usr/bin/env python3
import argparse
import hashlib
import os
import re
from typing import Iterable, List, Optional, Tuple

import requests

API = "https://api.github.com"

TASK_RE = re.compile(r"^- \[( |x|X)\] (.*?)(?:\s*\(#?(\d+)\)|\s+#(\d+))?\s*$")
RELATED_ISSUE_LINE_RE = re.compile(r"^(\s*関連Issue:\s*)(.*)\s*$")
FRONT_MATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
TODO_MARKER_RE = re.compile(r"<!--\s*todo-path:\s*(.*?)\s*-->")

LABEL_MAX_LENGTH = 50


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


def extract_front_matter_fields(content: str) -> dict:
    m = FRONT_MATTER_RE.match(content)
    fields = {}
    if not m:
        return fields
    body = m.group(1)
    for line in body.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            fields[k.strip()] = v.strip()
    return fields


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


def build_scoped_label(prefix: str, todo_path: str) -> str:
    rel = normalize_repo_path(todo_path)
    digest = hashlib.sha1(rel.encode("utf-8")).hexdigest()[:6]
    slug = re.sub(r"[^a-z0-9]+", "-", rel.lower()).strip("-") or "todo"
    max_slug_len = max(1, LABEL_MAX_LENGTH - len(prefix) - len(digest) - 2)
    slug = slug[:max_slug_len]
    return f"{prefix}-{slug}-{digest}"


def extract_marker(body: Optional[str]) -> Optional[str]:
    if not body:
        return None
    m = TODO_MARKER_RE.search(body)
    return m.group(1).strip() if m else None


def ensure_issue_labels(owner: str, repo: str, token: str, issue, labels: Iterable[str]):
    desired = list(dict.fromkeys(labels))
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


def ensure_issue_marker(owner: str, repo: str, token: str, issue, rel_path: str):
    marker = f"<!-- todo-path: {rel_path} -->"
    body = issue.get("body") or ""
    if marker in body:
        return issue

    new_body = body.rstrip()
    if new_body:
        new_body += "\n\n"
    new_body += marker
    updated = gh(
        "PATCH",
        f"{API}/repos/{owner}/{repo}/issues/{issue['number']}",
        token,
        json={"body": new_body},
    )
    return updated


def update_issue_cache(cache: List[dict], issue: dict) -> None:
    for idx, existing in enumerate(cache):
        if existing["number"] == issue["number"]:
            cache[idx] = issue
            break
    else:
        cache.append(issue)


def collect_todo_paths(todo_paths: List[str], todo_dir: Optional[str], template_name: str, include_template: bool) -> List[str]:
    paths: List[str] = []
    for p in todo_paths:
        if p and os.path.isfile(p):
            paths.append(os.path.normpath(p))

    if todo_dir:
        for root, _dirs, files in os.walk(todo_dir):
            for fname in files:
                if not fname.endswith(".md"):
                    continue
                if not include_template and fname == template_name:
                    continue
                paths.append(os.path.normpath(os.path.join(root, fname)))

    unique = []
    seen = set()
    for p in sorted(paths):
        if not include_template and os.path.basename(p) == template_name:
            continue
        if p not in seen:
            unique.append(p)
            seen.add(p)
    return unique


def sync_tasks_for_file(
    owner: str,
    repo: str,
    token: str,
    todo_path: str,
    global_label: str,
    label_prefix: str,
    parent_label: str,
    cached_issues: List[dict],
) -> Tuple[Optional[int], bool]:
    rel_path = normalize_repo_path(todo_path)
    scoped_label = build_scoped_label(label_prefix, rel_path)
    ensure_label(owner, repo, token, global_label, "Synced from docs/todo files")
    ensure_label(owner, repo, token, scoped_label, f"Scoped ToDo label for {rel_path}")
    ensure_label(owner, repo, token, parent_label, "Parent card issue for ToDo files")

    marker = f"<!-- todo-path: {rel_path} -->"

    scoped_issues = [
        issue
        for issue in cached_issues
        if extract_marker(issue.get("body")) == rel_path
        or any(lbl["name"] == scoped_label for lbl in issue.get("labels", []))
    ]
    issues_by_number = {issue["number"]: issue for issue in scoped_issues}
    issues_by_title = {issue["title"]: issue for issue in scoped_issues}
    issues_global_by_number = {issue["number"]: issue for issue in cached_issues}

    tasks = parse_tasks(todo_path)

    for task in tasks:
        issue = None
        if task["issue_number"]:
            candidate = issues_global_by_number.get(task["issue_number"])
            if candidate:
                candidate_marker = extract_marker(candidate.get("body"))
                if candidate_marker and candidate_marker != rel_path:
                    candidate = None
                else:
                    issue = candidate

        if not issue and task["title"] in issues_by_title:
            issue = issues_by_title[task["title"]]

        if not issue:
            body = (
                f"This issue is managed by **{rel_path}** sync.\n\n"
                f"<!-- todo-path: {rel_path} -->"
            )
            issue = gh(
                "POST",
                f"{API}/repos/{owner}/{repo}/issues",
                token,
                json={
                    "title": task["title"],
                    "labels": [global_label, scoped_label],
                    "body": body,
                },
            )
            update_issue_cache(cached_issues, issue)
        else:
            ensure_issue_labels(owner, repo, token, issue, [global_label, scoped_label])
            issue = ensure_issue_marker(owner, repo, token, issue, rel_path)
            update_issue_cache(cached_issues, issue)

        issues_by_number[issue["number"]] = issue
        issues_by_title[issue["title"]] = issue
        issues_global_by_number[issue["number"]] = issue

        desired_open = not task["checked"]
        is_open = issue["state"] == "open"
        if desired_open and not is_open:
            issue = gh(
                "PATCH",
                f"{API}/repos/{owner}/{repo}/issues/{issue['number']}",
                token,
                json={"state": "open"},
            )
            update_issue_cache(cached_issues, issue)
        elif not desired_open and is_open:
            issue = gh(
                "PATCH",
                f"{API}/repos/{owner}/{repo}/issues/{issue['number']}",
                token,
                json={"state": "closed"},
            )
            update_issue_cache(cached_issues, issue)

        issues_by_number[issue["number"]] = issue

    content = read_text(todo_path)
    fields = extract_front_matter_fields(content)
    fm_lines = [f"{k}: {v}" for k, v in fields.items()] or ["(no front matter)"]

    parent_title = f"Todo Card: {rel_path}"
    cards = list_issues_by_label(owner, repo, token, parent_label)
    parent = next((it for it in cards if extract_marker(it.get("body")) == rel_path), None)
    if not parent:
        body = (
            f"Parent card for **{rel_path}**.\n\n"
            + "\n".join(fm_lines)
            + f"\n\n<!-- todo-path: {rel_path} -->"
        )
        parent = gh(
            "POST",
            f"{API}/repos/{owner}/{repo}/issues",
            token,
            json={
                "title": parent_title,
                "labels": [parent_label, scoped_label],
                "body": body,
            },
        )
    else:
        ensure_issue_labels(owner, repo, token, parent, [parent_label, scoped_label])
        parent = ensure_issue_marker(owner, repo, token, parent, rel_path)

    new_content, changed = upsert_related_issue_number_line(content, parent["number"])
    if changed:
        write_text(todo_path, new_content)

    return parent["number"], changed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--todo-path", action="append", default=[], help="ToDo Markdown ファイルのパス")
    ap.add_argument("--todo-dir", help="ToDo ファイルを探索するディレクトリ")
    ap.add_argument("--template-name", default="template.md", help="テンプレートファイル名")
    ap.add_argument("--include-template", action="store_true", help="テンプレートも同期対象に含める")
    ap.add_argument("--global-label", default="todo-sync", help="全 ToDo に共通で付与するラベル")
    ap.add_argument("--label-prefix", default="todo-sync", help="ToDo ファイル固有ラベルの接頭辞")
    ap.add_argument("--parent-label", default="todo-card", help="親カード Issue に付与するラベル")
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

    cached_issues = list_issues_by_label(owner, repo_name, token, args.global_label) if args.global_label else []

    for path in todo_files:
        if not os.path.isfile(path):
            continue
        parent_number, changed = sync_tasks_for_file(
            owner,
            repo_name,
            token,
            path,
            args.global_label,
            args.label_prefix,
            args.parent_label,
            cached_issues,
        )
        rel = normalize_repo_path(path)
        status = "updated" if changed else "unchanged"
        print(f"Synced {rel} (parent #{parent_number}) - {status}")


if __name__ == "__main__":
    main()
