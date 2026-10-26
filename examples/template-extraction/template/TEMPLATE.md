# 从绿芽封面与流程参考图提取的模板

模板：`green-sprout-reference` / `1.0.0`
画幅：960 × 540
状态：已整理参数（prepared）；脚本不代表视觉检查通过。

## 来源与观测

- [cover](references/01.png)：封面代表图；深绿手写感大标题、暖白窗边与浅木桌面、右侧产品主体、少量珊瑚橙强调，功能标签使用浅色圆角卡片。
- [process](references/02.png)：流程正文代表图；沿用暖白与浅绿，左侧产品、右侧四步竖向卡片，步骤大编号、清楚的短标题和少量连接箭头。

## 固定规范

配色：primary=#164B3B；accent=#FF816B；body=#52655E；pale=#EDF7EF；paper=#FCFFF8；card_border=#D9EADB；chip_border=#D4E8D8；soft_primary=#77A580；icon_fill=#DDEEDD；arrow=#75A77C；white=#FFFFFF
- display：ZCOOL KuaiLe，81 pt
- heading：Reading Text SC，31 pt
- body：Reading Text SC，16.4 pt
- label：Reading Text SC，15 pt
- numeric：Reading Text SC，38 pt
- 网格：{"margins": [32, 40, 32, 40], "gap": 16, "corner_radius": 14}
- 原生组件：card、concept_tag、process_card、footer

## 页型骨架

- `hero-split`：由封面抽象出的左文右图骨架；页内主题图为可替换内容；槽位：panel、hero、title、subtitle、body、features
- `process-columns`：由流程代表图抽象出的主体与四步流程卡片；槽位：heading、hero、cards、conclusion、note
- `statement-chapter`：按相同字体、圆角、留白与图文关系派生的章节页，不声称来自一张未提供的参考图；槽位：panel、number、title、body、features、hero

## 近似、可变项与使用方式

- 参考图的精确字体不可确认，按观测气质选用ZCOOL KuaiLe作封面短标题、Reading Text SC作正文，属于可编辑近似。
- 颜色与布局是基于代表图整理的近似规范，不是自动或像素级提取结果。
- 半透明卡片近似为原生浅色填充与描边，以便编辑与跨软件导出。
- 背景复用已为同一虚构主题生成的无字素材；不把含字参考图作为背景。
- 保持配色、字体角色和图片处理稳定；可在相同网格下增加左右镜像或新的正文变体。
- 标题、编号、说明、流程和卡片使用原生对象，产品主体按页面内容独立替换。
- 正式页面绑定模板ID与版本；新增页型先扩展模板，必要偏离记录原因。
- 后续设计绑定模板ID与版本，先读取页型槽位和组件；文字与事实来自页面内容，不从模板复制。
- 需要新页型时在这些规则内扩展变体，保留修改说明；模板结构检查不能代替样页与整套导图。
