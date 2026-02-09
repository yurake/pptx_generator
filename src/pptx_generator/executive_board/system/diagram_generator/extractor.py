"""
システム情報抽出ロジック

パース結果から依存関係を解決し、DependencyRelationを生成する。
"""

from __future__ import annotations

import logging
from typing import Dict, List

from .models import CaseSystemDiagram, DependencyRelation, SystemComponent, SystemDiagramData

logger = logging.getLogger(__name__)


class SystemExtractor:
    """システム情報抽出器"""

    def _normalize_system_name(self, name: str) -> str:
        """
        システム名を正規化

        「〜層」「〜サービス」などの接尾辞を除去して、
        より柔軟なマッチングを可能にする。
        """
        suffixes = ["層", "サービス", "モジュール", "エンジン", "ゲートウェイ"]
        normalized = name
        for suffix in suffixes:
            if normalized.endswith(suffix):
                normalized = normalized[: -len(suffix)]
        return normalized.strip()

    def extract_relations(self, diagram_data: SystemDiagramData) -> SystemDiagramData:
        """
        依存関係を解決してDependencyRelationを生成

        各コンポーネントのdependenciesリストから、実際の依存関係を構築する。
        """
        updated_cases: List[CaseSystemDiagram] = []

        for case in diagram_data.cases:
            component_map: Dict[str, SystemComponent] = {
                comp.name: comp for comp in case.components
            }

            normalized_map: Dict[str, SystemComponent] = {
                self._normalize_system_name(comp.name): comp for comp in case.components
            }

            relations: List[DependencyRelation] = []

            for component in case.components:
                for dep_name in component.dependencies:
                    dep_component = component_map.get(dep_name)

                    if not dep_component:
                        normalized_dep = self._normalize_system_name(dep_name)
                        dep_component = normalized_map.get(normalized_dep)

                    if dep_component:
                        process_desc = self._extract_process_description(
                            component, dep_component
                        )

                        relations.append(
                            DependencyRelation(
                                from_system=component.name,
                                to_system=dep_component.name,
                                process_description=process_desc,
                            )
                        )
                    else:
                        logger.warning(
                            "Dependency not found: %s -> %s in case %s",
                            component.name,
                            dep_name,
                            case.case_id,
                        )

            updated_case = CaseSystemDiagram(
                case_id=case.case_id,
                case_name=case.case_name,
                components=case.components,
                relations=relations,
            )
            updated_cases.append(updated_case)

        return SystemDiagramData(cases=updated_cases)

    def _extract_process_description(
        self, from_comp: SystemComponent, to_comp: SystemComponent
    ) -> str:
        """
        処理内容を抽出

        依存元の役割から、依存先への処理内容を推測する。
        """
        role_lower = from_comp.role.lower()
        to_name_lower = to_comp.name.lower()

        keywords = {
            "認証": "認証処理",
            "決済": "決済実行",
            "データ": "データ保存",
            "記録": "記録保存",
            "検知": "検知処理",
            "管理": "管理処理",
            "参照": "情報参照",
            "連携": "連携処理",
        }

        for keyword, description in keywords.items():
            if keyword in role_lower or keyword in to_name_lower:
                return description

        return f"{to_comp.name}利用"
