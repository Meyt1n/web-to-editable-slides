# Codex执行约定

本Skill面向Codex，默认在Codex本地桌面应用中运行。当前Codex负责理解需求、视觉分析、设计、生图调用、代码和文件操作，仓库脚本负责确定性的记录、编译与检查。使用者只需给主题与资料；不要让其另找视觉模型、先在网页生图或提供OpenAI API Key。

## 从当前会话直接执行

| 工作 | Codex执行方式 |
|---|---|
| 需求澄清 | 有实质缺口时使用当前会话的提问工具；优先异步合并问题，同时继续独立工作。用户让你决定时直接规划 |
| 看参考图与成品 | 当前Codex模型直接查看图片；本地文件用可用的`view_image`工具打开，逐页对照。不要把OCR文本提取当作完成看图 |
| 生成或编辑图片 | 读取本会话可用的imagegen Skill，调用Codex内置imagegen；工具入口、参数和参考图机制以实际工具文档为准 |
| 执行脚本与写文件 | 用Codex文件/终端工具运行仓库脚本。工具被包装或延迟加载时先发现实际入口，不在Python里虚构imagegen函数 |
| Python与库 | 桌面版提供`load_workspace_dependencies`时优先调用，取得真实运行时路径，再交给doctor验证。已有工作区虚拟环境可复用 |
| 进度与交付 | 在当前聊天中更新实际进度；输出PPTX、完整工程和预览的绝对路径链接，有必要时展示图片 |

imagegen默认走Codex内置工具，不创建OpenAI客户端、不另起API调用，也不为生图索取API Key。任务文件中的提示词、图片和工具参数记录是重现资料，不是取代真实工具调用的凭据。

只有实际工具调用失败或当前会话确实未暴露相关入口时，才报告“当前Codex会话”的具体问题与已完成部分；不把“先准备有视觉/imagegen的宿主”当作默认开场或交付免责声明。不要虚构所有Codex运行界面都具有完全相同的工具。

## 分清Skill目录与用户工作区

1. Skill目录用于读取`SKILL.md`、scripts、references与assets。路径由当前安装位置解析，不硬编码用户名、Codex缓存版本或盘符。
2. 活跃工作区用于`.venv`、`output/`、任务、日志和交付物。即使Skill安装在用户技能目录，也从用户工作区执行，不向安装目录写项目产物或安装依赖。
3. 在桌面版先获取随包运行时。运行下列预检时，`<...>`替换为本会话工具真实返回的路径：

```text
<可执行Python> <Skill目录>/scripts/doctor.py --workspace <活跃工作区> --python <Codex提供的Python>
```

随后每条命令固定使用`selected.executable`和脚本绝对路径。doctor会尝试指定的Python、工作区`.venv`与当前解释器；它只验证本地Python和库，Codex工具由Codex会话确认。

如果没有可用工作区环境，用Codex提供的Python在工作区创建`.venv`并安装Skill的requirements，再预检；不修改系统Python或Skill安装目录。未暴露桌面运行时工具的Codex会话可直接选择现有工作区解释器。原生导出不需要Node、浏览器编辑器或额外PPTD插件。

## 执行到底与恢复

读取[自动流程](automation.md)，由Codex设计brief和逐页提示词，实际调用imagegen，自己查看每次结果，提取模板并写scene。脚本返回`call_imagegen/inspect_reference_image/write_template_and_scene`时，是给Codex的下一步动作，不是给使用者的待办。

长任务恢复时先读当前任务的brief、workflow和`status`，从已有进度继续；不要因为上下文切换而重新生成全部图片。已确定的主题、风格、素材授权和用户回答持续有效。生成图片必须复制到工作区项目后再引用，不能只留在Codex自动缓存中。

实际PPTX验收使用本机可用播放器：Windows已有PowerPoint时用仓库COM脚本；其他系统选择实际可用的渲染器。Codex能看参考图不等于PPTX已经实开，缺少实际导图时保持视觉验收待完成，不伪造通过。

## Codex发现与调用

优先使用本会话的`$skill-installer`安装仓库根目录的Skill。手动安装可使用Codex的`.agents/skills/`目录；已有安装保留原位置，不制造同名副本。入口名继续是`web-to-editable-slides`，在Codex中可显式用`$web-to-editable-slides`，也保持默认的自动匹配。

安装位置和调用约定以[OpenAI官方Skills文档](https://learn.chatgpt.com/docs/build-skills)为准；当前会话的工具与Skill说明是执行入口的依据，不用API图像生成文档替代Codex内置imagegen工具文档。
