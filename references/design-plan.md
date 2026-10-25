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
