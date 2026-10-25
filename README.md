# Web to Editable Slides

**先在网页版把PPT“设计出来”，再让能看图、能写文件的模型把它“搭出来”。**

这是一个中文优先的开源 Skill，记录从作品资料、网页版大纲和逐页生图，到实物素材优化、统一母版、可编辑PPT及实开检查的完整方法。

![绿芽：完全虚构的示例主题](assets/reference-cover.png)

## 这套流程解决什么

网页版逐页生成的图能快速确定视觉方向，但整页PNG放入PowerPoint后，标题、正文、卡片和流程仍然无法分别编辑。本技能指导另一个模型提取参考图中的设计规律，以原生文字、形状、流程和独立图片重建幻灯片。

它不声称一键无损转换，也不保证像素级复刻。图片中的复杂插画保留为素材，内容与布局则尽量重建为可编辑对象。

## 完整流程

```mermaid
flowchart LR
    A[作品资料与事实] --> B[网页版生成大纲]
    B --> C[比较风格候选]
    C --> D[确认风格与逐页提示词]
    D --> E[网页版逐页生成参考图]
    E --> F[按顺序上传图片与关联对话]
    F --> G[模型提取设计系统]
    G --> H[实物优先 · imagegen补充素材]
    H --> I[原生对象重建PPT]
    I --> J[预览 · 实开 · 字体与结构检查]
```

已有大纲或参考图时从对应步骤开始。模型可以是你使用的6.1 Sol，也可以是具备看图、写文件和相关工具能力的其他模型；仓库不把某个型号设为硬性依赖。

## 使用

把仓库作为一个技能目录安装。可在支持的Codex环境调用已有安装器：

```text
$skill-installer 从 https://github.com/Meyt1n/web-to-editable-slides 安装这个技能，技能位于仓库根目录。
```

或手动克隆到用户技能目录（不要覆盖已有目录）：

```bash
git clone https://github.com/Meyt1n/web-to-editable-slides.git ~/.codex/skills/web-to-editable-slides
```

若宿主使用其他技能搜索目录，把该文件夹放到对应位置即可。技能由 `SKILL.md` 描述；安装与发现规则以 [OpenAI官方技能文档](https://learn.chatgpt.com/docs/build-skills) 和你的宿主为准。

把逐页图片按顺序附上，并发送：

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
python scripts/make_handoff.py examples/green-sprout/brief.json --output output/handoff.md
python scripts/build_demo.py --output-dir output/green-sprout
python scripts/check_pptx.py output/green-sprout/green-sprout.pptx --require-fade --output output/pptx-report.json
python -m unittest discover -s tests -v
```

示例生成器离线运行，输出3页PPTX及配套PPTD；它按代码定义重建示例，**不自动识别任意参考图**。命令行重建版本默认不嵌字体；示例附带OFL字体，字体嵌入和实际播放应按所用软件验证。仓库中的交付示例另做了实开与字体检查，详见示例说明。

## 目录

| 文件 | 用途 |
|---|---|
| `SKILL.md` | 给模型加载的核心工作流 |
| `references/prompts.md` | 资料、大纲、风格、逐页生图、移交和修订提示词 |
| `references/handoff-schema.md` | 页码、素材和事实状态的交接规范 |
| `references/tools.md` | 关联对话、imagegen、素材检索、导出和验证能力说明 |
| `references/verification.md` | 原生可编辑性、字体、切换和实开检查 |
| `scripts/` | 图片清点、交接表、示例构建与PPTX检查脚本 |
| `assets/` | 全新生成的植物主题参考图、无字母版、主体图和OFL字体 |
| `examples/green-sprout/` | 一套不含私人素材的输入、提示词与实际输出 |

## imagegen与其他依赖

本技能不会开通imagegen，也不会自动获取付费API权限。使用宿主已提供的图像工具和已安装技能。内置工具可用时无需为了本仓库另写API调用；缺少工具时仍可生成大纲、提示词与PPT布局，并说明未生成的素材。

完整版生产曾用到PPTD、本地WASM导出、浏览器预览、PowerPoint COM、字体子集、图片清点与OOXML检查。本仓库**没有复制这些第三方技能或其运行时**，工具映射及可替代做法写在 [工具说明](references/tools.md)。

## 开源范围

原创脚本、技能说明和提示词采用 [MIT许可证](LICENSE)。示例自生成图片在维护者拥有或可许可的权利范围内同许可提供；字体单独适用SIL OFL 1.1，见 [第三方说明](THIRD_PARTY_NOTICES.md)。

欢迎用虚构或有授权的素材提交改进。请不要把真实用户资料、私人聊天链接、账号令牌或本机绝对路径提交到示例中。
