# 八种布局与字体选型图册

这是一份用于选择表达方式的图册，继续使用虚构的植物主题。它演示“固定主题和色彩，同时按内容改变结构”；不建议正式PPT每页随机更换字体。

| 页 | 表达方式 | 主要字体方案 |
|---|---|---|
| 01 | 场景图出血、宋体大标题 | ZCOOL XiaoWei＋Reading Text SC＋Barlow Condensed |
| 02 | 开放分栏、图文与信息层级 | 编辑风 |
| 03 | 沿共同维度的明暗对比 | 清晰产品风 |
| 04 | 无卡片的四步路径 | 清晰产品风 |
| 05 | 分层架构与输入关系 | 清晰产品风 |
| 06 | 大主体、局部引线与说明 | 编辑风 |
| 07 | 深底短句与章节留白 | ZCOOL KuaiLe＋Reading Text SC＋Barlow Condensed |
| 08 | 错位路线、阶段与后续设想 | 编辑风 |

[预览](preview.jpg) · [PPTX](demo/design-gallery.pptx) · [PPTD](demo/design-gallery.pptd) · [设计计划](demo/design-plan.json) · [实际验证](validation.md)

## 复现

在仓库根目录：

```bash
python -m pip install -r requirements.txt
python scripts/build_gallery.py --output-dir output/design-gallery
python scripts/review_design_plan.py output/design-gallery/design-plan.json
python scripts/make_handoff.py output/design-gallery/design-plan.json --output output/gallery-handoff.md
python scripts/check_pptx.py output/design-gallery/design-gallery.pptx --require-fade
```

构建器检查实际文字的字形覆盖，使用拉丁数字字体时不把中文交给系统自动回退。它不安装字体，也不自动嵌入PPTX字体。PPTD内嵌了预览所需的字体子集；PPTX要在本机安装适用字体或借助支持的软件嵌字，并实际导图检查。

原始OFL字体、许可和固定来源记录在`assets/fonts/`；工程`media/fonts/`为实际文字的子集。新增环境图的提示词见`prompts.md`。所有设备、UI与功能关系都是概念演示，不作为产品完成度或测试成果。
