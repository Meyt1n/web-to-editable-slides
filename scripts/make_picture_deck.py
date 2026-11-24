"""Assemble a static PPTX from numbered, full-resolution renders of a source PPTX."""
from __future__ import annotations

import argparse
from copy import deepcopy
from io import BytesIO
from pathlib import Path
import shutil
from zipfile import ZipFile

from PIL import Image
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.oxml.ns import qn


def assemble(source: Path, rendered: Path, output: Path) -> dict:
    if output.suffix.lower() != ".pptx":
        raise ValueError("The output must be a .pptx file")
    if output.exists():
        raise FileExistsError(f"Choose a new output file: {output}")

    original = Presentation(source)
    expected = [rendered / f"{i:02d}.png" for i in range(1, len(original.slides) + 1)]
    if not expected or set(expected) != set(rendered.glob("*.png")):
        raise ValueError("Render exactly one numbered PNG per source slide, starting at 01.png")
    width, height = original.slide_width, original.slide_height
    deck = Presentation()
    deck.slide_width, deck.slide_height = width, height
    deck.core_properties.title = source.stem + " · 图片版"
    deck.core_properties.author = ""

    pixels = None
    for i, (page, png) in enumerate(zip(original.slides, expected), 1):
        with Image.open(png) as im:
            size = im.size
            if im.format != "PNG" or abs(size[1] - size[0] * height / width) > .5:
                raise ValueError(f"{png.name}: PNG aspect ratio does not match the source canvas")
            if pixels is not None and size != pixels:
                raise ValueError(f"{png.name}: source renders must have a common resolution")
            pixels = size
            im.verify()
        slide = deck.slides.add_slide(deck.slide_layouts[6])
        slide._element.set("showMasterSp", "0")
        if page._element.get("show") == "0":
            slide._element.set("show", "0")
        image = slide.shapes.add_picture(str(png), 0, 0, width, height)
        image.name = f"第 {i:02d} 页 · 整页截图"
        transition = page._element.find(qn("p:transition"))
        if transition is not None and [child.tag for child in transition] == [qn("p:fade")]:
            slide._element.insert_element_before(deepcopy(transition), "p:timing", "p:extLst")

    buffer = BytesIO()
    deck.save(buffer)
    buffer.seek(0)
    with ZipFile(buffer) as archive:
        if archive.testzip() is not None:
            raise ValueError("The output package failed the ZIP integrity check")
    buffer.seek(0)
    reopened = Presentation(buffer)
    if len(reopened.slides) != len(expected) or reopened._element.xpath(".//p:embeddedFontLst"):
        raise ValueError("Unexpected slides or fonts in the output")
    for slide, png in zip(reopened.slides, expected):
        if len(slide.shapes) != 1:
            raise ValueError(f"{png.name}: the page must contain one image only")
        image = slide.shapes[0]
        bounds = (image.left, image.top, image.width, image.height)
        if image.shape_type != MSO_SHAPE_TYPE.PICTURE or bounds != (0, 0, width, height):
            raise ValueError(f"{png.name}: the image must fill the source canvas")
        if image.image.blob != png.read_bytes():
            raise ValueError(f"{png.name}: embedded pixels differ from the render")

    output.parent.mkdir(parents=True, exist_ok=True)
    buffer.seek(0)
    with output.open("xb") as stream:
        shutil.copyfileobj(buffer, stream)
    return {"slides": len(expected), "pixels": pixels, "output": str(output.resolve())}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--rendered-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = assemble(args.source, args.rendered_dir, args.output)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    width, height = result["pixels"]
    print(f"{result['output']} · {result['slides']} pages · {width} × {height}")
