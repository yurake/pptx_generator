"""PPTX テンプレートから branding.json 互換の設定を抽出する PoC スクリプト。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pptx_generator.branding_extractor import (
    BrandingExtractionError,
    extract_branding_config,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--template",
        required=True,
        type=Path,
        help="入力となる PPTX テンプレートのパス",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="抽出したブランド設定を書き出す JSON ファイル。未指定時は標準出力に表示",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="JSON をインデント付きで出力する",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        result = extract_branding_config(args.template)
    except BrandingExtractionError as exc:
        print(f"[branding_extract] エラー: {exc}", file=sys.stderr)
        return 1

    data = result.as_dict()
    json_text = json.dumps(data, ensure_ascii=False, indent=2 if args.pretty else None)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json_text + ("\n" if not json_text.endswith("\n") else ""), encoding="utf-8")
    else:
        print(json_text)

    return 0


if __name__ == "__main__":
    sys.exit(main())
