"""Build editable, content-neutral sample slides from the Qiheng pixel template."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory

from native_renderer import build
from template_pack import inside, load_template


TEMPLATE = Path(__file__).resolve().parents[1] / "assets/templates/qiheng-pixel"


def create_scene(theme, resources, portable):
    palette = theme["palette"]
    typography = theme["typography"]
    components = theme["components"]
    portable_fonts = theme["portable_fonts"] if portable else {}
    pages = []
    elements = []

    def label(key, box, value, role, *, color=None, align="left"):
        style = typography[role]
        family = style["family"]
        elements.append({"elementId": key, "bounds": box, "elementType": "text", "content": {
            "text": value, "fontFamily": portable_fonts.get(family, family),
            "fontSize": style["size"], "bold": style.get("bold", False),
            "color": palette[color or style["color"]], "align": [align, "middle"],
            "wrap": False, "lineHeight": 1.08,
        }})

    def shape(key, box, swatch, *, component=None, opacity=1):
        _, _, w, h = box
        element = {"elementId": key, "bounds": box, "elementType": "shape",
                   "shapeName": "rect", "opacity": opacity,
                   "fill": {"type": "solid", "color": palette[swatch]} if swatch else {"type": "none"}}
        if component:
            style = components[component]
            d = style["step"]
            path = (f"M {2*d} 0 H {w-2*d} V {d} H {w-d} V {2*d} H {w} V {h-2*d} "
                    f"H {w-d} V {h-d} H {w-2*d} V {h} H {2*d} V {h-d} H {d} V {h-2*d} "
                    f"H 0 V {2*d} H {d} V {d} H {2*d} Z")
            element.update(shapeName="custom", viewBox=[w, h], path=path,
                           border={"color": palette[style["edge"]], "width": style["edge-width"]})
        elements.append(element)

    def picture(key, box, resource, reason, fit="contain"):
        elements.append({"elementId": key, "bounds": box, "elementType": "image",
                         "src": resources[resource], "fit": {"mode": fit}, "raster_reason": reason})

    def start(layout, title=None, tag=None):
        nonlocal elements
        elements = []
        page = {"id": len(pages) + 1, "pageType": layout if layout in ("cover", "closing") else "content",
                "layout": layout, "background": {"type": "solid", "color": palette["base"]},
                "elements": elements}
        pages.append(page)
        artwork = "sunset-backdrop" if layout in ("cover", "closing") else "body-backdrop"
        picture("无字背景", [0, 0, *theme["canvas"]], artwork, "独立 ImageGen 像素底图", "cover")
        header = components["header"]
        shape("页眉低对比衬底", header["shade"], "header-shade", opacity=header["shade-opacity"])
        label("页眉", header["brand"], "SYSTEM LAB  /  汇报模板", "label", color="light")
        if title:
            label("主标题", header["heading"], title, "heading")
            shape("标题分隔线", header["rule"], "divider")
        if tag:
            shape("页签底", header["tag"], "paper", component="chip")
            label("页签", header["tag"], tag, "label", align="center")
        return theme["layouts"][layout]["slots"]

    def finish(conclusion, source):
        bar = components["conclusion"]
        shape("结论底框", bar["bounds"], bar["fill"], component="chip")
        shape("结论方点", bar["marker"], "purple-accent")
        label("本页结论", bar["text"], conclusion, "conclusion")
        footer = components["footer"]
        shape("页脚低对比衬底", footer["shade"], "footer-shade", opacity=footer["shade-opacity"])
        shape("页脚细线", footer["rule"], "divider")
        label("数据口径占位", footer["source"], source, "caption", color="light")

    def panel(key, box, heading):
        shape(key, box, "paper", component="card")
        x, y, w, h = box
        pad = components["card"]["inset"]
        shape(key + "内框", [x + pad, y + pad, w - 2 * pad, h - 2 * pad], None, component="inner-border")
        shape(key + "标题色标", [x + 15, y + 18, 5, 16], "purple-accent")
        label(key + "标题", [x + 26, y + 11, w - 48, 30], heading, "subheading")

    def metric(key, box, amount, title, tint="highlight"):
        x, y, w, h = box
        shape(key + "卡", box, tint, component="kpi")
        label(key, [x + 8, y + 2, w - 16, h * .60], amount, "metric", align="center")
        label(key + "说明", [x + 8, y + h * .61, w - 16, h * .34], title, "caption", align="center")

    def table(key, box, rows):
        style = typography["table"]
        cells = [[{"text": value, "fontFamily": portable_fonts.get(style["family"], style["family"]),
                   "fontSize": style["size"], "color": palette["ink"], "bold": i == 0,
                   "align": ["left" if j == 0 else "center", "middle"],
                   "fill": {"type": "solid", "color": palette[
                       ("table-highlight-header" if i == 0 else "highlight") if j == 2
                       else "table-header" if i == 0 else "inset" if i % 2 else "table-alternate"]}}
                  for j, value in enumerate(row)] for i, row in enumerate(rows)]
        elements.append({"elementId": key, "elementType": "table", "bounds": box,
                         "rows": cells, "columnWidths": [.43, .285, .285],
                         "rowHeights": [1 / len(rows)] * len(rows)})

    slots = start("cover")
    label("封面标题", slots["title"], "系统实验报告", "cover-title")
    label("封面副标题", slots["subtitle"], "面向智能任务的运行时设计与验证", "subheading", color="light")
    shape("封面分隔线", [42, 263, 463, 3], "divider")
    label("封面资料", slots["info"], "项目组名称  /  课程讨论课", "label", color="light")
    for box, key, icon in zip(slots["layers"], ("应用与交互", "运行时服务", "系统底座"),
                              ("spreadsheet", "latency", "checkpoint")):
        x, y, w, h = box
        shape(key + "卡", box, "paper", component="card")
        picture(key + "图标", [x + 14, y + 13, 44, 42], icon, "透明点阵主题插画")
        label(key, [x + 72, y, w - 90, h], key, "subheading")

    slots = start("architecture", "原型系统分层架构", "系统架构")
    panel("系统分层", slots["layers"], "系统分层")
    panel("设计决策", slots["decisions"], "设计决策")
    for index, (box, (title, description)) in enumerate(zip(slots["rows"], (
        ("应用与交互", "提交与观察任务"),
        ("运行时服务", "调度、工具权限与任务状态"),
        ("进程与通信", "启动、消息传递与身份校验"),
        ("系统底座", "复用内核和基本系统服务"),
    )), 1):
        x, y, w, h = box
        shape(title + "卡", box, "inset", component="chip")
        label(title, [x + 14, y, 174, h], title, "label")
        shape(f"分层竖线{index}", [x + 181, y + 11, 1, h - 22], "edge")
        label(title + "职责", [x + 196, y, w - 211, h], description, "body")
    for index, (title, icon) in enumerate((
        ("管理工作步骤", "latency"), ("核对工具授权", "spreadsheet"), ("保存任务状态", "checkpoint"),
    )):
        y = 162 + 75 * index
        shape(title + "卡", [636, y, 275, 57], "status", component="chip")
        picture(title + "图标", [650, y + 12, 33, 33], icon, "透明点阵主题插画")
        label(title, [697, y, 200, 57], title, "label")
    finish("按职责区分应用、运行时与系统底座。", "版式示例  ·  按项目替换分层与设计决策")

    slots = start("paper", "原论文图与关键机制", "学术调研")
    panel("论文图区", slots["figure"], "论文原图")
    panel("读图区", slots["reading-notes"], "读图重点")
    shape("论文图占位", slots["figure-image"], "inset", component="chip")
    label("论文图提示", [67, 259, 504, 49], "按原比例置入论文图版", "subheading", align="center")
    label("出处图注", [46, 422, 546, 21], "作者 · 年份 · 论文名 · 图号", "caption", align="center")
    for i, value in enumerate(("图中的主要模块", "数据或请求的路径", "与本项目相关的机制")):
        y = 164 + 72 * i
        shape(value + "卡", [635, y, 277, 53], "status", component="chip")
        label(value, [651, y, 244, 53], value, "label")
    finish("用原图定位机制，再说明它如何影响本项目。", "版式示例  ·  正式页附论文出处和图号")

    slots = start("evidence", "实验数据与实机截图", "实测验证")
    panel("数据区", slots["data"], "实测数据（ms）")
    panel("证据区", slots["evidence"], "系统运行截图")
    metric("首个响应", slots["kpi"], "120 → 80 ms", "首个响应中位数  ·  示例数据")
    table("实测表", slots["table"], [["指标", "基线", "实验组"], ["P50（ms）", "120", "80"],
                                   ["P95（ms）", "180", "130"], ["完成数", "20 / 20", "20 / 20"]])
    shape("截图位", slots["screenshot"], "base", component="chip")
    shape("窗口标题栏", [502, 168, 405, 29], "header-shade")
    label("截图窗口标签", [513, 170, 350, 25], "SYSTEM  /  运行记录", "label", color="light")
    label("截图占位提示", [515, 246, 380, 57], "在此放对应实机截图", "subheading", color="light", align="center")
    label("截图图注", slots["caption"], "图注写明系统版本与截图对应的实验", "caption", align="center")
    finish("示例中首个响应的中位数下降。", "示例数据  ·  正式页注明版本、样本数和计时边界")

    slots = start("comparison", "基线与新方案的表现对比", "数据对比")
    panel("基线面板", slots["baseline"], "单任务")
    panel("对比面板", slots["candidate"], "混合负载")
    label("基线说明", [62, 161, 380, 29], "完整回包中位数（ms）", "body")
    for index, (title, value, swatch) in enumerate((
        ("基线", 120, "purple-accent"), ("新方案", 145, "highlight-ink"),
    )):
        y = 213 + index * 89
        label(title, [62, y, 150, 31], title, "subheading")
        label(title + "数值", [265, y - 3, 159, 38], f"{value} ms", "metric", align="right")
        shape(title + "刻度", [62, y + 38, 362, 13], "status")
        shape(title + "条形", [62, y + 38, 362 * value / 160, 13], swatch)
    table("混合负载表", slots["comparison-table"], [
        ["指标（ms）", "基线", "新方案"], ["前台 P95", "120", "80"], ["后台 P95", "150", "180"],
    ])
    metric("前台变化", slots["tradeoffs"][0], "−40 ms", "前台 P95 变化")
    metric("后台变化", slots["tradeoffs"][1], "+30 ms", "后台 P95 变化", "tradeoff")
    finish("该组示例中前台等待缩短，后台等待增加。", "示例数据  ·  对照来自同一计时口径")

    slots = start("closing")
    for box, value in zip(slots["highlights"], ("问题与设计", "实测结果", "适用条件")):
        shape(value + "卡", box, "paper", component="card")
        label(value, box, value, "subheading", align="center")
    label("致谢", slots["thanks"], "感谢倾听", "cover-title", align="center")
    shape("讨论底框", slots["discussion"], "status", component="chip")
    label("讨论提示", slots["discussion"], "讨论  /  哪些负载值得启用这项机制？", "body", align="center")

    return {"version": 1, "title": "启衡式灰紫像素模板 · 可编辑样页",
            "size": theme["canvas"], "template_file": "template/template.json", "pages": pages}


def sample(output, portable):
    output = output.resolve()
    if output.exists():
        raise ValueError("Choose a fresh output directory.")
    theme = load_template(TEMPLATE / "template.json")
    assets = {"body-backdrop": theme["resources"]["background"], **theme["resources"]["images"]}
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="qiheng-sample-", dir=output.parent) as work:
        source = Path(work)
        shutil.copytree(TEMPLATE, source / "template")
        for target in assets.values():
            destination = source / target
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(inside(TEMPLATE, target), destination)
        scene = create_scene(theme, assets, portable)
        (source / "scene.json").write_text(json.dumps(scene, ensure_ascii=False, indent=2), encoding="utf-8")
        return build(source / "scene.json", output)


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--output-dir", type=Path, required=True)
    cli.add_argument("--portable-fonts", action="store_true")
    args = cli.parse_args()
    print(sample(args.output_dir, args.portable_fonts))
