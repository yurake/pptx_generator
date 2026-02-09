"""
システム依存関係図のデータモデル
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class SystemComponent(BaseModel):
    """システムコンポーネント"""

    name: str = Field(..., description="システム名")
    technology: Optional[str] = Field(None, description="技術例・製品名")
    dependencies: List[str] = Field(default_factory=list, description="依存先システム名のリスト")
    role: str = Field(..., description="役割・処理内容")
    case_id: str = Field(..., description="案件ID")
    layer: Optional[str] = Field(None, description="レイヤー名（APIゲートウェイ層、マイクロサービス層など）")
    responsibilities: List[str] = Field(default_factory=list, description="対応内容・実装項目のリスト")


class DependencyRelation(BaseModel):
    """依存関係"""

    from_system: str = Field(..., description="依存元システム名")
    to_system: str = Field(..., description="依存先システム名")
    process_description: str = Field(..., description="処理内容（矢印ラベル）")


class CaseSystemDiagram(BaseModel):
    """案件別システム構成図"""

    case_id: str = Field(..., description="案件ID")
    case_name: str = Field(..., description="案件名")
    components: List[SystemComponent] = Field(default_factory=list, description="システムコンポーネント一覧")
    relations: List[DependencyRelation] = Field(default_factory=list, description="依存関係一覧")


class SystemDiagramData(BaseModel):
    """全体のシステム構成図データ"""

    cases: List[CaseSystemDiagram] = Field(default_factory=list, description="案件別システム構成図一覧")
