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
  This CLI tool ingests PowerPoint templates and material data (plain text, PDFs, etc.) to generate presentation materials that conform to the template.
  </p>
</div>

## Overview
- Extract the layout structure and brand settings from a template PPTX to generate a reusable specification JSON.
- Combine the extracted specifications with document data to generate PPTX/PDF with an audit log (PDF conversion is also possible via LibreOffice).

## Quick Start
1. Prepare a virtual environment for Python 3.12.x and sync dependencies with `uv sync`.
2. Run `uv run --help` to verify that the CLI entry point is available.
3. Run the generation pipeline.

## Generation Pipeline Overview
### Dynamic Generation (dynamic mode)
Using layout information extracted from the templates, it assembles the presentation data into provisional slides and, by adjusting the content order and placement, can be produced again and again—a flexible mode. It is suitable when you want to flexibly create slides from presentation data.

```mermaid
flowchart TD
  %% ======= Styles =======
  classDef stage fill:#e0f2fe,stroke:#0284c7,stroke-width:2px,color:#0c4a6e,font-weight:bold;
  classDef file fill:#f3f4f6,stroke:#4b5563,stroke-width:1px,color:#111827,font-weight:bold;
  classDef userfile fill:#dcfce7,stroke:#16a34a,stroke-width:2px,color:#064e3b,font-weight:bold;
  classDef final fill:#fef9c3,stroke:#eab308,stroke-width:2px,color:#78350f,font-weight:bold;

  %% ======= Stage 1 =======
  Tmpl["**Template PPTX (templates.pptx)**"]:::userfile --> S1["**Stage 1 Template**"]:::stage
  S1 --> Jobspec["**Template spec (jobspec.json)**"]:::file

  %% ======= Stage 2 =======
  Prepare["**Source data (prepare_source.md / .json)**"]:::userfile --> S2["**Stage 2 Content preparation**"]:::stage
  S2 --> PrepareCards["**Draft (prepare_card.json)**"]:::file
  PrepareCards --> S3

  %% ======= Stage 3 =======
  S3["**Stage 3 Mapping**"]:::stage
  Jobspec --> S3
  S3 --> Ready["**PPTX JSON (generate_ready.json)**"]:::file

  %% ======= Stage 4 =======
  Ready --> S4["**Stage 4 PPTX generation**"]:::stage
  S4 --> PPTX["**proposal.pptx**"]:::final

  %% ======= Legend =======
  subgraph Legend[Legend]
    direction LR
    A1["**Stage (automated/HITL)**"]:::stage
    A2["**System-generated files**"]:::file
    A3["**User-prepared files**"]:::userfile
    A4["**Final deliverables**"]:::final
  end
```

| Stage | Overview | Command examples |
| --- | --- | --- |
| 1. Template | Extract and validate the template PPTX, and output foundational data such as `jobspec.json` to `.pptx/template/` | `uv run pptx template samples/templates/templates.pptx --mode dynamic` |
| 2. Content preparation | Normalize input materials into tentative slides and generate a draft with AI logs and audit information | `uv run pptx prepare samples/input/pitch.md` |
| 3. Mapping | Perform HITL approval and layout assignment, creating `.pptx/compose/generate_ready.json` | `uv run pptx compose .pptx/template/jobspec.json --prepare-cards .pptx/prepare/prepare_card.json` |
| 4. PPTX Generation | Output PPTX/PDF and audit logs using `generate_ready.json` | `uv run pptx gen .pptx/compose/generate_ready.json` |

### Static generation (static mode)
A mode that automatically maps data to the slide structure defined by the template and produces the final output. It is useful when slide layout and rules are fixed.

The structures that appear in static mode are organized as follows.

```
Blueprint (overall template blueprint)
└─ Slide (per-slide frame)
    └─ Slot (content placeholder)
```

- For static templates, placing `external/<template_id>/hooks.json` lets you delegate each stage to external hooks. Configuration examples and the environment variables passed to hooks are documented under `docs/design/stages/`.

```mermaid
flowchart TD
  %% ======= Styles =======
  classDef stage fill:#e0f2fe,stroke:#0284c7,stroke-width:2px,color:#0c4a6e,font-weight:bold;
  classDef file fill:#f3f4f6,stroke:#4b5563,stroke-width:1px,color:#111827,font-weight:bold;
  classDef userfile fill:#dcfce7,stroke:#16a34a,stroke-width:2px,color:#064e3b,font-weight:bold;
  classDef final fill:#fef9c3,stroke:#eab308,stroke-width:2px,color:#78350f,font-weight:bold;

  %% ======= Stage 1 =======
  TmplStatic["**Template PPTX (templates.pptx)**"]:::userfile --> S1Static["**Stage 1 Template**"]:::stage
  S1Static --> SpecStatic["**Template spec (jobspec.json)**<br/>**Template structure (template_spec.json)**"]:::file

  %% ======= Stage 2 =======
  PrepareStatic["**Source data (prepare_source.md / .json)**"]:::userfile --> S2Static["**Stage 2 Content preparation (slot generation)**"]:::stage
  SpecStatic --> S2Static
  S2Static --> PrepareCardsStatic["**Draft (prepare_card.json)**"]:::file
  PrepareCardsStatic --> S3Static

  %% ======= Stage 3 =======
  S3Static["**Stage 3 Mapping (Blueprint validation)**"]:::stage
  SpecStatic --> S3Static
  S3Static --> ReadyStatic["**PPTX JSON (generate_ready.json)**"]:::file

  %% ======= Stage 4 =======
  ReadyStatic --> S4Static["**Stage 4 PPTX generation**"]:::stage
  S4Static --> PPTXStatic["**proposal.pptx**"]:::final

  %% ======= Legend =======
  subgraph LegendStatic[Legend]
    direction LR
    B1["**Stage (automated/HITL)**"]:::stage
    B2["**Template spec / structure files**"]:::file
    B3["**User-prepared files**"]:::userfile
    B4["**Final deliverables**"]:::final
  end
```

| stage | Overview | Command examples |
| --- | --- | --- |
| 1. Template | Output the Blueprint information together with `.pptx/template/prompts/` (prompt templates) and `.pptx/slide_inputs.md` (slide input manifest) | `uv run pptx template samples/templates/templates.pptx --mode static` |
| 2. Content preparation | Edit the template (`.pptx/template/prompts/01_*.md`) and the input manifest (`.pptx/slide_inputs.md`), and if necessary omit `<data file path>` to shape mock slides according to the Blueprint slot definitions | `uv run pptx prepare --mode static` |
| 3. Mapping | Validate slot fulfillment and generate `generate_ready.json` | `uv run pptx compose .pptx/template/jobspec.json --static` |
| 4. PPTX generation | Output PPTX/PDF with a fixed layout | `uv run pptx gen .pptx/compose/generate_ready.json` |

The CLI commands for each stage and their key options are in `docs/design/cli/cli-command-reference.md`.

## Tests
- Run tests:
  ```bash
  uv run --extra dev pytest
  ```
- After testing, verify that the output directories such as `.pptx/compose/` and `.pptx/gen/` contain the expected artifacts.
- For detailed testing policy, refer to `tests/AGENTS.md`.

## Documentation Guide
- `AGENTS.md`: Common rules that coding agents must follow and links to related documents.
- `docs/README.md`: Navigation to the categories under `docs/` and their detailed documentation.
- `docs/requirements/requirements.md`: Current business and functional requirements.
- `docs/design/design.md`: Design overview of the four-stage pipeline and major components.
- `docs/runbooks/runbooks.md`: Procedures for operations, releases, troubleshooting, and related tasks.
- `docs/policies/policies.md`: Index summarizing the update procedures and the reference order for policy documents.
- `tests/AGENTS.md`: Guidelines for additional rules per test level and test-case design.

## Support and Inquiries
- For individual procedures such as releases, support, and story-skeleton operations, please refer to the contents under `docs/runbooks/`.

## License
- This project is licensed under the MIT License. For details, please refer to `LICENSE`.
