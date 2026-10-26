# 把设计意图写进交接表

在既有JSON交接表中可选增加`design`以及每页布局字段。旧交接表不需要迁移；缺少这些字段时仍能制作。

```json
{
  "project": "示例",
  "design": {
    "mode": "enhance",
    "font_profiles": {
      "editorial": {
        "heading": "ZCOOL XiaoWei",
        "body": "Reading Text SC",
        "numeric": "Barlow Condensed"
      }
    },
    "constants": ["深绿与暖白", "正文无衬线", "固定页边距"]
  },
  "slides": [
    {
      "id": 1,
      "title": "产品概述",
      "status": "concept",
      "layout": "hero-split",
      "font_profile": "editorial",
      "density": "low",
      "color_mode": "light",
      "focal_point": "产品主体与作品名称",
      "visual": "concept-product"
    }
  ]
}
```

- `mode`：`fidelity`、`enhance`、`explore`。
- `font_profiles`：由角色到字体家族的映射；角色一般为`heading`、`body`、`numeric`、`accent`。同家族可承担多个角色，字体名应与实际字体内名相符。
- `layout`：优先用版式库ID，也可自定义。
- `density`：`low`、`medium`、`high`，用于交接阅读节奏，不代表自动测得的信息量。
- `color_mode`：`light`、`dark`、`mixed`，记录设计意图。
- `focal_point`：一句话说明视觉重点。
- `visual`：文字记录素材用途，如`real-photo`、`concept-scene`、`native-diagram`。
- 若用`data-focus`，填写`data_source`，或明确`data_is_illustrative: true`并在页面注明示意。示意数据不能作为成果证据。

运行：

```bash
python scripts/review_design_plan.py path/to/brief.json --output output/design-review.json
```

报告将设计建议与结构错误分开。重复布局提示只在`enhance/explore`模式生效，忠实复刻不因重复而被判错。一个页面被提示字体多，也不表示它一定不好看；回到角色、字形覆盖和真实渲染判断。

报告不读取PPTX，不估计实际字体、对比度、图像质量或元素重叠。用它审计划，再用`check_pptx.py`审结构，最后逐页看图。

## 正式制作的模板绑定

先按[模板提取流程](template-extraction.md)落成模板包，在`design`中添加：

```json
{
  "template": {
    "id": "green-sprout-reference",
    "version": "1.0.0",
    "file": "template/template.json"
  }
}
```

`file`相对交接JSON所在目录；也可通过`--template`显式指定模板。每页的`layout`应来自模板的`layouts`；没有字体或配色覆盖时，直接继承模板设置。

```bash
python scripts/review_design_plan.py output/from-template/design-plan.json --require-template
```

此模式检查绑定是否存在、ID/版本是否一致、页型是否在模板内，以及已声明的字体/配色是否偏离。`template_override: {"reason": "具体原因"}`可放在`design`或某页，记录必要偏离；它只是制作说明，不代表额外用户授权。通常应优先把新布局加入模板变体。

旧交接表与探索图册仍可不绑定模板；这用于向后兼容和方案比较，不替代正式制作前的模板提取环节。

## 逐页参考、排版与图片计划

已有逐页图片时可在每页增加以下字段。它们会保留在交接文档中，供看图制作与验收；脚本不解析自然语言来判定真实排版。

```json
{
  "reference_prompt": "prompts.md 的第2页原提示词，或这里直接粘贴提示词；等价复现须注明",
  "layout_constraints": ["左侧主体，右侧四列卡片", "箭头从左到右，结论位于底部"],
  "typography_constraints": ["标题厚重深绿，正文清晰黑体", "保留原图的两行标题与强调词"],
  "image_plan": ["先查本地 media/product.jpg，以其外形为准用imagegen优化背景", "真实UI直接复用，不重绘其中数据"]
}
```

`reference_prompt`是非空文本，可记录提示词或准确来源；其他三项为字符串列表。没有原提示词时如实说明缺失，不能补写后声称找到了原文。全部为可选字段，兼容旧表。读取原始图片、提示词和最新用户指令后再决定如何还原，详见[参考图还原流程](reference-fidelity.md)。
