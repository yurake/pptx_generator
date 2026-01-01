"""スライド生成で使用するプロンプト組み立てヘルパー。"""

from __future__ import annotations

import textwrap

from .models import AIGenerationRequest


def build_user_prompt(request: AIGenerationRequest) -> str:
    instructions = request.policy.safeguards.get("user_instructions") if isinstance(request.policy.safeguards, dict) else None
    guidance = instructions or textwrap.dedent(
        """
        以下の要件を必ず守って JSON 形式で回答してください。
        - JSON オブジェクトのキーは title, body, note。
        - body は本文を段落や箇条書きごとの文字列として配列に格納し、途中で切り捨てず全文を保持してください。
        - note が不要な場合は null を指定。
        - 日本語で回答する。
        """
    ).strip()
    reference_section = ""
    if request.reference_text:
        reference_section = f"\n\n# 参考テキスト\n{request.reference_text}"
    return f"{guidance}\n\n# スライド情報\n{request.prompt}{reference_section}"


def build_system_prompt(request: AIGenerationRequest) -> str:
    safeguards = request.policy.safeguards if isinstance(request.policy.safeguards, dict) else {}
    default_prompt = "あなたは B2B プレゼン資料のコンテンツ作成を支援する専門アシスタントです。"
    return str(safeguards.get("system_prompt", default_prompt))
