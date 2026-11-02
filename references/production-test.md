# 用真实新主题验证整条制作链

本轮用虚构的“拾光书屋”完成5张imagegen参考图、1张独立空间配图、模板包、PPTD、原生PPTX及PowerPoint实开。提示词、模板观测与构建代码保存在[示例](../examples/reading-room/README.md)。固定内容示例生成器不能转换任意参考图；新项目仍需模型逐页读图并编写原生页面。

## 源工程字体与实际导图

字体子集只保证已有字符。更换主题后先用fontTools读取`getBestCmap()`，逐一核对文字框和表格用字；缺字时换用有授权的完整字体或重新生成子集。字体文件与许可一起打包，不能只记录系统中碰巧存在的字体名。

本次安装的neo-ppt编辑器会忽略`customFonts.src`中的内联`data:` CSS。仅声明字体名会静默回退；已加载的FontFace也未必进入导图器的克隆文档。`render_pptd.py`复用已安装的open-kimi-ppt导图器，在导出前加载本地字体，并注入可被导图器读取的字体CSS；不复制该编辑器或WASM。此适配依赖该后端，换版本或换后端后重新验证。

```powershell
python -m pip install PyYAML Pillow websocket-client
python scripts/render_pptd.py path/to/deck.pptd --font-map path/to/font-map.json --output-dir output/source-preview
```

字体映射为JSON：`{"Noto Sans SC":"media/body.ttf"}`，路径相对该JSON。可以用`--renderer-scripts`指定另行安装的`open-kimi-ppt/scripts`目录。字体加载日志只证明加载动作成功，最终仍要看导图。不要把后端的自动`pip --user`安装错误反复重试；虚拟环境中应在当前解释器安装缺少的依赖。

Windows本地WASM导出若提示`python yaml failed: undefined`，可能是其YAML回退硬编码`python3`而宿主只有`python`。可在工作区工具目录安装`js-yaml`，仅为导出子进程设置`NODE_PATH`；不修改全局Python映射。此问题属于后端适配，不是PPTD内容损坏。

## 最终PPTX必须另验

Windows有PowerPoint时，可用原有嵌字脚本保存。可选`-FontMap`会临时注册映射中的字体并广播字体更新，在`finally`撤销；不写系统字体目录或注册表。使用前核对字体许可，按当前任务已授权的环境范围执行。未指定该选项时保持原有行为。

```powershell
./scripts/embed_fonts_windows.ps1 -InputPptx output/native.pptx -OutputPptx output/final.pptx -FontMap path/to/font-map.json
./scripts/render_pptx_windows.ps1 -InputPptx output/final.pptx -OutputDir output/actual-render
python scripts/check_pptx.py output/final.pptx --require-fade --output output/structure.json
```

`render_pptx_windows.ps1`只读打开最终文件，按原画幅导出PNG，记录渲染器版本、对象数和文字越框候选。输出目录必须是新目录；不保存或覆盖输入PPTX。越框候选需看图判断，未覆盖表格内部文字和跨软件差异。

PowerPoint保存的压缩EOT可能无法被结构脚本解压；`--require-fonts`因此可能失败，不能改成伪造“通过”。保留字体声明、文件头结果、实际保存来源及实开记录。合法字体表、嵌入声明也不保证播放器采用同一字形；本例正文在浏览器与PowerPoint中的笔画和字宽仍有差异。

不要临时手造EOT容器来追求检查通过。本次实验出现过“可解析字体表、PPTX可打开，但播放器仍回退字体”的情况，实验代码未纳入工具。直接改OOXML时还须保留命名空间、使用规范`UTF-8`声明；XML库能解析不等于Office能打开。

实开还发现两行大标题的字体边界超出原框，最终改为两个原生文字框保留断行；数字标签扩展文字框宽度。先修框、间距或段落结构，不因浏览器一张图正确就结束验收。

## 逐页参考对照

建立`pairs.json`，路径相对这个JSON：

```json
[
  {"id":1,"reference":"references/01.png","rendered":"rendered/01.png"}
]
```

```powershell
python scripts/compare_slides.py path/to/pairs.json --output-dir output/comparison
```

工具生成逐页左右对照和总览，保留输入尺寸、哈希与画幅差异。它不改原图，不给像素相似度分数，也不自动判定“视觉通过”。逐页看标题位置、图文比例、节点、列数、裁切和字体，再另写实际结论。
