#!/usr/bin/env python3
import os
import re
import argparse
import requests
from typing import Tuple

API = "https://api.github.com"

TASK_RE = re.compile(r"^- \[( |x|X)\] (.*?)(?:\s*\(#?(\d+)\)|\s+#(\d+))?\s*$")
RELATED_ISSUE_LINE_RE = re.compile(r"^(\s*関連Issue:\s*)(.*)\s*$")
FRONT_MATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)

def read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def write_text(path: str, content: str):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

def parse_tasks(md_path: str):
    tasks = []
    with open(md_path, 'r', encoding='utf-8') as f:
        for line in f:
            m = TASK_RE.match(line)
            if not m:
                continue
            checked = (m.group(1).lower() == 'x')
            title = m.group(2).strip()
            num = m.group(3) or m.group(4)
            issue_number = int(num) if num else None
            tasks.append({
                'title': title,
                'checked': checked,
                'issue_number': issue_number,
            })
    return tasks

def gh(method: str, url: str, token: str, **kwargs):
    headers = kwargs.pop('headers', {})
    headers.update({
        'Authorization': f'Bearer {token}',
        'Accept': 'application/vnd.github+json',
    })
    r = requests.request(method, url, headers=headers, **kwargs)
    if r.status_code >= 400:
        raise RuntimeError(f"GitHub API error {r.status_code}: {r.text}")
    return r.json() if r.text else {}

def ensure_label(owner: str, repo: str, token: str, label: str, desc: str = 'Synced by template.md'):
    try:
        gh('GET', f"{API}/repos/{owner}/{repo}/labels/{label}", token)
    except Exception:
        gh('POST', f"{API}/repos/{owner}/{repo}/labels", token,
           json={'name': label, 'color': '0e8a16', 'description': desc})

def list_issues_by_label(owner: str, repo: str, token: str, label: str):
    issues = []
    page = 1
    while True:
        data = gh('GET', f"{API}/repos/{owner}/{repo}/issues", token,
                  params={'state': 'all', 'labels': label, 'per_page': 100, 'page': page})
        if not data:
            break
        for it in data:
            if 'pull_request' in it:
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
            fields[k].strip() if k in fields else None
            fields[k.strip()] = v.strip()
    return fields

def upsert_related_issue_number_line(content: str, number: int) -> Tuple[str, bool]:
    changed = False
    lines = content.splitlines()
    for i, line in enumerate(lines):
        m = RELATED_ISSUE_LINE_RE.match(line)
        if m:
            prefix, rest = m.group(1), m.group(2)
            if rest.strip() == "未作成" or rest.strip() == "":
                lines[i] = f"{prefix}#{number}"
                changed = True
            elif rest.strip().startswith("#"):
                pass
            else:
                lines[i] = f"{prefix}#{number}"
                changed = True
            break
    else:
        inset = f"関連Issue: #{number}"
        # try placing after front matter if exists
        fm = FRONT_MATTER_RE.match(content)
        if fm:
            endpos = fm.end()
            content = content[:endpos] + inset + "\n" + content[endpos:]
            changed = True
        else:
            content = inset + "\n" + content
            changed = True
        return content, changed
    return ("
".join(lines) + ("
" if content.endswith("\n") else "")), changed

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--todo-path', default='docs/todo/template.md')
    ap.add_argument('--label', default='todo-sync')
    ap.add_argument('--parent-label', default='todo-card')
    args = ap.parse_args()

    repo = os.environ.get('GITHUB_REPOSITORY')
    token = os.environ.get('GITHUB_TOKEN')
    if not repo or not token:
        raise SystemExit('GITHUB_REPOSITORY and GITHUB_TOKEN are required')
    owner, repo_name = repo.split('/')

    ensure_label(owner, repo_name, token, args.label, 'Synced from template.md tasks')
    ensure_label(owner, repo_name, token, args.parent_label, 'Parent card issue')

    # Per-task issues
    tasks = parse_tasks(args.todo_path)
    existing = list_issues_by_label(owner, repo_name, token, args.label)
    issues_by_number = {i['number']: i for i in existing}
    issues_by_title = {i['title']: i for i in existing}

    for t in tasks:
        issue = None
        if t['issue_number'] and t['issue_number'] in issues_by_number:
            issue = issues_by_number[t['issue_number']]
        elif t['title'] in issues_by_title:
            issue = issues_by_title[t['title']]
        else:
            created = gh('POST', f"{API}/repos/{owner}/{repo_name}/issues", token,
                        json={'title': t['title'], 'labels': [args.label],
                              'body': 'This issue is managed by **template.md** sync.'})
            issue = created

        labels = [l['name'] for l in issue.get('labels', [])]
        if args.label not in labels:
            gh('POST', f"{API}/repos/{owner}/{repo_name}/issues/{issue['number']}/labels", token,
               json={'labels': [args.label]})

        desired_open = not t['checked']
        is_open = (issue['state'] == 'open')
        if desired_open and not is_open:
            gh('PATCH', f"{API}/repos/{owner}/{repo_name}/issues/{issue['number']}", token, json={'state': 'open'})
        elif not desired_open and is_open:
            gh('PATCH', f"{API}/repos/{owner}/{repo_name}/issues/{issue['number']}", token, json={'state': 'closed'})

    # Parent card issue
    content = read_text(args.todo_path)
    fields = extract_front_matter_fields(content)
    parent_title = fields.get('目的') or f"Todo Card: {os.path.basename(args.todo_path)}"

    cards = list_issues_by_label(owner, repo_name, token, args.parent_label)
    parent = next((it for it in cards if it['title'] == parent_title), None)
    if not parent:
        fm_lines = [f"{k}: {v}" for k, v in fields.items()] or ["(no front matter)"]
        body = "Parent card for this TODO template.\n\n" + "\n".join(fm_lines)
        parent = gh('POST', f"{API}/repos/{owner}/{repo_name}/issues", token,
                    json={'title': parent_title, 'labels': [args.parent_label], 'body': body})

    new_content, changed = upsert_related_issue_number_line(content, parent['number'])
    if changed:
        write_text(args.todo_path, new_content)

if __name__ == '__main__':
    main()
