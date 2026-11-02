# 修补日：智能体自行生图、读图与原生重建

4页虚构社区工作坊方案：封面、四步流程、活动安排、准备事项。主题、受众、文案、大纲与逐页视觉描述均由智能体设计，实际调用内置imagegen生成参考图，再由同一智能体看图、提取模板、分离素材并写通用scene。没有用户手动写提示词、看图提取JSON或操作PPT编辑器。

[实际成品预览](preview.jpg) · [参考/成品逐页对照](comparison.jpg) · [验收记录与限制](validation.json)

## 这次真正执行了什么

- `brief.json`保存模型设计的受众、目标、风格与逐页内容；`project/prompts/`保存实际提示词及调用快照。
- 实际进行了5次逐页参考图生成：第二页第一次自行加入了大幅拼贴插画，模型看图发现偏离计划，修改提示词后只重生成该页。两次结果和提示词都保留。
- 另进行了2次素材分离：封面木凳组合与收尾木桌拼贴从对应参考局部生成透明素材，记录在`project/media/`。复杂木纹和纸纹仍为位图，其内部不能分别编辑。
- `project/reference-review.json`是模型实际看图后的观察；`project/template/`保存共性和页型；`project/scene.json`保存原生场景。通用后端不读取主题专属的Python布局代码。
- 仓库原生后端直接生成PPTX及PPTD，字体用仓库字库准备；没有调用外部PPTD/WASM导出器。PowerPoint用于最终嵌字、导图与播放验证，记录与二进制检查分别保留。

## 离线重放已完成的设计

安装仓库requirements后，在根目录运行，输出使用新目录：

```powershell
python scripts/auto_deck.py status examples/auto-workshop/project
python scripts/auto_deck.py compile examples/auto-workshop/project --output-dir output/workshop-replay
```

此命令重放已有设计与素材，不会再次生图，也不冒充新主题的自动识别。新主题由智能体依照[自动制作流程](../../references/automation.md)自主写brief、调用imagegen和看图，再使用相同通用后端，无需使用者改脚本。

Windows有PowerPoint时，智能体继续执行字体保存、实际导图与逐页对照，并写visual-qa后finish；没有实际渲染器时只能报告结构检查状态。

## 观察到的问题与近似

实际实开中发现python-pptx预设形状继承主题阴影，导致原本应轻薄的线与节点出现投影；通用后端现已显式关闭继承阴影。流程说明出现单字孤行后改为按语义断行并统一顶部对齐；修复后再次导图。

参考图标题是生图字形，成品用站酷小薇加粗近似，不能保证笔画相同；背景纸纹简化为暖白底。流程、圈线、表格、标签与编号均为原生对象；右侧图标用原生编号近似。封面和木桌组合各保留一个独立位图，局部构图与笔触存在差异。对照图保留这些差异，不提供虚假的像素相似度评分。

跨PowerPoint/WPS/Keynote兼容性、复杂长篇和复杂复合动画未在此例得到证明，具体已检查项与未检查项见validation.json。

## 独立新主题与结构压力试验

另一个独立智能体用同一Skill完成了一页虚构读书会招募草案：自己设计提示词、实际调用一次imagegen、读图、提取模板并用原生后端导出，直到finish/status返回complete，无需用户接手中间操作。实际PowerPoint预览见[独立新主题结果](forward-test-preview.png)：30个原生对象、0张位图、一个5×2可编辑表格，溢出候选为空。该试跑暴露的默认Python过旧与哈希手算问题，分别促成doctor预检、明确哈希约定与qa-skeleton自动填充工具。

还用本例四种页型复用为30页，检查了520个对象的批量导出、表格与动画引用，结构检查通过。这是单机结构压力试验，不代表30页独立设计、逐页视觉验收或跨软件性能保证。具体时长、文件大小和验证范围保留在validation.json；本轮本地共71项测试通过。
