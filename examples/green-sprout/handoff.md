# 绿芽——桌面植物养护提醒系统：制作交接

用途：演示由网页版参考图重建原生可编辑PPT的流程；主题完全虚构
画幅：16:9
风格：暖白窗边、清新浅绿、珊瑚橙点缀、圆角卡片、柔和产品视觉
主色：#164B3B, #FF816B, #EDF7EF
imagegen使用意向：True（仍以宿主能力与会话权限为准）

## 设计约定

模式：fidelity
- 使用模板：green-sprout-reference / 1.0.0
- 模板位置：../template-extraction/template/template.json（先读取规范与相应页型，再制作页面）
- 字体方案 from-template：heading=Reading Text SC；body=Reading Text SC；display=ZCOOL KuaiLe

素材优先顺序：查找有授权的本地图片 → 展示图按需基于本地图用imagegen优化 → 参考图片局部复刻 → 缺图时新生成概念配图；成果证据保留原图

## 内容与提示词来源

- 公开示例的大纲与提示词：examples/green-sprout/prompts.md；可见范围：public-synthetic

## 01 绿芽：桌面植物养护提醒系统

参考：assets/reference-cover.png
事实状态：concept

对应提示词或来源：examples/green-sprout/prompts.md 的封面参考段；这是等价复现提示词，不是原始调用日志

布局：hero-split
字体方案：from-template

保留的参考排版：
- 左侧标题和说明，右侧独立植物与手机主体
- 左下保留三项功能；右上保留概念演示标记

字体与层级约束：
- 深绿亲和短标题，正文用清晰黑体；具体字体为有许可的近似
- 保留标题、副标题、说明三个层级，不把长句等比例放大

图片来源与处理计划：
- 复用公开本地概念图 assets/product-cutout.png；该图曾以参考封面为imagegen输入生成
- 背景复用同主题无字图；不重复生图，不把展示图写成实拍成果

- 看见植物状态，记住每一次照料
- 状态查看、养护提醒、记录管理

素材位置：
- assets/template-background.png
- assets/product-cutout.png

制作说明：标题与三张功能卡片为原生对象；主体图为自生成概念图

## 02 从植物状态到养护提醒

参考：assets/reference-process.png
事实状态：concept

对应提示词或来源：examples/green-sprout/prompts.md 的流程参考段；等价复现提示词

布局：process-columns
字体方案：from-template

保留的参考排版：
- 左侧主体，右侧四张竖向卡片并列
- 保留01到04和从左到右的阅读顺序，结论放底部

字体与层级约束：
- 深绿标题、浅绿编号、珊瑚橙局部强调；正文层级清楚

图片来源与处理计划：
- 复用与封面相同的本地独立主体和无字背景；卡片、文字、箭头原生制作

- 采集状态 → 整理信息 → 形成提醒 → 记录照料
- 流程为示意，不提供虚构实测指标

素材位置：
- assets/template-background.png
- assets/product-cutout.png

制作说明：四张流程卡片、编号和说明全部原生重建，保留原参考图的视觉关系

## 03 养护服务与交互设计

参考：沿用前两页共性新增章节页
事实状态：concept

布局：statement-chapter
字体方案：from-template

- 查看状态
- 收到提醒
- 记录照料

素材位置：
- assets/template-background.png
- assets/product-cutout.png

制作说明：演示在同一母版上新增章节页，正文和大编号均可编辑
