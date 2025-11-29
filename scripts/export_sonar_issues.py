#!/usr/bin/env python3
"""
export_sonar_issues.py

SonarCloud の Issues を取得して、ファイルごとにまとめた JSON を出力するスクリプト。

- 認証情報:
    - SONAR_TOKEN       : SonarCloud のトークン (必須)
    - SONAR_PROJECT_KEY : SonarCloud の Project Key (必須)

- 代表的な使い方:
    SONAR_TOKEN=xxxxx SONAR_PROJECT_KEY=yyyyy python export_sonar_issues.py

`.env` (カレントディレクトリ) が存在する場合は自動で読み込まれる。

主要オプション:
- --branch     : 解析対象ブランチ (default: main)
- --severities : 取得対象の重大度 (default: BLOCKER,CRITICAL,MAJOR)
- --types      : 取得対象の種別 (default: BUG,VULNERABILITY,CODE_SMELL)
- --statuses   : 取得対象のステータス (default: OPEN,CONFIRMED,REOPENED)
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
import requests

DEFAULT_BASE_URL = "https://sonarcloud.io"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export SonarCloud issues and group them by file path."
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"SonarCloud base URL (default: {DEFAULT_BASE_URL})",
    )
    parser.add_argument(
        "--branch",
        default="main",
        help="Branch name to filter issues (default: main)",
    )
    parser.add_argument(
        "--severities",
        default="BLOCKER,CRITICAL,MAJOR",
        help="Comma-separated severities (default: BLOCKER,CRITICAL,MAJOR).",
    )
    parser.add_argument(
        "--types",
        default="BUG,VULNERABILITY,CODE_SMELL",
        help="Comma-separated types (default: BUG,VULNERABILITY,CODE_SMELL).",
    )
    parser.add_argument(
        "--statuses",
        default="OPEN,CONFIRMED,REOPENED",
        help="Comma-separated statuses (default: OPEN,CONFIRMED,REOPENED).",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=500,
        help="Page size for SonarCloud API (max 500, default: 500)",
    )
    parser.add_argument(
        "--max-issues",
        type=int,
        default=None,
        help="Optional hard limit for number of issues to fetch (for safety)",
    )
    parser.add_argument(
        "--output",
        default="temp/sonar_issues_by_file.json",
        help="Output JSON file path (default: temp/sonar_issues_by_file.json)",
    )
    return parser.parse_args()


def build_headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
    }


def fetch_all_issues(
    base_url: str,
    token: str,
    project_key: str,
    branch: Optional[str] = None,
    severities: Optional[str] = None,
    types: Optional[str] = None,
    statuses: Optional[str] = None,
    page_size: int = 500,
    max_issues: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    SonarCloud /api/issues/search をページングして、すべての issue を取得する。
    """
    if page_size <= 0 or page_size > 500:
        raise ValueError("page_size must be between 1 and 500.")

    url = f"{base_url.rstrip('/')}/api/issues/search"
    headers = build_headers(token)

    page_index = 1
    issues: List[Dict[str, Any]] = []

    while True:
        params: Dict[str, Any] = {
            "projectKeys": project_key,
            "ps": page_size,
            "p": page_index,
            "additionalFields": "_all",
        }
        if branch:
            params["branch"] = branch
        if severities:
            params["severities"] = severities
        if types:
            params["types"] = types
        if statuses:
            params["statuses"] = statuses

        resp = requests.get(url, headers=headers, params=params, timeout=30)
        try:
            resp.raise_for_status()
        except requests.HTTPError as e:
            print(
                f"[ERROR] Failed to call SonarCloud API: {e} "
                f"(status={resp.status_code}, body={resp.text[:500]!r})",
                file=sys.stderr,
            )
            raise

        data = resp.json()
        batch = data.get("issues", [])
        paging = data.get("paging", {}) or {}
        total = paging.get("total")

        if not batch:
            break

        issues.extend(batch)

        # 安全のための上限
        if max_issues is not None and len(issues) >= max_issues:
            issues = issues[:max_issues]
            break

        # paging 情報に基づいて終了判定
        if total is not None and len(issues) >= total:
            break

        page_index += 1

    return issues


def extract_file_path(component: str, project_key: str) -> str:
    """
    SonarCloud の component は一般的に
      <projectKey>:path/to/file.py
    のような形式になっているので、projectKey 部分を削除してファイルパスだけを返す。
    """
    prefix = f"{project_key}:"
    if component.startswith(prefix):
        return component[len(prefix):]
    # 念のためのフォールバック
    if ":" in component:
        return component.split(":", 1)[1]
    return component


def group_issues_by_file(
    issues: List[Dict[str, Any]],
    project_key: str,
) -> Dict[str, List[Dict[str, Any]]]:
    """
    issues をファイルパスごとにまとめる。

    出力形式のイメージ:
    {
      "path/to/file.py": [
        {
          "line": 123,
          "severity": "MAJOR",
          "type": "CODE_SMELL",
          "rule": "python:S125",
          "message": "...",
          "issue_key": "AXxxxxxxx",
          "status": "OPEN"
        },
        ...
      ],
      ...
    }
    """
    result: Dict[str, List[Dict[str, Any]]] = {}

    for issue in issues:
        component = issue.get("component") or ""
        file_path = extract_file_path(component, project_key)

        line = issue.get("line")
        severity = issue.get("severity")
        issue_type = issue.get("type")
        rule = issue.get("rule")
        message = issue.get("message")
        issue_key = issue.get("key")
        status = issue.get("status")

        entry = {
            "line": line,
            "severity": severity,
            "type": issue_type,
            "rule": rule,
            "message": message,
            "issue_key": issue_key,
            "status": status,
        }

        result.setdefault(file_path, []).append(entry)

    # 行番号 + severity でソートしておくとエージェントが扱いやすい
    def sort_key(item: Dict[str, Any]) -> Any:
        line_val = item.get("line") or 0
        severity_val = item.get("severity") or ""
        return (line_val, severity_val)

    for file_path, items in result.items():
        items.sort(key=sort_key)

    return result


def main() -> None:
    args = parse_args()

    load_dotenv()

    project_key = os.environ.get("SONAR_PROJECT_KEY")
    token = os.environ.get("SONAR_TOKEN")

    if not project_key:
        print(
            "[ERROR] Env SONAR_PROJECT_KEY must be set.",
            file=sys.stderr,
        )
        sys.exit(1)

    if not token:
        print(
            "[ERROR] Env SONAR_TOKEN must be set.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(
        f"[INFO] Fetching issues from SonarCloud project={project_key!r} "
        f"branch={args.branch!r} severities={args.severities!r} "
        f"types={args.types!r} statuses={args.statuses!r}",
        file=sys.stderr,
    )

    issues = fetch_all_issues(
        base_url=args.base_url,
        token=token,
        project_key=project_key,
        branch=args.branch,
        severities=args.severities,
        types=args.types,
        statuses=args.statuses,
        page_size=args.page_size,
        max_issues=args.max_issues,
    )

    print(f"[INFO] Fetched {len(issues)} issues.", file=sys.stderr)

    grouped = group_issues_by_file(issues, project_key=project_key)

    output_path = Path(args.output)
    if output_path.parent and not output_path.parent.exists():
        output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(grouped, f, ensure_ascii=False, indent=2)

    print(f"[INFO] Exported grouped issues to {output_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
