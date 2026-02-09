"""
LLMベースのMarkdownパーサー

Markdownから「システム対応概要」セクションを抽出し、
システムコンポーネント情報を構造化データに変換する。
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Callable, Protocol

from llm import (
    load_azure_openai_config,
    load_openai_chat_config,
    log_provider_resolution,
    resolve_llm_provider,
)

from .models import CaseSystemDiagram, SystemComponent, SystemDiagramData

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ParseResult:
    """パース結果"""

    diagram_data: SystemDiagramData
    model: str
    warnings: list[str]
    tokens: dict[str, int]


class DiagramParserClient(Protocol):
    """Diagram Parser LLM クライアントのインターフェース"""

    def parse(self, markdown_text: str) -> ParseResult:
        """Markdownテキストからシステム構成情報を抽出"""


class DiagramParserConfigurationError(RuntimeError):
    """パーサー設定エラー"""


SYSTEM_EXTRACTION_PROMPT = """あなたは技術文書からシステム構成情報を抽出する専門家です。

以下のMarkdownテキストから「システム対応概要」セクションを見つけ、
各システムコンポーネントの情報を抽出してJSON形式で出力してください。

抽出する情報:
1. システム/サービス名称
2. 技術例（使用技術・製品名）
3. 依存関係（このシステムが依存する他のシステム名のリスト）
4. 役割・処理内容

出力形式（JSON）:
{{
  "cases": [
    {{
      "case_id": "case1",
      "case_name": "案件名",
      "components": [
        {{
          "name": "システム名",
          "technology": "技術例",
          "dependencies": ["依存先1", "依存先2"],
          "role": "役割・処理内容",
          "case_id": "case1"
        }}
      ]
    }}
  ]
}}

重要な注意事項:
- 各案件ごとに case_id を割り当ててください（case1, case2, ...）
- case_name は案件のタイトルから抽出してください
- dependencies は依存先システムの name と完全一致する文字列のリストにしてください
- 依存関係が記載されていない場合は空のリスト [] にしてください
- 出力はJSON形式のみで、説明文は含めないでください

入力テキスト:
{markdown_text}
"""


def create_diagram_parser() -> DiagramParserClient:
    """Diagram Parser クライアントを作成"""
    resolution = resolve_llm_provider(
        primary_env="PPTX_DIAGRAM_LLM_PROVIDER",
        fallback_env="PPTX_LLM_PROVIDER",
        default="mock",
    )
    log_provider_resolution(logger, component="diagram_parser", resolution=resolution)

    factories: dict[str, Callable[[], DiagramParserClient]] = {
        "mock": MockDiagramParser,
        "openai": OpenAIDiagramParser.from_env,
        "azure-openai": AzureOpenAIDiagramParser.from_env,
    }

    factory = factories.get(resolution.provider)
    if factory is None:
        raise DiagramParserConfigurationError(
            f"未知の LLM プロバイダーです: {resolution.provider}"
        )

    return factory()


class MockDiagramParser:
    """モック実装（テスト用）"""

    def parse(self, markdown_text: str) -> ParseResult:
        """正規表現ベースの簡易パース"""
        cases: list[CaseSystemDiagram] = []

        case_pattern = r"# 案件名：(.+?)(?=\n# 案件名：|\Z)"
        case_matches = re.finditer(case_pattern, markdown_text, re.DOTALL)

        for case_idx, case_match in enumerate(case_matches, start=1):
            case_text = case_match.group(0)
            full_case_name = case_match.group(1).strip()
            case_name = full_case_name.split("\n")[0].strip()
            case_id = f"case{case_idx}"

            components: list[SystemComponent] = []

            overview_pattern = r"## システム対応概要（サンプル）(.+?)(?=\n## |\Z)"
            overview_match = re.search(overview_pattern, case_text, re.DOTALL)

            if overview_match:
                overview_text = overview_match.group(1)

                component_pattern = r"\*\s+\*\*(.+?):\*\*\s+(.+?)(?=\n\s+-\s+技術例|\n\*\s+\*\*|\Z)"
                component_matches = re.finditer(component_pattern, overview_text, re.DOTALL)

                for comp_match in component_matches:
                    system_name = comp_match.group(1).strip()
                    description = comp_match.group(2).strip()

                    layer = self._infer_layer(system_name)

                    tech_pattern = r"-\s+技術例：(.+?)(?=\n|$)"
                    tech_match = re.search(tech_pattern, overview_text[comp_match.end() :])
                    technology = tech_match.group(1).strip() if tech_match else None

                    dep_pattern = r"-\s+依存：(.+?)(?=\n|$)"
                    dep_match = re.search(dep_pattern, overview_text[comp_match.end() :])
                    dependencies: list[str] = []
                    if dep_match:
                        dep_text = dep_match.group(1).strip()
                        dependencies = [d.strip() for d in dep_text.split("、")]

                    role_pattern = r"-\s+役割：(.+?)(?=\n\*|\Z)"
                    role_match = re.search(
                        role_pattern, overview_text[comp_match.end() :], re.DOTALL
                    )
                    role = role_match.group(1).strip() if role_match else description

                    components.append(
                        SystemComponent(
                            name=system_name,
                            technology=technology,
                            dependencies=dependencies,
                            role=role,
                            case_id=case_id,
                            layer=layer,
                            responsibilities=[],
                        )
                    )

            items_pattern = r"## システム対応項目（サンプル）(.+?)(?=\n## |\Z)"
            items_match = re.search(items_pattern, case_text, re.DOTALL)

            if items_match and components:
                items_text = items_match.group(1)

                system_items_pattern = r"\*\s+\*\*(.+?)\*\*(.+?)(?=\n\s*\*\s+\*\*|\Z)"
                system_items_matches = re.finditer(system_items_pattern, items_text, re.DOTALL)

                for sys_item_match in system_items_matches:
                    system_header = sys_item_match.group(1).strip()
                    system_content = sys_item_match.group(2).strip()

                    system_name = system_header.split("（")[0].strip()
                    target_components = [
                        comp for comp in components if comp.name == system_name
                    ]

                    if target_components:
                        responsibilities = self._extract_responsibilities(system_content)
                        target_components[0].responsibilities = responsibilities

            cases.append(
                CaseSystemDiagram(
                    case_id=case_id,
                    case_name=case_name,
                    components=components,
                    relations=[],
                )
            )

        diagram_data = SystemDiagramData(cases=cases)

        return ParseResult(
            diagram_data=diagram_data,
            model="mock",
            warnings=[],
            tokens={"prompt": 0, "completion": 0, "total": 0},
        )

    def _extract_responsibilities(self, text: str) -> list[str]:
        items = []
        for line in text.split("\n"):
            line = line.strip()
            if line.startswith("-"):
                items.append(line[1:].strip())
        return items

    def _infer_layer(self, system_name: str) -> str | None:
        if "層" in system_name:
            return system_name

        layer_keywords = {
            "APIゲートウェイ": "APIゲートウェイ層",
            "ゲートウェイ": "APIゲートウェイ層",
            "認証": "アプリケーション層",
            "サービス": "アプリケーション層",
            "エンジン": "アプリケーション層",
            "統合": "統合層",
            "ブロックチェーン": "統合層",
            "データベース": "データ層",
            "DB": "データ層",
            "ストレージ": "データ層",
        }

        for keyword, layer in layer_keywords.items():
            if keyword in system_name:
                return layer

        return None


class OpenAIDiagramParser:
    """OpenAI APIを使用したパーサー"""

    def __init__(self, client: Any, model: str):
        self.client = client
        self.model = model

    @classmethod
    def from_env(cls) -> OpenAIDiagramParser:
        config = load_openai_chat_config(
            default_model="gpt-4o-mini",
            default_temperature=0.1,
            default_max_tokens=4000,
            error_cls=DiagramParserConfigurationError,
        )
        import openai

        client = openai.OpenAI(api_key=config.api_key, base_url=config.base_url)
        return cls(client, config.model)

    def parse(self, markdown_text: str) -> ParseResult:
        prompt = SYSTEM_EXTRACTION_PROMPT.format(markdown_text=markdown_text)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "あなたは技術文書解析の専門家です。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            if not content:
                raise ValueError("LLM response is empty")

            data = json.loads(content)
            diagram_data = SystemDiagramData(**data)

            tokens = {
                "prompt": response.usage.prompt_tokens if response.usage else 0,
                "completion": response.usage.completion_tokens if response.usage else 0,
                "total": response.usage.total_tokens if response.usage else 0,
            }

            return ParseResult(
                diagram_data=diagram_data,
                model=self.model,
                warnings=[],
                tokens=tokens,
            )

        except Exception as exc:
            logger.error("OpenAI API error: %s", exc)
            raise


class AzureOpenAIDiagramParser:
    """Azure OpenAI APIを使用したパーサー"""

    def __init__(self, client: Any, model: str):
        self.client = client
        self.model = model

    @classmethod
    def from_env(cls) -> AzureOpenAIDiagramParser:
        config = load_azure_openai_config(
            default_temperature=0.1,
            default_max_tokens=4000,
            default_api_version="2024-02-15-preview",
            error_cls=DiagramParserConfigurationError,
        )
        import openai

        client = openai.AzureOpenAI(
            api_key=config.api_key,
            api_version=config.api_version,
            azure_endpoint=config.endpoint,
        )
        return cls(client, config.deployment)

    def parse(self, markdown_text: str) -> ParseResult:
        prompt = SYSTEM_EXTRACTION_PROMPT.format(markdown_text=markdown_text)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "あなたは技術文書解析の専門家です。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            if not content:
                raise ValueError("LLM response is empty")

            data = json.loads(content)
            diagram_data = SystemDiagramData(**data)

            tokens = {
                "prompt": response.usage.prompt_tokens if response.usage else 0,
                "completion": response.usage.completion_tokens if response.usage else 0,
                "total": response.usage.total_tokens if response.usage else 0,
            }

            return ParseResult(
                diagram_data=diagram_data,
                model=self.model,
                warnings=[],
                tokens=tokens,
            )

        except Exception as exc:
            logger.error("Azure OpenAI API error: %s", exc)
            raise


class DiagramParser:
    """Diagram Parser のファサード"""

    def __init__(self, client: DiagramParserClient | None = None):
        self.client = client or create_diagram_parser()

    def parse_markdown(self, markdown_text: str) -> SystemDiagramData:
        result = self.client.parse(markdown_text)
        logger.info(
            "Diagram parsing completed: model=%s, cases=%d, tokens=%s",
            result.model,
            len(result.diagram_data.cases),
            result.tokens,
        )
        return result.diagram_data
