# 字体、背景与讲解节奏：五页能力小样

这是原创设计能力验证，展示六款可编辑字体、三种背景配方、三张原创无字背景和按知识点展开的动画。学习了授权参考稿的分层、留白和讲解方法，没有复制其图片或正文。

查看[实际PowerPoint导图](preview.jpg)与[验收记录](validation.json)。通用方法见[字体库、分层背景与动画](../../references/art-direction.md)。

| 页码 | 验证内容 |
|---|---|
| 1 | 马善政书法标题；原创无字水墨背景；原生大字暗纹；标题纵向擦入 |
| 2 | 龙藏标题；同色安静正文背景；编号、关键词、解释按四次点击依次展开 |
| 3 | 原创暖白宣纸背景；马善政、龙藏、小薇、快乐、Noto Sans SC、Barlow Condensed六字体分工展示 |
| 4 | 浅纸问答页；题目与解释分两次点击出现，同组标签与说明一起展开 |
| 5 | 深色网格背景；清晰正文、边缘几何与稳定的内容安全区 |

字体对照页用于选型。正式课件应选定一组标题、正文和数字字体，不要求同时使用六款。

## 重建与导出

先安装仓库的`requirements.txt`。在仓库根目录运行，输出目录须为新目录：

```powershell
python examples/style-lab/build.py --output-dir output/my-style-lab
```

构建器调用`prepare_fonts.py`，按本次文案检查缺字、生成子集，并将Noto变量字体冻结为400字重。完整上游字库、许可与来源在`assets/fonts/`；工程中只携带实际需要的子集及许可。无字氛围图的实际imagegen提示词、哈希、页型和正文安全区在`assets/backgrounds/catalog.json`及其指向文件，无需重新生图即可离线重建。构建器实际调用`copy_asset`打包图片、提示词和来源，调用`motion_presets`安排标题、知识点和问答动画。

先使用已安装的open-kimi-ppt后端检查源工程图片（需浏览器及可选依赖`websocket-client`）：

```powershell
python scripts/render_pptd.py output/my-style-lab/style-lab.pptd --font-map output/my-style-lab/font-map.json --output-dir output/my-style-lab/source-preview
```

再用所装后端的`export_pptx.py`导出`native.pptx`。Windows安装PowerPoint时，继续执行：

```powershell
./scripts/embed_fonts_windows.ps1 -InputPptx output/my-style-lab/native.pptx -OutputPptx output/my-style-lab/style-lab.pptx -FontMap output/my-style-lab/font-map.json
./scripts/render_pptx_windows.ps1 -InputPptx output/my-style-lab/style-lab.pptx -OutputDir output/my-style-lab/rendered -FontMap output/my-style-lab/font-map.json
python scripts/check_pptx.py output/my-style-lab/style-lab.pptx --require-fade --output output/my-style-lab/pptx-report.json
./scripts/render_animation_windows.ps1 -InputPptx output/my-style-lab/style-lab.pptx -OutputVideo output/my-style-lab/animation-preview.mp4
```

字体保存和静态导图的`-FontMap`临时加载随包字体，结束后撤销，不做持久安装。手动编辑器可能需要联网取得Google Fonts CSS；本地预览脚本显式加载随包字库。

## 实测发现与修正

- 图片里的书法不能直接当作一种字体。新增可编辑的真实书法字体，不声称精确识别参考稿的图片字。
- Noto变量字体默认内名带Thin；准备工具显式冻结常规字重并回填实际家族内名。
- PowerPoint视频可正确使用嵌字，`Slide.Export`静态导图却曾回退。导图新增显式`-FontMap`与依赖记录，六款字体实际看图确认。
- 实开后发现暗纹字框过窄、关键词文字高度超框；修正字号与文本框。扩展到五页后重新实开，溢出候选仍为0。
- 连续运行时遇到过短暂COM启动失败；共享会话助手仅对已知临时错误有限重试，不结束用户已有PowerPoint进程。
- 动画检查同时记录效果、触发、时长和目标引用。第二页有四个点击组，第四页问答有两个点击组；导出报告和实际预览见验收记录。

实际PowerPoint静态图和自动播放视频分别验收。视频显示了标题擦入与知识点依次出现，但不能代替现场点击时的停顿检查。PowerPoint保存了六个压缩EOT字体部件；结构工具仍诚实标记其压缩二进制无法解压验证，不把这一项当成严格字体验证通过，也不据此保证其他播放器效果一致。
