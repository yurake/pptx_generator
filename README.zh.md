<div align="center">
  <p>
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="assets/pptx_generator_logo_black.png">
      <source media="(prefers-color-scheme: light)" srcset="assets/pptx_generator_logo_white.png">
      <img src="assets/pptx_generator_logo_white.png" alt="PPTX GENERATOR">
    </picture>
  </p>

  <p>
    <a href="LICENSE"><img src="https://img.shields.io/github/license/yurake/pptx_generator" alt="许可证"></a>
    <a href="https://github.com/yurake/pptx_generator/actions/workflows/ci.yml"><img src="https://github.com/yurake/pptx_generator/actions/workflows/ci.yml/badge.svg" alt="持续集成状态"></a>
    <img src="https://img.shields.io/badge/python-3.12-blue" alt="Python 3.12">
  </p>

<p>
  <a href="https://sonarcloud.io/project/overview?id=yurake_pptx_generator"><img src="https://img.shields.io/sonar/quality_gate/yurake_pptx_generator?server=https%3A%2F%2Fsonarcloud.io" alt="SonarCloud 质量门槛"></a>
  <a href="https://sonarcloud.io/project/overview?id=yurake_pptx_generator"><img src="https://img.shields.io/sonar/coverage/yurake_pptx_generator?server=https%3A%2F%2Fsonarcloud.io" alt="SonarCloud 覆盖率"></a>
  <a href="https://sonarcloud.io/project/issues?resolved=false&amp;id=yurake_pptx_generator&amp;types=BUG"><img src="https://sonarcloud.io/api/project_badges/measure?project=yurake_pptx_generator&amp;metric=bugs" alt="SonarCloud 缺陷"></a>
  <a href="https://sonarcloud.io/project/issues?resolved=false&amp;id=yurake_pptx_generator&amp;types=VULNERABILITY"><img src="https://sonarcloud.io/api/project_badges/measure?project=yurake_pptx_generator&amp;metric=vulnerabilities" alt="SonarCloud 漏洞"></a>
  <a href="https://sonarcloud.io/project/issues?resolved=false&amp;id=yurake_pptx_generator&amp;types=CODE_SMELL"><img src="https://sonarcloud.io/api/project_badges/measure?project=yurake_pptx_generator&amp;metric=code_smells" alt="SonarCloud 代码异味"></a>
</p>

<p>
  <a href="https://sonarcloud.io/project/overview?id=yurake_pptx_generator"><img src="https://sonarcloud.io/api/project_badges/measure?project=yurake_pptx_generator&amp;metric=sqale_rating" alt="SonarCloud 可维护性"></a>
  <a href="https://sonarcloud.io/project/overview?id=yurake_pptx_generator"><img src="https://sonarcloud.io/api/project_badges/measure?project=yurake_pptx_generator&amp;metric=reliability_rating" alt="SonarCloud 可靠性"></a>
  <a href="https://sonarcloud.io/project/overview?id=yurake_pptx_generator"><img src="https://sonarcloud.io/api/project_badges/measure?project=yurake_pptx_generator&amp;metric=security_rating" alt="SonarCloud 安全评分"></a>
  <a href="https://sonarcloud.io/project/overview?id=yurake_pptx_generator"><img src="https://sonarcloud.io/api/project_badges/measure?project=yurake_pptx_generator&amp;metric=duplicated_lines_density" alt="SonarCloud 重复行密度"></a>
</p>

  <p>
  <a href="README.md"><img alt="日语" src="https://img.shields.io/badge/%F0%9F%87%AF%F0%9F%87%B5%E6%97%A5%E6%9C%AC%E8%AA%9E-white"></a>
  <a href="README.zh.md"><img alt="简体中文" src="https://img.shields.io/badge/%F0%9F%87%A8%F0%9F%87%B3%E4%B8%AD%E6%96%87%E7%89%88-white"></a>
  <a href="README.en.md"><img alt="英语" src="https://img.shields.io/badge/%F0%9F%87%BA%F0%9F%87%B8English-white"></a>
  </p>

<p>
这是一个 CLI 工具，用于导入 PowerPoint 模板和资料数据（纯文本、PDF 等），并生成符合模板的演示文稿。
</p>
</div>

## 概要
- 从模板 PPTX 中提取布局结构和品牌设置，并生成可复用的规格 JSON。
- 将提取的规格与资料数据结合，生成带有审计日志的 PPTX/PDF（可通过 LibreOffice 实现 PDF 转换）。

## 快速入门
1. 准备一个 Python 3.12 系的虚拟环境，并使用 `uv sync` 同步依赖。
2. 运行 `uv run --help` 以确认 CLI 入口点可用。
3. 执行生成流水线。

## 生成管线概览
### 动态生成 (dynamic mode)
使用从模板中提取的布局信息，将数据整理成临时幻灯片，在调整内容的顺序和排布的同时，可以多次重新输出，是一种灵活的模式。适合希望从数据灵活地创建幻灯片的场景。

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

| 阶段 | 概述 | 命令示例 |
| --- | --- | --- |
| 1. 模板 | 提取并验证模板 PPTX，将 `jobspec.json` 等基础数据输出到 `.pptx/extract/` | `uv run pptx template samples/templates/templates.pptx --layout-mode dynamic` |
| 2. 内容准备 | 将输入资料规范化为临时幻灯片，并生成带有 AI 日志和审计信息的草稿 | `uv run pptx prepare samples/contents/sample_import_content_summary.txt` |
| 3. 映射 | 进行 HITL 审批与布局分配，并创建 `.pptx/compose/generate_ready.json` | `uv run pptx compose .pptx/extract/jobspec.json --prepare-cards .pptx/prepare/prepare_card.json` |
| 4. PPTX 生成 | 使用 `generate_ready.json` 输出 PPTX/PDF 和审计日志 | `uv run pptx gen .pptx/compose/generate_ready.json` |

### 静态生成（静态模式）
这是根据模板设定的幻灯片结构自动分配资料数据并完成制作的模式。在幻灯片的布局和规则已确定的场景中很有用。

在静态模式中出现的结构具有如下所示的层级。

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

| 阶段 | 概述 | 命令示例 |
| --- | --- | --- |
| 1. 模板 | 将蓝图信息与 `.pptx/extract/prompts/`（提示词模板）和 `.pptx/slide_inputs.md`（幻灯片输入清单）一起输出 | `uv run pptx template samples/templates/templates.pptx --layout-mode static` |
| 2. 内容准备 | 模板 (`.pptx/extract/prompts/01_*.md`) 与输入清单 (`.pptx/slide_inputs.md`) 编辑；如有需要，可以省略 `<data file path>`，以符合 Blueprint 的 Slot 定义对占位幻灯片进行整理 | `uv run pptx prepare --mode static` |
| 3. 映射 | 在验证 Slot 满足状况的同时生成 `generate_ready.json` | `uv run pptx compose .pptx/extract/jobspec.json --static` |
| 4. PPTX 生成 | 以固定布局输出 PPTX/PDF | `uv run pptx gen .pptx/compose/generate_ready.json` |

- 静态模板中，提供 `external/<template_id>/hooks.json` 时，可以将各阶段的处理委托给外部钩子。详细的设置示例以及传递的环境变量，请参考 `docs/design/stages/` 的各阶段文档。

各阶段的 CLI 命令及主要选项，请参阅 `docs/design/cli/cli-command-reference.md`。

## 测试
- 测试执行:
  ```bash
  uv run --extra dev pytest
  ```
- 测试完成后，请检查 `.pptx/compose/`、`.pptx/gen/` 等输出目录，确认是否生成了预期的产物。
- 详细的测试方针请参考 `tests/AGENTS.md`。

## 文档指南
- `AGENTS.md`: 编码代理应遵守的通用规则及相关文档链接。
- `docs/README.md`: `docs/` 目录下的分类与详细资料的导航。
- `docs/requirements/requirements.md`: 当前的业务/功能需求。
- `docs/design/design.md`: 四阶段流水线和主要组件的设计概览。
- `docs/runbooks/runbooks.md`: 运维、发布、故障排除等的操作手册。
- `docs/policies/policies.md`: 汇总政策文档全体的更新步骤与参照顺序的索引。
- `tests/AGENTS.md`: 各测试层级的附加规则与用例设计指南。

## 支持与咨询
- 有关发布、支持、故事骨架运用等，具体步骤请参考位于 `docs/runbooks/` 下的各自步骤。

## 许可证
- 本项目在 MIT 许可证下提供。详情请参阅 `LICENSE`。
