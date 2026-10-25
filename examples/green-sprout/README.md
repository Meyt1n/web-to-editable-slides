# 绿芽：完整的虚构示例

本示例没有任何真实作品素材。两张参考页、无字背景和产品主体均由内置imagegen生成，目的是演示分离“设计参考”和“最终可编辑对象”。

| 输入/输出 | 作用 |
|---|---|
| `../../assets/reference-cover.png` | 带完整文字的封面参考图 |
| `../../assets/reference-process.png` | 四步流程参考图 |
| `../../assets/template-background.png` | 新生成的无字母版 |
| `../../assets/product-cutout.png` | 基于同一虚构主题新生成的透明产品素材 |
| `brief.json`、`handoff.md` | 页码、风格、素材和事实状态的交接 |
| `prompts.md` | 可复制的等价生成提示词 |
| `demo/` | 3页PPTX、PPTD、pages与media完整工程 |
| `preview.jpg` | 实际PPTX渲染后的总览 |
| `verification.json` | 发布前PPTX结构检查 |

参考图和无字背景于早期制作阶段生成，其原始工具提示词未保留。`prompts.md`如实提供用于复现其视觉意图的等价提示词，并单独记录本轮主体图的实际提示词。生成具有随机性，不承诺逐像素重现。

在仓库根目录运行：

```bash
python -m pip install -r requirements.txt
python scripts/make_handoff.py examples/green-sprout/brief.json --output output/handoff.md
python scripts/build_demo.py --output-dir output/green-sprout
python scripts/check_pptx.py output/green-sprout/green-sprout.pptx --require-fade
```

源码构建版本不嵌字体：可以安装`assets/demo-font.ttf`，或选择本机支持中文的替代字体并重新渲染；不安装也可查看PPTD的内置字体预览。Windows上另可用`embed_fonts_windows.ps1`请求PowerPoint嵌字，结果仍须检查。

仓库交付版的实际检查结果见`verification.json`和`validation.md`。它不是已经实现的植物硬件或APP，更不是性能、养护效果或用户试验的证明。
