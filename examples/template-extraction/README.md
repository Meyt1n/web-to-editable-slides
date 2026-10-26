# 从两张提示图提取模板，再根据模板制作

本例读的是仓库内虚构植物主题的封面和四步流程参考图，未使用真实用户素材。

## 读图后得到什么

1. 观察整套画面的共性：暖白窗边、深绿标题、少量珊瑚橙强调、亲和短标题、浅色圆角卡片与产品主体。
2. 把文案、植物主体、手机占位界面等页面内容与设计规范分开。
3. 形成[读图观测与选定参数](observations.json)，记录来源、字体近似、颜色与几何近似、原生组件、页型和可变范围。
4. 将这些结果整理为[自包含模板包](template/TEMPLATE.md)，包含模板JSON、代表图、背景、字体和许可。
5. 三页示例实际读取模板的字体、配色、圆角和内容槽位，再填入文案与独立主体图；输出设计计划记录使用的模板ID与版本。

字体无法从位图精确确认，因此选择气质接近的OFL字体并注明近似；章节页是在共同规范下派生，不冒称有一张未提供的章节参考图。无字背景复用此前为同一主题生成的素材，不是把含字参考图当成背景。

## 运行

在仓库根目录：

```bash
python -m pip install -r requirements.txt
python scripts/template_pack.py prepare examples/template-extraction/observations.json --source-dir . --output-dir output/template
python scripts/template_pack.py check output/template/template.json
python scripts/build_demo.py --template output/template/template.json --output-dir output/from-template
python scripts/review_design_plan.py output/from-template/design-plan.json --require-template
python scripts/check_pptx.py output/from-template/green-sprout.pptx --require-fade
```

模板提取中的视觉判断由模型完成；整理脚本只复制选定素材、校验相对路径与槽位，并生成人可读规范，不自动识图或调用imagegen。

## 实际应用结果

[三页可编辑示例](../green-sprout/demo/green-sprout.pptx) · [预览](../green-sprout/preview.jpg) · [绑定模板的设计计划](../green-sprout/demo/design-plan.json)

源工程内有一份模板快照，后续编辑可追溯所用版本。测试还会改变模板中的强调色、标题位置和字号，再检查输出PPTX，证明生成器读取了参数，而不是只在说明文档中提到模板。

`prepared`只表示规范已经整理；实际看图和实开检查记录在[模板应用验证](validation.md)与[示例验证文档](../green-sprout/validation.md)。如果继续增加页面，应先读取模板和对应页型；新布局先作为模板变体扩展，必要偏离记录原因。
