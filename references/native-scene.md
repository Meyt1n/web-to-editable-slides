# 仓库自带原生后端

`native_renderer.py`使用requirements中的python-pptx、FontTools和Pillow，把当前Codex看图后写出的通用场景导出为PPTX与自包含PPTD。无需外部WASM导出器、浏览器编辑器或Node。输入不是任意图片的自动OCR结果；视觉分析和设计由当前Codex模型直接完成。

按[Codex执行约定](codex.md)取得运行时并用`doctor.py --workspace <活跃工作区> --python <Codex返回的Python>`选择Python 3.10+且依赖完整的解释器，后续使用该路径与Skill脚本绝对路径；不要混用系统Python与已有虚拟环境。产物写入工作区，不写入Skill安装目录。

```powershell
python scripts/native_renderer.py task/scene.json --output-dir output/deck-01
```

## 输入与依赖

```json
{
  "version":1,"title":"演示标题","size":[960,540],
  "template_file":"template/template.json",
  "pages":[{
    "id":1,"pageType":"content","layout":"模板已声明的页型",
    "reference":"references/01-v01.png",
    "background":{"type":"solid","color":"#F7F2E8"},
    "elements":[{
      "elementId":"title","elementType":"text","bounds":[56,50,840,80],
      "content":{"text":"可编辑标题","fontFamily":"ZCOOL XiaoWei","fontSize":44,"color":"#2B3530","bold":true,"align":["left","middle"],"wrap":false}
    }],"animations":[]
  }]
}
```

模板使用现有`template_pack.py`规范，保存在专门的`template/`目录，资源自包含；页面必须引用已声明的页型，画布尺寸一致。资源用相对路径，图片放`media/`，参考图放`references/`，`media/fonts/`留给准备工具。当前字体从仓库6款完整字库中按全部实际文案准备；可用`font_weights`指定每家族的静态字重。输出字体子集、OFL、font-map以及原模板快照。

## 已实现的元素

| 类型 | 当前支持 | 主要边界 |
|---|---|---|
| text | 原生文本框，中文字体、字号、粗体、HEX6颜色、水平/垂直对齐、换行与行距 | 普通字符串，不解析HTML富文本；不自动缩字消除拥挤 |
| shape | rect、roundRect、ellipse、custom，纯色/无填充、细边、透明度 | 自由路径支持SVG M/L/C/Q/Z等解析出的线与贝塞尔段；viewBox是宽高二元组 |
| line | 折线与连接线 | `points`是`"0,0 100,4 200,0"`形式，配bounds/viewBox/border；复杂箭头可用独立原生路径 |
| image | PNG/JPEG，cover/contain，保留透明PNG | 每张图必须写`raster_reason`，披露内部不可分别编辑的内容；不允许全图透明度 |
| table | 原生表格，矩形单元格，列/行比例、逐格字体/填充/对齐 | 不支持合并、旋转、全表透明度；columnWidths、rowHeights均为正且和为1 |
| chart | 原生柱形、折线、散点，同种系列；坐标轴范围、数值标签、底色与配色 | 需真实数据或明确示例数据，不从图片编造；暂不支持混合/复杂统计图 |

场景沿用PPTD元素字段：`elementId/elementType/bounds`。形状用`fill:{type:'solid',color:'#...'}`、`border:{style:'solid',color:'#...',width:1}`；custom另有`path`和`viewBox`。表格用`rows`二维对象，单元格沿用文本字段并可有`fill`。图片另有`src/fit/raster_reason`；`raster_reason`是本工具的来源说明字段。

图表用`data:{cols:['x','y'],rows:[['A',2],['B',3]]}`、`series:[{type:'bar',name:'示意',encode:{x:'x',y:'y'},fill:'#72896B'}]`。另写`dataSource:{status:'demo',label:'仅作演示'}`或有来源说明的`verified`。图中也应放可见的来源/示例说明，元数据不能代替面向读者的说明。

图表可加`style:{background:'#FFFCF6',textColor:'#24354B',gridColor:'#B9CCD8',minimum:0,maximum:15,majorUnit:3,numberFormat:'0',labelFormat:'0.00',dataLabels:true,fontSize:13,pointColors:['#315ECC','#D9674D']}`。`numberFormat`控制纵轴，`labelFormat`控制数值标签；比例数据用0–1及`0%`，不要把0–100误配成百分比格式。`pointColors`仅用于单系列柱形图，颜色数必须等于数据行数；多系列用各系列的`fill`。两个单位不同的指标应分图并分别设置尺度。

`style`是本仓库原生编译器的场景扩展，准确复现以`scene.json`和本编译器为准；其他PPTD编辑器对扩展样式的显示需另行核对，不从PPTX导图推断编辑器表现。

## 动画与可编辑性

所有页默认根级fade切换。页内支持下列8种原生效果；可用`motion_presets.py`编排，见[按内容选动画](motion-design.md)。

| 效果 | 原生行为 | 可选参数 |
|---|---|---|
| `appear` | 显示对象；`durationMs`可作为该步停留时长 | 无 |
| `fade-in/fade-out` | 淡入/淡出，退出后隐藏 | 无 |
| `wipe-in/wipe-out` | 擦入/擦出，退出后隐藏 | `direction: up/down/left/right`，默认right，沿用OOXML wipe过滤器含义 |
| `fly-in` | 对x/y位置做插值，从画布边缘进入 | `direction`表示起始边，up上、down下、left左、right右；默认left |
| `zoom-in` | 宽高从0插值到对象原始尺寸 | 无 |
| `pulse` | 短暂放大后复位；已显示对象的强调 | `scale`是大于1的比例，默认1.08 |

动画字段为`elementId/effect/trigger/durationMs/delayMs`，另按效果支持`direction/scale`。不支持的字段和组合报错。时长必须为有限正数，延迟为有限非负数，均四舍五入到毫秒；`pulse`的`durationMs`包含放大及复位两半，规范化到至少2ms的偶数。触发为`onClick/withPrevious/afterPrevious`：新点击开始一组；withPrevious相对前一动画的起点延迟，afterPrevious相对前一动画的终点延迟，均非整组起点。表格/图表整体动画、复杂运动路径及其他效果超出本后端范围；图表上的独立文字与标注仍可动画。

同一`elementId`可依次入场、强调、退出及再次入场。首次入场前隐藏；首个动画是强调/退出的对象视为起初可见。已显示时不能再次入场，隐藏时不能强调或退出，同组内同一对象的动画不能相互重叠。每次动画有独立构建标识，避免编辑器在另存时丢掉后续效果。`check_motion.py`可比较原始与另存PPTX的目标、效果、点击组和时序；自动流程有动画时会在`finish`执行并保留报告。

导出的PPTD保留这些动画参数，但其他PPTD编辑器/导出器未必实现本编译器的全部效果和`scale`等参数；本地PPTX的播放验证不能作为其他编辑器动画预览的验证。

`handwriting_groups`为已拆分的词、短语或笔画生成有先后次序的擦入，自动安排词长时长和短停顿，每个知识点用一次点击。它不负责拆图、识字或恢复字体，也不沿完整曲线路径追踪笔尖；详见[手写讲稿风](handwriting.md)。当前后端仍输出fade切换，能够识别输入稿的Morph不等于已经支持生成Morph。

`editability-report.json`逐页列出原生对象数量和位图边界；自由曲线在PPT中是可编辑路径，复杂木纹、照片和插画内部仍是位图。本工具拒绝未实现的元素字段/效果，避免“生成成功”却丢失关键内容。原生对象数量不等于可编辑像素比例，不宣传完全无损转换。

字体二进制嵌入和实际PPTX导图仍使用可用播放器：Windows可运行`embed_fonts_windows.ps1`和`render_pptx_windows.ps1 -FontMap ...`；无Office时仍可离线生成PPTX与PPTD，但不能把结构检查当成字形或视觉验收。PPTD编辑器是可选工具，导出不依赖它。

## 当前验证范围

仓库CI覆盖结构、数据完整性、缺字、失效动画目标、依赖路径与通用后端。公开例子保留真实提示词、失败重试、参考/成品对照和验证记录。PowerPoint实开结果只证明记录中的环境；WPS、Keynote、LibreOffice以及复杂长篇、复杂复合动画须分别验证，不能从一个播放器的成功推出兼容结论。
