# Web to Editable Slides

**面向 Codex 的自动 PPT 制作 Skill：给出主题，Codex 自己设计、生图、看图，再交付可编辑幻灯片。**

[![CI](https://github.com/Meyt1n/web-to-editable-slides/actions/workflows/validate.yml/badge.svg)](https://github.com/Meyt1n/web-to-editable-slides/actions/workflows/validate.yml) · [MIT](LICENSE) · [开始使用](#开始使用) · [实际效果](#实际效果) · [开发与验证](#开发与验证)

你描述用途、受众和主题，Codex 按需询问少量问题，随后自主规划内容、编写逐页提示词、调用内置 imagegen、查看生成结果、提取模板，并重建为原生文字、图形、表格和独立图片。

默认交付 **PPTX、完整源工程、实际预览和可编辑性报告**。已有参考图或 PPT 时，也可以直接从复刻、优化或局部修改开始。

![Codex 自动制作的四页「修补日」PowerPoint 实际预览](examples/auto-workshop/preview.jpg)

上图是实际 PowerPoint 导图。该例的提示词、生成参考图、一次纠偏重试、模板、场景与验收记录均保留在[完整试跑](examples/auto-workshop/README.md)中。

## 开始使用

在 Codex 中安装仓库根目录的 Skill：

```text
$skill-installer 从 https://github.com/Meyt1n/web-to-editable-slides 安装这个技能，技能位于仓库根目录。
```

安装后，直接描述你要做的 PPT：

```text
使用 $web-to-editable-slides，制作一套「社区修补工作坊」介绍PPT。
面向社区组织者，约6页，用于现场讲解，风格温暖简洁。
其他设计由你决定，必要时集中问我几个问题。
```

Codex 会继续完成提示词、生图、看图、模板提取、重建和检查。你不需要先去网页版生成图片、手工编写 JSON 或逐步运行脚本，也不用另配视觉模型或提供 API Key。

<details>
<summary>手动安装</summary>

也可以克隆到 Codex 的用户技能目录：

```bash
git clone https://github.com/Meyt1n/web-to-editable-slides.git ~/.agents/skills/web-to-editable-slides
```

已有安装保留原位置，避免建立同名副本。安装与发现规则见 [OpenAI 官方 Skills 文档](https://learn.chatgpt.com/docs/build-skills)。

</details>

## 三种使用方式

| 你提供什么 | Codex 会做什么 | 示例要求 |
|---|---|---|
| 主题、资料或大纲 | 规划方案，自己生成参考图，再重建与验收 | 「做一套6页的产品介绍，其他设计由你决定」 |
| 逐页参考图及原提示词（如有） | 提取共性模板，保留对应页的排版、字体层级与阅读顺序 | 「按附件顺序复刻，文字和流程尽量原生可编辑」 |
| 已有 PPT | 沿用现有风格修改、增页，或学习字体、背景与动画 | 「保持这份PPT的风格，补两页实施计划」 |

有明确参考时，默认保留其页面骨架；需要重新编排时按你授权的范围调整。已有实物照片、界面或数据时优先使用原始资料，生成素材与真实证据分别记录。

## 工作方式

```mermaid
flowchart LR
    A[主题与资料] --> B[Codex规划与提示词]
    B --> C[内置imagegen生成参考图]
    C --> D[Codex看图与模板提取]
    D --> E[原生重建]
    E --> F[实际导图与完整交付]
    D -->|需要纠偏| B
    F -->|需要修复| E
```

设计、视觉理解和工具调用由当前 Codex 完成；仓库脚本负责保存进度、准备字体、编译文件和检查依赖。任务中断后可以从已有结果续跑，提示词或参考图变化会使相关步骤失效，避免沿用过期结果。

仓库自带通用原生后端，直接从场景生成 PPTX 和自包含 PPTD，默认导出无需额外的 PPTD/WASM 插件。Codex 优先发现桌面版提供的运行时，再选择依赖完整的工作区环境；任务、依赖和产物都放在活跃工作区。

详细说明：[Codex 执行约定](references/codex.md) · [自动制作流程](references/automation.md) · [原生后端](references/native-scene.md)

## 能做什么

| 能力 | 当前实现 |
|---|---|
| 可编辑内容 | 原生文本框、基础形状、自由曲线路径、流程连接线、简单表格，以及柱形、折线和散点图 |
| 字体搭配 | 6款 OFL 字库、5组角色搭配；按实际文案检查缺字、生成子集并冻结变量字重 |
| 背景设计 | 水墨、暖纸、技术网格三种分层配方；3张原创无字背景，附提示词、适用页型与正文安全区 |
| 模板复用 | 提取配色、字体、网格、组件和页型，在共同设计规则内变化布局 |
| 讲解动画 | 错峰入场、流程推进、左右对比、证据揭示、重点强调、状态替换及逐词/分笔画；8种原生元素效果，默认页切换为 fade |
| 检查与恢复 | 环境预检、依赖哈希、提示词快照、逐页对照、动画时序与兼容切换分支检查、完成凭据 |

参考：[字体、背景与动画](references/art-direction.md) · [手写制作与动画](references/handwriting.md) · [版式库](references/layout-library.md) · [模板提取](references/template-extraction.md) · [逐页还原](references/reference-fidelity.md)

动画选型与公开源码研究见[动画设计](references/motion-design.md)，六页可运行样本见[动画小样](examples/motion-lab/README.md)。PowerPoint嵌字或另存后，自动流程会比较动画目标、效果、点击组和时序，避免文件能打开却丢失动画。

## 实际效果

| 示例 | 展示内容 | 查看 |
|---|---|---|
| 修补日 | Codex 自主设计、实际生图、纠偏重试、四种页型重建与 PowerPoint 验收 | [完整过程](examples/auto-workshop/README.md) · [参考/成品对照](examples/auto-workshop/comparison.jpg) |
| 邻里共读 | 独立新主题试跑；30个原生对象、一个5×2表格，最终无位图 | [实际预览](examples/auto-workshop/forward-test-preview.png) · [验证记录](examples/auto-workshop/validation.json) |
| 字体与背景小样 | 六款字体、深浅背景、知识点与问答动画 | [五页小样](examples/style-lab/README.md) · [预览](examples/style-lab/preview.jpg) |
| 拾光书屋 | 五页参考图到可编辑稿，保留空间分区、流程与活动表格 | [制作记录](examples/reading-room/README.md) · [逐页对照](examples/reading-room/comparison.jpg) |

其他示例：[八种原生版式](examples/design-gallery/README.md) · [模板提取与复用](examples/template-extraction/README.md) · [绿芽概念演示](examples/green-sprout/README.md)

这些都是虚构或自生成的公开示例。原始用户资料、私人对话和参考文件的私有拆包内容不包含在素材库中。

## 交付与边界

成品包含可编辑 PPTX、完整源工程、预览和逐页可编辑性说明。PPTD 的 manifest、`pages/`、`media/`及引用依赖需要一起保留；字体子集与许可随工程提供。

- **可编辑性按对象说明。** 文字、流程、表格等尽量使用原生对象；复杂照片、木纹和插画可保留为独立图片，其内部不能分别编辑。
- **参考还原保留必要近似。** 生图字形、纸纹和手绘细节不保证逐像素一致，近似会记入模板或对照记录。
- **实际导图与结构检查分别验收。** PowerPoint 等本机播放器用于检查最终 PPTX；仅通过 ZIP/XML 检查，不代表已经完成视觉验收。
- **兼容性按实测记录。** 当前公开实测包括 Windows PowerPoint；WPS、Keynote 和复杂复合动画需要单独测试，不能由一个播放器的结果推断。

原生后端会明确拒绝暂未实现的字段或效果。支持范围与验证限制见[后端说明](references/native-scene.md)和[导出检查](references/verification.md)。

## 开发与验证

日常制作交给 Codex 执行；以下用于开发和离线重放已有设计。

需要 Python 3.10+ 与 `requirements.txt` 中的依赖。先用 `scripts/doctor.py --workspace <工作区>`选择解释器；下面的 `python` 指依赖完整的该解释器，输出目录须为新目录。

```bash
python -m unittest discover -s tests -v
python scripts/auto_deck.py compile examples/auto-workshop/project --output-dir output/workshop-replay
python scripts/check_pptx.py output/workshop-replay/deck.pptx --require-fade
```

离线重放使用已保存的场景与素材，不会重新生图；新主题由 Codex 自主规划、调用 imagegen 和读图，再使用同一后端导出。`template_pack.py`负责整理读图结论，本身不执行图像识别。

[GitHub Actions](https://github.com/Meyt1n/web-to-editable-slides/actions/workflows/validate.yml) 在 Python 3.10、3.12 上运行测试与示例重放，覆盖字体、路径、原生对象、动画引用及工作流状态。本地还完成了复用四种页型的30页、520个对象结构压力试验；这不等于30页独立设计或逐页视觉验收，详见[实测记录](examples/auto-workshop/validation.json)。

## 开源与素材许可

原创脚本、Skill说明和提示词采用 [MIT](LICENSE)。自生成图片在可许可的权利范围内随仓库提供；字体单独适用 SIL OFL 1.1，来源与许可见[第三方说明](THIRD_PARTY_NOTICES.md)。

欢迎使用虚构或有授权的资料提交改进，请保留复现步骤、实际预览和验证记录。
