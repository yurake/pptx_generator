#!/usr/bin/env python3
import os
import argparse
import requests

API = "https://api.github.com"
BEGIN = "<!-- BEGIN: issues-sync -->"
END = "<!-- END: issues-sync -->"

def gh(method, url, token, **kwargs):
    headers = kwargs.pop('headers', {})
    headers.update({'Authorization': f'Bearer {token}', 'Accept': 'application/vnd.github+json'})
    r = requests.request(method, url, headers=headers, **kwargs)
    if r.status_code >= 400:
        raise RuntimeError(f"GitHub API error {r.status_code}: {r.text}")
    return r.json() if r.text else {}

def list_synced_issues(owner, repo, token, label):
    res = []
    page = 1
    while True:
        data = gh('GET', f"{API}/repos/{owner}/{repo}/issues", token,
                  params={'state': 'all', 'labels': label, 'per_page': 100, 'page': page})
        if not data:
            break
        for it in data:
            if 'pull_request' in it:
                continue
            res.append(it)
        if len(data) < 100:
            break
        page += 1
    res.sort(key=lambda i: (i['state'] != 'open', i['number']))
    return res

def render_block(issues):
    lines = ["## Synced Issues\n"]
    for it in issues:
        mark = 'x' if it['state'] == 'closed' else ' '
        lines.append(f"- [{mark}] {it['title']} (#{it['number']})\n")
    return ''.join(lines)

def upsert_block(md_path, new_block):
    if not os.path.exists(md_path):
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(f"{BEGIN}\n{new_block}{END}\n")
        return True

    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()

    start = content.find(BEGIN)
    end = content.find(END)

    if start == -1 or end == -1 or end < start:
        updated = content
        if not content.endswith('\n'):
            updated += '\n'
        updated += f"\n{BEGIN}\n{new_block}{END}\n"
    else:
        updated = content[:start + len(BEGIN)] + "\n" + new_block + content[end:]

    if updated != content:
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(updated)
        return True
    return False

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--todo-path', default='docs/todo/template.md')
    ap.add_argument('--label', default='todo-sync')
    args = ap.parse_args()

    repo = os.environ.get('GITHUB_REPOSITORY')
    token = os.environ.get('GITHUB_TOKEN')
    if not repo or not token:
        raise SystemExit('GITHUB_REPOSITORY and GITHUB_TOKEN are required')
    owner, repo_name = repo.split('/')

    issues = list_synced_issues(owner, repo_name, token, args.label)
    block = render_block(issues)
    changed = upsert_block(args.todo_path, block)
    print('changed=' + str(changed))

if __name__ == '__main__':
    main()
