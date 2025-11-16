"""pptx_generator CLI."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
from importlib import resources as importlib_resources
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import click
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE, PP_PLACEHOLDER

from .branding_extractor import (BrandingExtractionError,
                                 extract_branding_config)
from .brief import (BriefAIOrchestrationError, BriefAIOrchestrator,
                    BriefDocument, BriefPolicyError, BriefSourceDocument,
                    load_brief_policy_set)
from .draft_intel import load_return_reasons
from .generate_ready import generate_ready_to_jobspec
from .layout_validation import (LayoutValidationError, LayoutValidationOptions,
                                LayoutValidationResult, LayoutValidationSuite)
from .models import (ContentApprovalDocument, DraftDocument,
                     GenerateReadyDocument, JobSpec, JobSpecScaffold,
                     SpecValidationError, TemplateRelease,
                     TemplateReleaseDiagnostics, TemplateReleaseGoldenRun,
                     TemplateReleaseReport, TemplateSpec)
from .pipeline import (AnalyzerOptions, BriefNormalizationError,
                       BriefNormalizationOptions, BriefNormalizationStep,
                       ContentApprovalOptions, ContentApprovalStep,
                       DraftStructuringOptions, DraftStructuringStep,
                       MappingOptions, MappingStep,
                       MonitoringIntegrationOptions, MonitoringIntegrationStep,
                       PdfExportError, PdfExportOptions, PdfExportStep,
                       PipelineContext, PipelineRunner, PipelineStep,
                       PolisherError, PolisherOptions, PolisherStep,
                      RefinerOptions, RenderingAuditOptions,
                      RenderingAuditStep, RenderingOptions,
                      SimpleAnalyzerStep, SimpleRefinerStep,
                      SimpleRendererStep, SpecValidatorStep,
                      TemplateExtractor, TemplateExtractorOptions)
from .pipeline.analyzer import SlideSnapshot
from .spec_loader import load_jobspec_from_path
from .pipeline.draft_structuring import DraftStructuringError
from .review_engine import AnalyzerReviewEngineAdapter
from .settings import BrandingConfig, RulesConfig
from .template_audit import (build_release_report, build_template_release,
                             load_template_release)

DEFAULT_RULES_PATH = Path("config/rules.json")
DEFAULT_BRANDING_PATH = Path("config/branding.json")
DEFAULT_CHAPTER_TEMPLATES_DIR = Path("config/chapter_templates")
DEFAULT_RETURN_REASONS_PATH = Path("config/return_reasons.json")
DEFAULT_BRIEF_POLICY_PATH = Path("config/brief_policies/default.json")
DEFAULT_PREPARE_OUTPUT_DIR = Path(".pptx/prepare")

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class OutlineResult:
    """アウトライン工程の実行結果。"""

    context: PipelineContext
    draft_path: Path
    approved_path: Path
    log_path: Path
    meta_path: Path
    generate_ready_path: Path
    generate_ready_meta_path: Path


_DEFAULT_DRAFT_OPTIONS = DraftStructuringOptions()
DEFAULT_DRAFT_FILENAME = _DEFAULT_DRAFT_OPTIONS.draft_filename
DEFAULT_APPROVED_FILENAME = _DEFAULT_DRAFT_OPTIONS.approved_filename
DEFAULT_DRAFT_LOG_FILENAME = _DEFAULT_DRAFT_OPTIONS.log_filename
DEFAULT_GENERATE_READY_FILENAME = _DEFAULT_DRAFT_OPTIONS.generate_ready_filename
DEFAULT_GENERATE_READY_META_FILENAME = _DEFAULT_DRAFT_OPTIONS.generate_ready_meta_filename
DEFAULT_DRAFT_META_FILENAME = "draft_meta.json"


discover-template-ai-policy
load_dotenv()


def _discover_template_ai_policy() -> Path | None:
    """Return the default template AI policy path if available."""

    candidates: list[Path] = []

    cwd_candidate = Path.cwd() / "config" / "template_ai_policies.json"
    if cwd_candidate.exists():
        candidates.append(cwd_candidate.resolve())

    repo_candidate = Path(__file__).resolve().parents[2] / "config" / "template_ai_policies.json"
    if repo_candidate.exists():
        candidates.append(repo_candidate.resolve())

    # If running from an installed package, resource lookup may succeed
    try:
        resource = importlib_resources.files("pptx_generator").joinpath("config/template_ai_policies.json")
        if resource.is_file():
            with importlib_resources.as_file(resource) as resource_path:
                candidates.append(resource_path.resolve())
    except (ModuleNotFoundError, FileNotFoundError):
        pass

    for candidate in candidates:
        if candidate.exists():
            logger.info("Detected default template AI policy: %s", candidate)
            return candidate
    return None


def _configure_llm_logger() -> None:
    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    llm_logger = logging.getLogger("pptx_generator.content_ai.llm")
    if not any(isinstance(h, logging.FileHandler) and getattr(h, "baseFilename", None) == str(log_dir / "out.log") for h in llm_logger.handlers):
        handler = logging.FileHandler(log_dir / "out.log", encoding="utf-8")
        formatter = logging.Formatter(
            fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        )
        handler.setFormatter(formatter)
        llm_logger.addHandler(handler)
    llm_logger.setLevel(logging.INFO)
    llm_logger.propagate = False


[... truncated due to length ...]