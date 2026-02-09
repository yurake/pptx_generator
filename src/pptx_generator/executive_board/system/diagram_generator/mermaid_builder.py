"""
Mermaid記法ビルダー

SystemDiagramDataからMermaid記法（graph TD）を生成する。
"""

from __future__ import annotations

import logging
from typing import Dict, List

from .models import CaseSystemDiagram, DependencyRelation, SystemComponent, SystemDiagramData

logger = logging.getLogger(__name__)


class MermaidBuilder:
    """Mermaid記法ビルダー"""

    def build(self, diagram_data: SystemDiagramData) -> str:
        lines: List[str] = ["graph TD"]

        for case_idx, case in enumerate(diagram_data.cases):
            subgraph_lines = self._build_subgraph(case, case_idx)
            lines.extend(subgraph_lines)

        lines.append("")

        for case_idx, case in enumerate(diagram_data.cases):
            relation_lines = self._build_relations(case, case_idx)
            lines.extend(relation_lines)

        return "\n".join(lines)

    def _build_subgraph(self, case: CaseSystemDiagram, case_idx: int) -> List[str]:
        lines: List[str] = []

        system_name = self._extract_system_name(case.case_name)
        lines.append(f'    subgraph System["{system_name}"]')
        lines.append("        direction TB")

        layers = self._group_by_layer(case.components)

        if layers:
            for layer_name, components in layers.items():
                lines.append(f'        subgraph "{layer_name}"')
                for component in components:
                    node_id = self._generate_node_id(case_idx, case.components.index(component))
                    node_line = self._build_node(node_id, component)
                    lines.append(f'            {node_line}')
                lines.append("        end")
        else:
            for comp_idx, component in enumerate(case.components):
                node_id = self._generate_node_id(case_idx, comp_idx)
                node_line = self._build_node(node_id, component)
                lines.append(f"        {node_line}")

        lines.append("    end")
        lines.append("")

        return lines

    def _group_by_layer(self, components: List[SystemComponent]) -> Dict[str, List[SystemComponent]]:
        layers: Dict[str, List[SystemComponent]] = {}

        for component in components:
            layer_name = component.layer or "その他"
            if layer_name not in layers:
                layers[layer_name] = []
            layers[layer_name].append(component)

        if len(layers) == 1 and "その他" in layers:
            return {}

        return layers

    def _build_node(self, node_id: str, component: SystemComponent) -> str:
        display_name = self._simplify_system_name(component.name)

        parts = [display_name]

        if component.technology:
            parts.append(f"({component.technology})")

        for resp in component.responsibilities[:3]:
            resp_simplified = self._to_noun_phrase(resp)
            if len(resp_simplified) > 40:
                resp_simplified = resp_simplified[:37] + "..."
            parts.append(f"・{resp_simplified}")

        label = "<br/>".join(parts)
        return f'{node_id}["{label}"]'

    def _simplify_system_name(self, name: str) -> str:
        name = name.replace("層", "").replace("サービス", "")
        return name.strip()

    def _to_noun_phrase(self, text: str) -> str:
        text = text.replace("する", "").replace("します", "")
        text = text.replace("実装", "").replace("対応", "")
        text = text.replace("構築", "").replace("設定", "")

        if "：" in text:
            text = text.split("：")[0]
        if ":" in text:
            text = text.split(":")[0]

        return text.strip()

    def _extract_system_name(self, case_name: str) -> str:
        if "システム" in case_name:
            if "向け" in case_name:
                after_muke = case_name.split("向け")[1]
                system_part = after_muke.split("システム")[0] + "システム"
                return system_part.strip()
            before_system = case_name.split("システム")[0]
            words = before_system.split()
            if words:
                return words[-1] + "システム"
        return case_name

    def _build_relations(self, case: CaseSystemDiagram, case_idx: int) -> List[str]:
        lines: List[str] = []

        name_to_node_id: Dict[str, str] = {}
        for comp_idx, component in enumerate(case.components):
            node_id = self._generate_node_id(case_idx, comp_idx)
            name_to_node_id[component.name] = node_id

        for relation in case.relations:
            from_id = name_to_node_id.get(relation.from_system)
            to_id = name_to_node_id.get(relation.to_system)

            if from_id and to_id:
                arrow_line = f'    {from_id} -->|{relation.process_description}| {to_id}'
                lines.append(arrow_line)
            else:
                logger.warning(
                    "Cannot create relation: %s -> %s (node IDs not found)",
                    relation.from_system,
                    relation.to_system,
                )

        return lines

    def _generate_node_id(self, case_idx: int, component_idx: int) -> str:
        case_letter = chr(65 + case_idx)
        return f"{case_letter}{component_idx + 1}"
