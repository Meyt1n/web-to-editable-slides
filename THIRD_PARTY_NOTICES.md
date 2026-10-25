# 素材与依赖说明

| 资源 | 来源 | 用途 | 许可/说明 |
|---|---|---|---|
| 技能、脚本和提示词 | 本仓库原创 | 流程与自动化 | MIT |
| 绿芽参考封面、流程页、无字背景、主体图 | 宿主内置imagegen生成 | 完全虚构的公开概念示例 | 在维护者拥有或可许可的权利范围内随仓库按MIT提供，不表示对AI输出享有独占权 |
| `assets/demo-font.ttf` | Adobe Source Han Sans系列字体的重命名子集，family为Reading Text SC | 示例中文显示 | SIL OFL 1.1，完整许可见`assets/font-OFL.txt`；字体不适用MIT |
| Pillow | https://github.com/python-pillow/Pillow | 图片清点、预览与图像元数据处理 | MIT-CMU，以其发行包为准 |
| python-pptx | https://github.com/scanny/python-pptx | 构建原生PPTX示例 | MIT，按依赖自身许可使用 |
| PyYAML | https://github.com/yaml/pyyaml | 输出配套PPTD示例 | MIT，按依赖自身许可使用 |

字体原始项目：https://github.com/adobe-fonts/source-han-sans 。示例使用的字体已做子集和名称调整，原始版权及OFL信息保留。OFL字体可与本仓库共同分发，但不能改为本仓库的MIT许可。

第三方Python依赖通过`requirements.txt`安装，不将其源码或二进制打包进仓库。演示文稿技能、imagegen技能、浏览器控制器、本地WASM导出器、Microsoft Office等仅作为工具能力被说明，不作为本仓库的一部分再分发。

示例没有包含真实用户图片、私人对话、真实APP界面、视频或项目代码。生成图仅演示PPT制作方法，不是设备成品或试验成果。
