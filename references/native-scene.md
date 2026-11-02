# 仓库自带原生后端

`native_renderer.py`使用requirements中的python-pptx、FontTools和Pillow，把模型看图后写出的通用场景导出为PPTX与自包含PPTD。无需外部WASM导出器、浏览器编辑器或Node。输入不是任意图片的自动OCR结果；视觉分析和设计由运行Skill的智能体完成。

先用`python scripts/doctor.py`选择Python 3.10+且依赖完整的解释器，后续始终使用返回的路径；不要混用系统Python与已有虚拟环境。

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
| chart | 原生柱形、折线、散点，同种系列 | 需真实数据或明确示例数据，不从图片编造；暂不支持混合/复杂统计图 |

场景沿用PPTD元素字段：`elementId/elementType/bounds`。形状用`fill:{type:'solid',color:'#...'}`、`border:{style:'solid',color:'#...',width:1}`；custom另有`path`和`viewBox`。表格用`rows`二维对象，单元格沿用文本字段并可有`fill`。图片另有`src/fit/raster_reason`；`raster_reason`是本工具的来源说明字段。

图表用`data:{cols:['x','y'],rows:[['A',2],['B',3]]}`、`series:[{type:'bar',name:'示意',encode:{x:'x',y:'y'},fill:'#72896B'}]`。另写`dataSource:{status:'demo',label:'仅作演示'}`或有来源说明的`verified`。图中也应放可见的来源/示例说明，元数据不能代替面向读者的说明。

## 动画与可编辑性

所有页默认根级fade切换。页内支持`appear/fade-in/wipe-in`入口动画，触发为`onClick/withPrevious/afterPrevious`，支持正时长与非负延迟。可直接使用`motion_presets.py`。表格/图表整体入口、强调、退出、运动路径等超出此后端范围；选择其他可用后端或记录设计近似，不静默删动画。

`editability-report.json`逐页列出原生对象数量和位图边界；自由曲线在PPT中是可编辑路径，复杂木纹、照片和插画内部仍是位图。本工具拒绝未实现的元素字段/效果，避免“生成成功”却丢失关键内容。原生对象数量不等于可编辑像素比例，不宣传完全无损转换。

字体二进制嵌入和实际PPTX导图仍使用可用播放器：Windows可运行`embed_fonts_windows.ps1`和`render_pptx_windows.ps1 -FontMap ...`；无Office时仍可离线生成PPTX与PPTD，但不能把结构检查当成字形或视觉验收。PPTD编辑器是可选工具，导出不依赖它。

## 当前验证范围

仓库CI覆盖结构、数据完整性、缺字、失效动画目标、依赖路径与通用后端。公开例子保留真实提示词、失败重试、参考/成品对照和验证记录。PowerPoint实开结果只证明记录中的环境；WPS、Keynote、LibreOffice以及复杂长篇、复杂复合动画须分别验证，不能从一个播放器的成功推出兼容结论。
