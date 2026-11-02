# 拾光书屋：从imagegen参考图到原生PPT的完整试跑

虚构主题“社区共享阅读空间”，5页：封面、空间分区、借阅流程、一周活动、试点计划。没有实际场地、真实运营数据或对外承诺。

`prompts.json`保留5次参考图生成的完整提示词，后4页以第一张封面作为风格参考；`asset-prompt.txt`是独立空间配图的实际提示词。全部使用内置imagegen，未调用外部计费API。参考图、配图、字体与许可在`input/`；图片来源和哈希见`input/generation-log.json`。

可直接查看[实际PowerPoint预览](preview.jpg)、[参考与实际逐页对照](comparison.jpg)和[本次验收记录](validation.json)。

## 离线重建源工程

在仓库根目录、已安装requirements.txt的Python环境运行，输出目录须为空或新建：

```powershell
Copy-Item -Recurse examples/reading-room/input output/my-reading-room
python scripts/template_pack.py prepare examples/reading-room/observations.json --source-dir output/my-reading-room --output-dir output/my-reading-room/template
python examples/reading-room/build.py output/my-reading-room
python scripts/review_design_plan.py output/my-reading-room/design-plan.json --require-template
```

`build.py`实际读取模板槽位、配色、字体角色，写出5份`.page`和`.pptd`，并检查正文、标题和表格全部用字。它是这个主题的可复现制作代码，不是通用读图转换器。

## 导图、导出与实际播放

先使用另行安装的open-kimi-ppt后端导出源工程图片，逐页检查后再导出PPTX：

```powershell
python -m pip install websocket-client
python scripts/render_pptd.py output/my-reading-room/reading-room.pptd --font-map output/my-reading-room/font-map.json --output-dir output/my-reading-room/source-preview
```

PPTX使用所装演示文稿技能的`export_pptx.py`本地WASM路径导出，Windows字体保存与实际导图：

```powershell
./scripts/embed_fonts_windows.ps1 -InputPptx output/my-reading-room/native.pptx -OutputPptx output/my-reading-room/reading-room.pptx -FontMap output/my-reading-room/font-map.json
./scripts/render_pptx_windows.ps1 -InputPptx output/my-reading-room/reading-room.pptx -OutputDir output/my-reading-room/rendered
python scripts/check_pptx.py output/my-reading-room/reading-room.pptx --require-fade
```

`-FontMap`临时注册所给字体，保存后撤销，不向系统目录或注册表安装。手动使用编辑器时可能需要联网获取Google Fonts CSS；本地字体也随包提供，`render_pptd.py`使用这些字体生成预览。后端未随本例分发。

## 本次实测发现与修正

- 示例正文子集缺少新主题文字：改用按本次文案生成的OFL字体子集，并在写源工程前逐字检查。
- 内联CSS字体被编辑器忽略；单独加载FontFace未进入导图克隆：加入本地字体与CSS注入适配，实际导图确认宋体标题。
- 虚拟环境中的后端自动`pip --user`失败：在当前解释器补齐可选依赖并增加预检。
- Windows WASM回退寻找`python3`失败：在工作区配置`js-yaml`及子进程`NODE_PATH`，无需改全局Python。
- 最终PPT实开的大标题和编号越框：标题拆成两个原生文字框，编号框加宽；最终PowerPoint报告无越框候选。
- 参考图与实际播放器的字体笔画、正文细节存在差异；照片按独立配图重新裁切，平面图的家具、植物装饰做了几何简化。保留空间分区、节点顺序、表格内容与各页构图，未声称像素级复刻。
- 手造字体容器虽然能通过部分结构检查，但未可靠改善播放器字形，实验代码没有纳入工具；最终用PowerPoint本身保存字体。

最终本地交付目录包含可编辑PPTX、完整PPTD工程、实际PowerPoint导图、参考/成品并排对照与逐页检查记录。结构报告中的压缩EOT仍标记无法解压验证；这与实际保存、实开记录分别保留。
