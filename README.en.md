<div align="center">
  <p>
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="docs/assets/pptx_generator_logo_black.png">
      <source media="(prefers-color-scheme: light)" srcset="docs/assets/pptx_generator_logo_white.png">
      <img src="docs/assets/pptx_generator_logo_white.png" alt="PPTX GENERATOR">
    </picture>
  </p>

  <p>
    <a href="LICENSE"><img src="https://img.shields.io/github/license/yurake/pptx_generator" alt="License"></a>
    <a href="https://github.com/yurake/pptx_generator/actions/workflows/ci.yml"><img src="https://github.com/yurake/pptx_generator/actions/workflows/ci.yml/badge.svg" alt="CI Status"></a>
    <img src="https://img.shields.io/badge/python-3.12-blue" alt="Python 3.12">
  </p>

<p>
  <a href="https://sonarcloud.io/project/overview?id=yurake_pptx_generator"><img src="https://img.shields.io/sonar/quality_gate/yurake_pptx_generator?server=https%3A%2F%2Fsonarcloud.io" alt="SonarCloud Quality Gate"></a>
  <a href="https://sonarcloud.io/project/overview?id=yurake_pptx_generator"><img src="https://img.shields.io/sonar/coverage/yurake_pptx_generator?server=https%3A%2F%2Fsonarcloud.io" alt="SonarCloud Coverage"></a>
  <a href="https://sonarcloud.io/project/issues?resolved=false&amp;id=yurake_pptx_generator&amp;types=BUG"><img src="https://sonarcloud.io/api/project_badges/measure?project=yurake_pptx_generator&amp;metric=bugs" alt="SonarCloud Bugs"></a>
  <a href="https://sonarcloud.io/project/issues?resolved=false&amp;id=yurake_pptx_generator&amp;types=VULNERABILITY"><img src="https://sonarcloud.io/api/project_badges/measure?project=yurake_pptx_generator&amp;metric=vulnerabilities" alt="SonarCloud Vulnerabilities"></a>
  <a href="https://sonarcloud.io/project/issues?resolved=false&amp;id=yurake_pptx_generator&amp;types=CODE_SMELL"><img src="https://sonarcloud.io/api/project_badges/measure?project=yurake_pptx_generator&amp;metric=code_smells" alt="SonarCloud Code Smells"></a>
</p>

  <p>
    <a href="https://sonarcloud.io/project/overview?id=yurake_pptx_generator"><img src="https://sonarcloud.io/api/project_badges/measure?project=yurake_pptx_generator&amp;metric=sqale_rating" alt="SonarCloud Maintainability"></a>
    <a href="https://sonarcloud.io/project/overview?id=yurake_pptx_generator"><img src="https://sonarcloud.io/api/project_badges/measure?project=yurake_pptx_generator&amp;metric=reliability_rating" alt="SonarCloud Reliability"></a>
    <a href="https://sonarcloud.io/project/overview?id=yurake_pptx_generator"><img src="https://sonarcloud.io/api/project_badges/measure?project=yurake_pptx_generator&amp;metric=security_rating" alt="SonarCloud Security Rating"></a>
    <a href="https://sonarcloud.io/project/overview?id=yurake_pptx_generator"><img src="https://sonarcloud.io/api/project_badges/measure?project=yurake_pptx_generator&amp;metric=duplicated_lines_density" alt="SonarCloud Duplicated Lines"></a>
  </p>

<p>
<a href="README.md"><img alt="Japanese" src="https://img.shields.io/badge/%F0%9F%87%AF%F0%9F%87%B5%E6%97%A5%E6%9C%AC%E8%AA%9E-white"></a>
<a href="README.zh.md"><img alt="Chinese" src="https://img.shields.io/badge/%F0%9F%87%A8%F0%9F%87%B3%E4%B8%AD%E6%96%87%E7%89%88-white"></a>
<a href="README.en.md"><img alt="English" src="https://img.shields.io/badge/%F0%9F%87%BA%F0%9F%87%B8English-white"></a>
</p>

<p>
This CLI tool ingests PowerPoint templates and data assets (plain text, PDFs, etc.) and generates presentation materials that conform to the template.
</p>
</div>

## Overview
- Extract the layout structure and brand settings from the template PPTX, and generate a reusable specification JSON.
- Combine the extracted specifications with the document data to generate PPTX/PDF with an audit log (PDF conversion is also possible using LibreOffice).

## Quick Start
1. Create a Python 3.12 virtual environment and synchronize dependencies with `uv sync`.
2. Run `uv run --help` to verify that the CLI entry point is available.
3. Run the generation pipeline.

## Generation pipeline overview
### Dynamic generation (dynamic mode)
This flexible mode uses layout information extracted from templates to assemble the document data into provisional slides, and allows you to repeatedly regenerate slides by adjusting the content order and placement. It is suited for flexibly creating slides from document data.

```mermaid
flowchart TD
  %% ======= Styles =======
  classDef stage fill:#e0f2fe,stroke:#0284c7,stroke-width:2px,color:#0c4a6e,font-weight:bold;
  classDef file fill:#f3f4f6,stroke:#4b5563,stroke-width:1px,color:#111827,font-weight:bold;
  classDef userfile fill:#dcfce7,stroke:#16a34a,stroke-width:2px,color:#064e3b,font-weight:bold;
  classDef final fill:#fef9c3,stroke:#eab308,stroke-width:2px,color:#78350f,font-weight:bold;

  %% ======= Stage 1 =======
  Tmpl["**テンプレートPPTX (templates.pptx)**"]:::userfile --> S1["**stage 1 テンプレ**"]:::stage
  S1 --> Jobspec["**テンプレ仕様(jobspec.json)**"]:::file

  %% ======= Stage 2 =======
  Prepare["**資料データ (prepare_source.md / .json)**"]:::userfile --> S2["**stage 2 コンテンツ準備**"]:::stage
  S2 --> PrepareCards["**ドラフト(prepare_card.json)**"]:::file
  PrepareCards --> S3

  %% ======= Stage 3 =======
  S3["**stage 3 マッピング**"]:::stage
  Jobspec --> S3
  S3 --> Ready["**パワポ.json (generate_ready.json)**"]:::file

  %% ======= Stage 4 =======
  Ready --> S4["**stage 4 PPTX生成**"]:::stage
  S4 --> PPTX["**proposal.pptx**"]:::final

  %% ======= Legend =======
  subgraph Legend[凡例]
    direction LR
    A1["**stage（自動/HITL）**"]:::stage
    A2["**システム生成ファイル**"]:::file
    A3["**ユーザー準備ファイル**"]:::userfile
    A4["**最終成果物**"]:::final
  end
```

| stage | Overview | Example command |
| --- | --- | --- |
| 1. Template | Extract and validate the template PPTX, and output foundational data such as `jobspec.json` to `.pptx/template/` | `uv run pptx template samples/templates/templates.pptx --mode dynamic` |
| 2. Content Preparation | Normalize the input materials into draft slides and generate a draft with AI logs and audit information | `uv run pptx prepare samples/input/pitch.md` |
| 3. Mapping | Perform HITL approval and layout assignment, creating `.pptx/compose/generate_ready.json` | `uv run pptx compose .pptx/template/jobspec.json --prepare-cards .pptx/prepare/prepare_card.json` |
| 4. PPTX Generation | Output PPTX/PDF and audit logs using `generate_ready.json` | `uv run pptx gen .pptx/compose/generate_ready.json` |

### Static generation (static mode)
This mode automatically assigns and assembles slide data according to the slide structure defined by the template. It is useful in cases where slide layout and rules are predefined.

The structures that appear in static mode are organized in the following hierarchy.

```
Blueprint（テンプレ全体の設計図）
└─ Slide（スライドごとの枠組み）
    └─ Slot（コンテンツ差し込み枠）
```

```mermaid
flowchart TD
  %% ======= Styles =======
  classDef stage fill:#e0f2fe,stroke:#0284c7,stroke-width:2px,color:#0c4a6e,font-weight:bold;
  classDef file fill:#f3f4f6,stroke:#4b5563,stroke-width:1px,color:#111827,font-weight:bold;
  classDef userfile fill:#dcfce7,stroke:#16a34a,stroke-width:2px,color:#064e3b,font-weight:bold;
  classDef final fill:#fef9c3,stroke:#eab308,stroke-width:2px,color:#78350f,font-weight:bold;

  %% ======= Stage 1 =======
  TmplStatic["**テンプレートPPTX (templates.pptx)**"]:::userfile --> S1Static["**stage 1 テンプレ**"]:::stage
  S1Static --> SpecStatic["**テンプレ仕様(jobspec.json)**<br/>**テンプレ構造(template_spec.json)**"]:::file

  %% ======= Stage 2 =======
  PrepareStatic["**資料データ (prepare_source.md / .json)**"]:::userfile --> S2Static["**stage 2 コンテンツ準備 (Slot 生成)**"]:::stage
  SpecStatic --> S2Static
  S2Static --> PrepareCardsStatic["**ドラフト(prepare_card.json)**"]:::file
  PrepareCardsStatic --> S3Static

  %% ======= Stage 3 =======
  S3Static["**stage 3 マッピング (Blueprint 検証)**"]:::stage
  SpecStatic --> S3Static
  S3Static --> ReadyStatic["**パワポ.json (generate_ready.json)**"]:::file

  %% ======= Stage 4 =======
  ReadyStatic --> S4Static["**stage 4 PPTX生成**"]:::stage
  S4Static --> PPTXStatic["**proposal.pptx**"]:::final

  %% ======= Legend =======
  subgraph LegendStatic[凡例]
    direction LR
    B1["**stage（自動/HITL）**"]:::stage
    B2["**テンプレ仕様 / 構造ファイル**"]:::file
    B3["**ユーザー準備ファイル**"]:::userfile
    B4["**最終成果物**"]:::final
  end
```

| Stage | Overview | Example command |
| --- | --- | --- |
| 1. Template | Output the Blueprint information along with `.pptx/template/prompts/` (prompt templates) and `.pptx/slide_inputs.md` (slide input manifest) | `uv run pptx template samples/templates/templates.pptx --mode static` |
| 2. Content Preparation | Edit the template (`.pptx/template/prompts/01_*.md`) and the input manifest (`.pptx/slide_inputs.md`), and, if needed, omit `<data file path>` to shape provisional slides in accordance with the Blueprint Slot definitions | `uv run pptx prepare --mode static` |
| 3. Mapping | Generate `generate_ready.json` while validating slot fulfillment | `uv run pptx compose .pptx/template/jobspec.json --static` |
| 4. PPTX Generation | Output PPTX/PDF with a fixed layout | `uv run pptx gen .pptx/compose/generate_ready.json` |

- In static templates, providing `external/<template_id>/hooks.json` allows delegating per-stage processing to external hooks. For installation and operation procedures, refer to `external/README.md`; for agent guidelines, refer to `external/AGENTS.md`. For detailed configuration examples and the environment variables that will be passed, refer to the stage documents under `docs/design/stages/`.

The CLI commands for each stage and their main options are in `docs/design/cli/cli-command-reference.md`.

## Test
- Run tests:
  ```bash
  uv run --extra dev pytest
  ```
- After tests, check the output directories such as `.pptx/compose/` and `.pptx/gen/` to confirm that the expected artifacts have been generated.
- For detailed testing guidelines, refer to `tests/AGENTS.md`.

## Documentation Guide
- `AGENTS.md`: Common rules that coding agents must follow and links to related documentation.
- `docs/README.md`: Navigation to categories under `docs/` and detailed materials.
- `docs/requirements/requirements.md`: Current business/functional requirements.
- `docs/design/design.md`: Design overview of the 4-stage pipeline and major components.
- `docs/runbooks/runbooks.md`: Procedures for operations, releases, troubleshooting, and related tasks.
- `docs/policies/policies.md`: An index summarizing the update procedures and reference order for the policy documents as a whole.
- `tests/AGENTS.md`: Guidelines for additional rules per testing level and test-case design guidance.

## Support and Inquiries
- For release, support, and story-skeleton operations, as well as other procedures, please refer to the items under `docs/runbooks/`.

## License
- This project is provided under the MIT License. For details, please refer to `LICENSE`.
