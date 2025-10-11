"""TemplateExtractor の単体テスト。"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from pptx_generator.models import LayoutInfo, ShapeInfo, TemplateSpec
from pptx_generator.pipeline.template_extractor import (
    SLIDE_BULLET_ANCHORS,
    TemplateExtractor,
    TemplateExtractorOptions,
    TemplateExtractorStep,
)


class TestTemplateExtractorOptions:
    """TemplateExtractorOptions のテスト。"""

    def test_default_values(self) -> None:
        """デフォルト値のテスト。"""
        template_path = Path("test.pptx")
        options = TemplateExtractorOptions(template_path=template_path)
        
        assert options.template_path == template_path
        assert options.output_path is None
        assert options.layout_filter is None
        assert options.anchor_filter is None
        assert options.format == "json"

    def test_custom_values(self) -> None:
        """カスタム値のテスト。"""
        template_path = Path("test.pptx")
        output_path = Path("output.json")
        
        options = TemplateExtractorOptions(
            template_path=template_path,
            output_path=output_path,
            layout_filter="Layout1",
            anchor_filter="anchor1",
            format="yaml",
        )
        
        assert options.template_path == template_path
        assert options.output_path == output_path
        assert options.layout_filter == "Layout1"
        assert options.anchor_filter == "anchor1"
        assert options.format == "yaml"


class TestTemplateExtractorStep:
    """TemplateExtractorStep のテスト。"""

    @pytest.fixture
    def mock_presentation(self):
        """モックプレゼンテーションを作成。"""
        presentation = Mock()
        
        # レイアウトのモック
        layout1 = Mock()
        layout1.name = "タイトルスライド"
        
        # 図形のモック
        shape1 = Mock()
        shape1.name = "タイトル"
        shape1.left = 914400  # 1インチ
        shape1.top = 1828800  # 2インチ
        shape1.width = 9144000  # 10インチ
        shape1.height = 914400  # 1インチ
        shape1.__class__.__name__ = "SlidePlaceholder"
        shape1.text_frame = Mock()
        shape1.text_frame.text = "タイトルをここに入力"
        shape1.placeholder_format = Mock()
        shape1.placeholder_format.type = "TITLE"
        
        shape2 = Mock()
        shape2.name = "サブタイトル"
        shape2.left = 914400
        shape2.top = 3657600  # 4インチ
        shape2.width = 9144000
        shape2.height = 914400
        shape2.__class__.__name__ = "SlidePlaceholder"
        shape2.text_frame = Mock()
        shape2.text_frame.text = "サブタイトルをここに入力"
        shape2.placeholder_format = Mock()
        shape2.placeholder_format.type = "SUBTITLE"
        
        layout1.shapes = [shape1, shape2]
        
        presentation.slide_layouts = [layout1]
        
        return presentation

    @pytest.fixture
    def temp_template_path(self):
        """一時テンプレートファイルパス。"""
        with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as f:
            temp_path = Path(f.name)
        temp_path.write_text("dummy pptx content")
        yield temp_path
        temp_path.unlink()

    def test_extract_template_spec_success(self, temp_template_path, mock_presentation):
        """正常なテンプレート抽出のテスト。"""
        options = TemplateExtractorOptions(template_path=temp_template_path)
        step = TemplateExtractorStep(options)
        
        with patch('pptx_generator.pipeline.template_extractor.Presentation') as mock_pres_class:
            mock_pres_class.return_value = mock_presentation
            
            template_spec = step.extract_template_spec()
            
            assert isinstance(template_spec, TemplateSpec)
            assert template_spec.template_path == str(temp_template_path)
            assert len(template_spec.layouts) == 1
            
            layout = template_spec.layouts[0]
            assert layout.name == "タイトルスライド"
            assert len(layout.anchors) == 2
            
            # 最初の図形
            shape1 = layout.anchors[0]
            assert shape1.name == "タイトル"
            assert shape1.shape_type == "SlidePlaceholder"
            assert shape1.left_in == 1.0
            assert shape1.top_in == 2.0
            assert shape1.width_in == 10.0
            assert shape1.height_in == 1.0
            assert shape1.text == "タイトルをここに入力"
            assert shape1.placeholder_type == "TITLE"
            assert shape1.is_placeholder is True
            
            # 2番目の図形
            shape2 = layout.anchors[1]
            assert shape2.name == "サブタイトル"
            assert shape2.top_in == 4.0

    def test_extract_template_spec_file_not_found(self):
        """存在しないファイルのテスト。"""
        non_existent_path = Path("non_existent.pptx")
        options = TemplateExtractorOptions(template_path=non_existent_path)
        step = TemplateExtractorStep(options)
        
        with pytest.raises(FileNotFoundError):
            step.extract_template_spec()

    def test_extract_template_spec_invalid_file(self, temp_template_path):
        """不正なファイルのテスト。"""
        options = TemplateExtractorOptions(template_path=temp_template_path)
        step = TemplateExtractorStep(options)
        
        with patch('pptx_generator.pipeline.template_extractor.Presentation') as mock_pres_class:
            mock_pres_class.side_effect = Exception("Invalid PPTX file")
            
            with pytest.raises(RuntimeError, match="テンプレートファイルの読み込みに失敗しました"):
                step.extract_template_spec()

    def test_layout_filter(self, temp_template_path, mock_presentation):
        """レイアウトフィルタのテスト。"""
        options = TemplateExtractorOptions(
            template_path=temp_template_path,
            layout_filter="コンテンツ"  # 存在しないレイアウト名
        )
        step = TemplateExtractorStep(options)
        
        with patch('pptx_generator.pipeline.template_extractor.Presentation') as mock_pres_class:
            mock_pres_class.return_value = mock_presentation
            
            template_spec = step.extract_template_spec()
            
            # フィルタに一致しないため、レイアウトは0個
            assert len(template_spec.layouts) == 0

    def test_anchor_filter(self, temp_template_path, mock_presentation):
        """アンカーフィルタのテスト。"""
        options = TemplateExtractorOptions(
            template_path=temp_template_path,
            anchor_filter="タイトル"  # タイトル図形のみ抽出
        )
        step = TemplateExtractorStep(options)
        
        with patch('pptx_generator.pipeline.template_extractor.Presentation') as mock_pres_class:
            mock_pres_class.return_value = mock_presentation
            
            template_spec = step.extract_template_spec()
            
            assert len(template_spec.layouts) == 1
            layout = template_spec.layouts[0]
            assert len(layout.anchors) == 1  # タイトルのみ
            assert layout.anchors[0].name == "タイトル"

    def test_slide_bullet_conflict_detection(self):
        """SlideBullet競合検出のテスト。"""
        options = TemplateExtractorOptions(template_path=Path("dummy.pptx"))
        step = TemplateExtractorStep(options)
        
        # SlideBullet で使用される可能性のあるアンカー名の図形
        shape = Mock()
        shape.name = "bullets"  # SLIDE_BULLET_ANCHORS に含まれる
        shape.left = 914400
        shape.top = 914400
        shape.width = 914400
        shape.height = 914400
        shape.__class__.__name__ = "Rectangle"
        shape.text_frame = None
        
        shape_info = step._extract_shape_info(shape)
        
        assert shape_info.conflict is not None
        assert "SlideBullet拡張仕様で使用される可能性のあるアンカー名" in shape_info.conflict

    def test_missing_fields_detection(self):
        """必須フィールド欠落検出のテスト。"""
        options = TemplateExtractorOptions(template_path=Path("dummy.pptx"))
        step = TemplateExtractorStep(options)
        
        # 名前なし、サイズ不正の図形
        shape = Mock()
        shape.name = ""
        shape.left = 914400
        shape.top = 914400
        shape.width = 0  # 不正なサイズ
        shape.height = -1  # 不正なサイズ
        shape.__class__.__name__ = "Rectangle"
        shape.text_frame = None
        
        shape_info = step._extract_shape_info(shape)
        
        assert "name" in shape_info.missing_fields
        assert "width" in shape_info.missing_fields
        assert "height" in shape_info.missing_fields


class TestTemplateExtractor:
    """TemplateExtractor のテスト。"""

    @pytest.fixture
    def temp_template_path(self):
        """一時テンプレートファイルパス。"""
        with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as f:
            temp_path = Path(f.name)
        temp_path.write_text("dummy pptx content")
        yield temp_path
        temp_path.unlink()

    def test_extract_and_save_json(self, temp_template_path):
        """JSON形式での保存テスト。"""
        options = TemplateExtractorOptions(
            template_path=temp_template_path,
            format="json"
        )
        extractor = TemplateExtractor(options)
        
        # モックテンプレートスペック
        mock_template_spec = TemplateSpec(
            template_path=str(temp_template_path),
            extracted_at="2023-01-01T00:00:00Z",
            layouts=[],
        )
        
        with patch.object(extractor.step, 'extract_template_spec') as mock_extract:
            mock_extract.return_value = mock_template_spec
            
            with tempfile.TemporaryDirectory() as temp_dir:
                output_path = Path(temp_dir) / "test_output.json"
                result_path = extractor.extract_and_save(output_path)
                
                assert result_path == output_path
                assert output_path.exists()
                
                # ファイル内容確認
                content = output_path.read_text(encoding="utf-8")
                assert '"template_path"' in content
                assert str(temp_template_path) in content

    def test_extract_and_save_yaml(self, temp_template_path):
        """YAML形式での保存テスト。"""
        options = TemplateExtractorOptions(
            template_path=temp_template_path,
            format="yaml"
        )
        extractor = TemplateExtractor(options)
        
        # モックテンプレートスペック
        mock_template_spec = TemplateSpec(
            template_path=str(temp_template_path),
            extracted_at="2023-01-01T00:00:00Z",
            layouts=[],
        )
        
        with patch.object(extractor.step, 'extract_template_spec') as mock_extract:
            mock_extract.return_value = mock_template_spec
            
            with tempfile.TemporaryDirectory() as temp_dir:
                output_path = Path(temp_dir) / "test_output.yaml"
                result_path = extractor.extract_and_save(output_path)
                
                assert result_path == output_path
                assert output_path.exists()
                
                # ファイル内容確認
                content = output_path.read_text(encoding="utf-8")
                assert "template_path:" in content
                assert str(temp_template_path) in content


class TestConstants:
    """定数のテスト。"""

    def test_slide_bullet_anchors(self):
        """SLIDE_BULLET_ANCHORS 定数のテスト。"""
        expected_anchors = {"bullets", "bullet_list", "content", "body"}
        assert SLIDE_BULLET_ANCHORS == expected_anchors
        assert isinstance(SLIDE_BULLET_ANCHORS, set)
