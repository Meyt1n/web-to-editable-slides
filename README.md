# Web to Editable Slides

**在Codex里说清主题，由Codex自己设计提示词、调用内置imagegen、看参考图，再生成可编辑PPT。**

这是一个面向Codex、中文优先的开源Skill，默认在Codex本地桌面应用中使用。当前Codex直接负责视觉理解、按需提问、规划、逐页生图、模板提取、原生重建和导图验收；使用者给出主题与资料即可，不必先去网页版生图、另选视觉模型或准备API Key。

仓库自带通用`native_renderer.py`，从Codex整理的场景直接生成PPTX与自包含PPTD，支持文字、形状、自由曲线、图片、简单原生表格和柱形/折线/散点图，不要求额外PPTD/WASM后端。`auto_deck.py`保存提示词、生图尝试、依赖哈希和验收记录，支持中断续跑。Codex读取任务的下一步动作并继续执行，脚本不单独调用模型或图像API。

[Codex执行约定](references/codex.md) · [自动执行说明](references/automation.md) · [原生后端能力与边界](references/native-scene.md) · [完整自动试跑](examples/auto-workshop/README.md)

现在也支持在原风格内优化字体搭配、表达方式与页面节奏：先按内容选结构，再做同一套设计语言中的变化。

字体库现有6款完整字库和5组搭配，并提供水墨、暖纸、安静技术三种分层背景配方、三张原创无字背景及可调用的标题/知识点/问答动画方案。可从既有PPT学习原生字体、图片字、背景层次与展开顺序，再用可编辑文字和独立素材实现。方法见[字体、背景与动画](references/art-direction.md)，实际效果见[五页能力小样](examples/style-lab/README.md)，背景参数与来源见[素材目录](assets/backgrounds/catalog.json)。

已有逐页参考时默认保留原页排版：结合对应提示词还原标题、图文比例、分栏、流程与字体层级。展示图片先查本地素材，需要时交给imagegen优化；本地缺图时，再复刻参考页里的授权图片局部。

![绿芽：完全虚构的示例主题](assets/reference-cover.png)

## 这套流程解决什么

逐页参考图能快速确定视觉方向，但整页PNG放入PowerPoint后，标题、正文、卡片和流程仍然无法分别编辑。本技能让当前Codex完成生图与重建：生成图作为它自己的设计依据，以原生文字、形状、流程、表格和独立图片构建幻灯片。

它不声称一键无损转换，也不保证像素级复刻。图片中的复杂插画保留为素材，内容与布局则尽量重建为可编辑对象。

## 完整流程

```mermaid
flowchart LR
    A[主题与资料] --> B[按需询问 · 自主规划]
    B --> C[Codex编写逐页提示词]
    C --> D[Codex调用内置imagegen]
    D --> E[Codex自己看图与纠偏]
    E --> F[提取模板 · 分离独立素材]
    F --> G[通用场景 · 仓库原生导出]
    G --> H[实际导图 · 对照修复]
    H --> I[PPTX · 完整源工程 · 预览与可编辑性报告]
    E -->|需要重生成| C
    H -->|需要修复| G
```

已有大纲或参考图时从对应步骤开始。设计与读图使用当前Codex模型，生图使用当前会话内置imagegen，不要求用户另配模型服务。复杂插画内部仍可能是位图，输出明确列出这些边界；不宣传所有笔画完全可编辑或所有播放器无差异。

## 先提取模板，再制作页面

新增正式的模板提取环节：从代表提示图中归纳配色、字体角色、网格和组件，整理成带ID与版本的模板包，先验证一张代表页，再让后续页面从同一模板派生。

模板包含参数、页型骨架、原生组件、必要背景与来源记录；它不只是一张底图。后续可改变图文比例与布局，同时沿用共同规则。

- [模板提取步骤](references/template-extraction.md)
- [从两张参考图到模板包的完整示例](examples/template-extraction/README.md)
- [实际模板规范](examples/template-extraction/template/TEMPLATE.md)
- [实际模板JSON](examples/template-extraction/template/template.json)

```text
使用 $web-to-editable-slides，先从这些提示图里提取一套模板。
把字体、配色、网格、组件和页型落成模板包，先检查一个代表页。
后面的页面按这套模板设计，不逐页重新猜风格；需要变化时使用模板变体。
```

## 保留每页排版，结合原提示词还原

模板统一共性，每页仍保留自己的骨架。重建前将参考图与该页提示词配对；重建后将实际渲染与参考图并排检查，核对标题位置、图文占比、列数、卡片数量、阅读顺序、字重、断行和留白。需要重新编排时，以用户明确允许的范围为准。

- [完整版首轮任务书与逐页提示词](references/prompts.md#1-最开始发给网页版的完整任务书)：从作品事实、附件、汇报目标到字体和排版要求。
- [参考图还原与图片处理](references/reference-fidelity.md)：本地图优化、参考图片局部复刻、精确UI与实拍证据的使用。
- [交接表新增字段](references/design-plan.md#逐页参考排版与图片计划)：记录该页提示词、布局约束、字体约束和图片处理计划。

```text
保留每页参考图的排版，并结合原提示词的字体和布局要求重建。
先找本地图，合适的直接用，需要改善时作为imagegen输入优化。
本地缺图时，对参考页中的授权照片或插画局部用imagegen复刻成独立素材。
每页导图后与原页并排核对，再给我可编辑文件。
```

## 使用

在Codex中调用已有安装器，将仓库根目录作为Skill安装：

```text
$skill-installer 从 https://github.com/Meyt1n/web-to-editable-slides 安装这个技能，技能位于仓库根目录。
```

或手动克隆到用户技能目录（不要覆盖已有目录）：

```bash
git clone https://github.com/Meyt1n/web-to-editable-slides.git ~/.agents/skills/web-to-editable-slides
```

已有安装保留原位置，避免建立同名副本；Codex的本地技能目录与发现规则见[OpenAI官方Skills文档](https://learn.chatgpt.com/docs/build-skills)。Skill读取脚本和素材，实际任务、`.venv`及`output/`放在当前Codex工作区。

默认只需描述主题，例如：

```text
使用 $web-to-editable-slides，做一套面向社区组织者的工作坊方案PPT。
约6页，用于现场讲解，风格温暖简洁。必要时集中问我少量问题。
由你设计每页提示词并调用imagegen，自己看图提取模板和重建，
导图检查后直接交付可编辑PPTX、完整源工程、预览和可编辑性说明。
```

已有逐页图片时按顺序附上，并发送：

```text
使用 $web-to-editable-slides。
这些图片是我在网页版生成的PPT参考稿，按附件顺序排列。
请结合我提供的关联对话或提示词导出，提取共性并做成真正可编辑的PPT。
沿用已经确认的风格；需要的图片可以使用imagegen生成。
优先从我指定的素材目录寻找实物照片和真实界面；允许基于实物优化。
正文、标题、编号、流程和表格尽量使用原生对象。
不要把整页图直接作为最终PPT。先检查预览，再给我PPTX和源工程。
```

关联对话不支持访问时，粘贴大纲和逐页提示词或提供导出的文字。不要为了让模型读取而公开私人聊天。

## 字体与排版优化

新增三组字体方案、14种按内容选择的布局，以及可运行的8页原生版式图册。标题、正文、数字、少量点缀分别设定角色；正文保持清晰，通过宋黑搭配、亲和短标题、字重、留白、分栏和图文比例丰富表现。

![八种布局与字体选型](examples/design-gallery/preview.jpg)

- [字体与视觉规则](references/design-system.md)：在忠实复刻、同风格优化和方向探索之间选择。
- [版式库](references/layout-library.md)：大图、开放分栏、对比、时间线、架构、主体标注、证据、矩阵、路线等。
- [8页可编辑图册](examples/design-gallery/demo/design-gallery.pptx) · [完整源工程](examples/design-gallery/demo/design-gallery.pptd)
- [设计计划字段与检查](references/design-plan.md)：提示无必要的连续重复和过多字体，不自动改变用户模板。

图册展示不同选型，正式稿应选定适合主题的一组字体与规则，避免逐页随机换风格。图册的字体来自OFL项目，附完整许可与来源记录；数字字体只处理它支持的字符。

```text
使用 $web-to-editable-slides，在原风格内优化字体和排版。
给标题、正文和数字明确分工，按每页重点切换图文、对比、流程、架构或章节留白。
改善无必要的连续卡片重复，不改作品事实，不为丰富版式编造数据。
```

## 可直接运行的示例

示例主题为**绿芽——桌面植物养护提醒系统**，全部为imagegen生成的虚构概念素材，不含真实用户项目、硬件实拍、APP截图、身份信息和私人对话。

- [示例输入与运行步骤](examples/green-sprout/README.md)
- [参考流程图](assets/reference-process.png)
- [可编辑PPT示例](examples/green-sprout/demo/green-sprout.pptx)
- [示例预览](examples/green-sprout/preview.jpg)
- [示例PPTD源工程](examples/green-sprout/demo/green-sprout.pptd)

本地准备Python 3.10+，运行：

```bash
python -m pip install -r requirements.txt
python scripts/inventory_images.py assets --output-dir output/inventory
python scripts/template_pack.py prepare examples/template-extraction/observations.json --source-dir . --output-dir output/template
python scripts/template_pack.py check output/template/template.json
python scripts/make_handoff.py examples/green-sprout/brief.json --output output/handoff.md
python scripts/build_demo.py --template output/template/template.json --output-dir output/green-sprout
python scripts/review_design_plan.py output/green-sprout/design-plan.json --require-template
python scripts/check_pptx.py output/green-sprout/green-sprout.pptx --require-fade --output output/pptx-report.json
python scripts/build_gallery.py --output-dir output/design-gallery
python scripts/review_design_plan.py output/design-gallery/design-plan.json --output output/design-review.json
python -m unittest discover -s tests -v
```

示例生成器离线运行，输出3页PPTX及配套PPTD；它按代码定义重建示例，**不自动识别任意参考图**。命令行重建版本默认不嵌字体；示例附带OFL字体，字体嵌入和实际播放应按所用软件验证。仓库中的交付示例另做了实开与字体检查，详见示例说明。

## 目录

| 文件 | 用途 |
|---|---|
| `SKILL.md` | 给模型加载的核心工作流 |
| `references/prompts.md` | 资料、大纲、风格、逐页生图、移交和修订提示词 |
| `references/handoff-schema.md` | 页码、素材和事实状态的交接规范 |
| `references/codex.md`、`automation.md` | Codex内置工具、运行时、工作区与自动执行约定 |
| `references/tools.md` | 关联对话、imagegen、素材检索、导出和验证能力说明 |
| `references/verification.md` | 原生可编辑性、字体、切换和实开检查 |
| `references/design-system.md`、`layout-library.md` | 字体角色、视觉变化与按内容选版式 |
| `references/design-plan.md` | 设计计划字段和建议式检查 |
| `references/template-extraction.md` | 提示图分析、模板包、代表页核对与后续模板复用 |
| `references/reference-fidelity.md` | 逐页图与提示词配对、保留排版字体、本地图优先与imagegen局部复刻 |
| `scripts/` | Codex环境预检、自动任务、通用原生导出、图片清点与PPTX检查 |
| `assets/` | 原创参考图、分层背景、独立配图与OFL字体库 |
| `examples/green-sprout/` | 一套不含私人素材的输入、提示词与实际输出 |
| `examples/design-gallery/` | 8种原生布局、三组字体方案及可复现工程 |
| `examples/template-extraction/` | 来源观测、可读取模板与按模板生成的例子 |
| `examples/auto-workshop/` | Codex自动设计、生图、纠偏、重建、验收及离线重放的实测 |

## Codex内置工具与本地依赖

默认由当前Codex模型看图并调用内置imagegen，按当前工具文档执行，不另建图像API服务或索取API Key。实际工具错误按当前Codex会话定位，保留已完成进度继续恢复。

桌面版先取得Codex提供的运行时，再由doctor选择依赖完整的解释器。Python依赖与任务放在用户活跃工作区；默认原生导出使用本仓库代码，PowerPoint等本机播放器用于实际导图验收。历史PPTD/WASM后端保留为可选实现，工具分工见[工具说明](references/tools.md)。

## 开源范围

原创脚本、技能说明和提示词采用 [MIT许可证](LICENSE)。示例自生成图片在维护者拥有或可许可的权利范围内同许可提供；字体单独适用SIL OFL 1.1，见 [第三方说明](THIRD_PARTY_NOTICES.md)。

欢迎用虚构或有授权的素材提交改进。请不要把真实用户资料、私人聊天链接、账号令牌或本机绝对路径提交到示例中。
