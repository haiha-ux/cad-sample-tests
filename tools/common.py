"""Shared drawing setup: layers, ISO linetypes, text/dim styles, A3 frame, ISO 7200 title block, PDF/DWG export.

All geometry is written with ezdxf (no AutoCAD). `s` = drawing scale factor: 1 for 1:1, 50 for 1:50 —
the frame, title block, text and dimension sizes are multiplied by `s` so the sheet plots at 1:s on A3.
"""
import math
import shutil
import subprocess
import tempfile
from pathlib import Path

import ezdxf
from ezdxf.enums import TextEntityAlignment

ODA = Path(r"C:\Users\USER\tools\oda_fc\ODAFileConverter.exe")
A3 = (420.0, 297.0)


def new_doc(layers: dict[str, tuple[int, str]], s: float = 1.0):
    """layers: name -> (lineweight in 1/100 mm, linetype)."""
    doc = ezdxf.new("R2018", setup=False, units=4)        # 4 = millimetres
    doc.header["$MEASUREMENT"] = 1                         # metric
    doc.header["$LTSCALE"] = s
    doc.header["$PSLTSCALE"] = 0
    doc.header["$LWDISPLAY"] = 1
    # ISO 128-2 patterns for 0.25 mm lines: dash 12d = 3, gap 3d = 0.75; long dash 24d = 6, dot 0.5d.
    doc.linetypes.add("DASHED", pattern=[3.75, 3.0, -0.75], description="ISO dashed __ __ __")
    doc.linetypes.add("CENTER", pattern=[8.5, 6.0, -1.0, 0.5, -1.0],
                      description="ISO long-dash dot ____ . ____")
    for name, (lw, lt) in layers.items():
        doc.layers.add(name, color=7, lineweight=lw, linetype=lt)
    doc.styles.add("ISO", font="isocpeur.ttf")
    doc.styles.add("ISO_ARIAL", font="arial.ttf")          # for Ø, ±, ° and Vietnamese-free symbols
    return doc


def add_dimstyle(doc, name, s=1.0, txt=3.5, asz=3.0, arch=False):
    ds = doc.dimstyles.add(name)
    ds.dxf.dimtxsty = "ISO"
    ds.dxf.dimscale = s
    ds.dxf.dimtxt = txt
    ds.dxf.dimasz = asz
    ds.dxf.dimexe = 2.0
    ds.dxf.dimexo = 1.0
    ds.dxf.dimgap = 1.0
    ds.dxf.dimtad = 1           # text above dimension line (ISO 129)
    ds.dxf.dimtih = 0           # text aligned with dimension line
    ds.dxf.dimtoh = 0
    ds.dxf.dimdec = 2
    ds.dxf.dimzin = 8           # suppress trailing zeros: 120.00 -> 120, 6.60 -> 6.6
    ds.dxf.dimdsep = ord(".")
    ds.dxf.dimlunit = 2         # decimal
    ds.dxf.dimtdec = 1
    ds.dxf.dimtzin = 8
    if arch:
        ds.dxf.dimtsz = 1.5     # oblique ticks instead of arrows (architectural)
        ds.dxf.dimdle = 1.5
    return ds


def frame(msp, s=1.0, layer="TITLE"):
    """A3 sheet: trimmed edge 420x297, ISO 5457 frame 20 mm left / 10 mm others."""
    w, h = A3
    msp.add_lwpolyline([(0, 0), (w * s, 0), (w * s, h * s), (0, h * s)], close=True,
                       dxfattribs={"layer": layer, "lineweight": 18})
    msp.add_lwpolyline([(20 * s, 10 * s), ((w - 10) * s, 10 * s), ((w - 10) * s, (h - 10) * s),
                        (20 * s, (h - 10) * s)], close=True, dxfattribs={"layer": layer, "lineweight": 70})


def text(msp, x, y, t, h, layer="TEXT", align=TextEntityAlignment.BOTTOM_LEFT, style="ISO", rot=0.0):
    e = msp.add_text(t, height=h, rotation=rot, dxfattribs={"layer": layer, "style": style})
    e.set_placement((x, y), align=align)
    return e


def first_angle_symbol(msp, x, y, s=1.0, layer="TITLE"):
    """ISO 5456-2 first-angle symbol: truncated cone side view on the LEFT, circles on the RIGHT."""
    k = s
    msp.add_lwpolyline([(x, y + 1.5 * k), (x + 6 * k, y), (x + 6 * k, y + 6 * k), (x, y + 4.5 * k)], close=True,
                       dxfattribs={"layer": layer})
    cx = x + 11 * k
    msp.add_circle((cx, y + 3 * k), 3 * k, dxfattribs={"layer": layer})
    msp.add_circle((cx, y + 3 * k), 1.5 * k, dxfattribs={"layer": layer})
    for a, b in (((x - 1 * k, y + 3 * k), (x + 7 * k, y + 3 * k)), ((cx - 4 * k, y + 3 * k), (cx + 4 * k, y + 3 * k)),
                 ((cx, y - 1 * k), (cx, y + 7 * k))):
        msp.add_line(a, b, dxfattribs={"layer": "CENTER" if "CENTER" in [l.dxf.name for l in msp.doc.layers] else layer})


def roughness_symbol(msp, x, y, value, s=1.0, layer="TEXT"):
    """ISO 21920-1 / 1302 basic symbol 'material removal required' with Ra value on the long leg."""
    k = s
    h1 = 5 * k                        # short-leg height for 3.5 mm text
    p0 = (x, y)
    p1 = (x - h1 * math.tan(math.radians(30)), y + h1)
    p2 = (x + 2 * h1 * math.tan(math.radians(30)), y + 2 * h1)
    msp.add_line(p1, p0, dxfattribs={"layer": layer})
    msp.add_line(p0, p2, dxfattribs={"layer": layer})
    msp.add_line(p1, (p0[0] + h1 * math.tan(math.radians(30)), p1[1]), dxfattribs={"layer": layer})  # removal bar
    msp.add_line(p2, (p2[0] + 14 * k, p2[1]), dxfattribs={"layer": layer})
    text(msp, p2[0] + 1 * k, p2[1] - 4.5 * k, value, 3.5 * k, layer)


def roughness_general(msp, x, y, value, s=1.0, layer="TEXT"):
    """ISO 1302 general surface texture requirement placed by the title block:  ✓Ra 3.2 ( ✓ )."""
    roughness_symbol(msp, x, y, value, s, layer)
    k = s
    px = x + 25 * k
    text(msp, px, y + 2 * k, "(", 7 * k, layer)
    sym = (px + 6 * k, y + 2.5 * k)
    h1 = 3 * k
    t30 = math.tan(math.radians(30))
    msp.add_line((sym[0] - h1 * t30, sym[1] + h1), sym, dxfattribs={"layer": layer})
    msp.add_line(sym, (sym[0] + 2 * h1 * t30, sym[1] + 2 * h1), dxfattribs={"layer": layer})
    msp.add_line((sym[0] - h1 * t30, sym[1] + h1), (sym[0] + h1 * t30, sym[1] + h1), dxfattribs={"layer": layer})
    text(msp, px + 10 * k, y + 2 * k, ")", 7 * k, layer)


def title_block(msp, s, rows, layer="TITLE"):
    """ISO 7200 style block, 180 mm wide, bottom-right inside the frame.
    rows: list of lists of (label, value, width_mm); drawn bottom-up, each row 8 mm high."""
    x0, y0, rh = (410 - 180) * s, 10 * s, 8 * s
    y = y0
    for row in rows:
        x = x0
        for label, value, wmm in row:
            w = wmm * s
            msp.add_lwpolyline([(x, y), (x + w, y), (x + w, y + rh), (x, y + rh)], close=True,
                               dxfattribs={"layer": layer, "lineweight": 35})
            text(msp, x + 1 * s, y + rh - 2.6 * s, label, 1.8 * s, layer)
            if value:
                text(msp, x + 1.5 * s, y + 1.4 * s, value, 3.5 * s if len(value) < 26 else 2.5 * s, layer)
            x += w
        assert abs(x - x0 - 180 * s) < 1e-6, f"title block row width {(x - x0) / s} mm != 180"
        y += rh
    return x0, y0, y


def export_pdf(doc, pdf_path: Path, scale: float):
    """Render model space to a real A3 PDF page at 1:scale using ezdxf's drawing add-on (PyMuPDF backend)."""
    from ezdxf.addons.drawing import Frontend, RenderContext, config, layout, pymupdf
    backend = pymupdf.PyMuPdfBackend()
    cfg = config.Configuration(background_policy=config.BackgroundPolicy.WHITE,
                               color_policy=config.ColorPolicy.BLACK,
                               lineweight_policy=config.LineweightPolicy.ABSOLUTE,
                               lineweight_scaling=1.0)
    Frontend(RenderContext(doc), backend, config=cfg).draw_layout(doc.modelspace(), finalize=True)
    page = layout.Page(A3[0], A3[1], layout.Units.mm, margins=layout.Margins.all(0))
    pdf = backend.get_pdf_bytes(page, settings=layout.Settings(scale=1.0 / scale, fit_page=False))
    pdf_path.write_bytes(pdf)


def export_dwg(dxf_path: Path, dwg_dir: Path):
    """DXF -> DWG (AutoCAD 2018 format) with ODA File Converter; returns the DWG path."""
    tmp_in, tmp_out = Path(tempfile.mkdtemp()), Path(tempfile.mkdtemp())
    shutil.copy(dxf_path, tmp_in / dxf_path.name)
    subprocess.run([str(ODA), str(tmp_in), str(tmp_out), "ACAD2018", "DWG", "0", "1", "*.DXF"],
                   check=True, timeout=120)
    out = tmp_out / (dxf_path.stem + ".dwg")
    assert out.exists() and out.stat().st_size > 0, "ODA khong tao DWG"
    dst = dwg_dir / out.name
    shutil.copy(out, dst)
    return dst


def dwg_roundtrip_count(dwg_path: Path) -> dict:
    """Independent check: DWG -> DXF again with ODA, read with ezdxf, count entities by type/layer."""
    tmp_in, tmp_out = Path(tempfile.mkdtemp()), Path(tempfile.mkdtemp())
    shutil.copy(dwg_path, tmp_in / dwg_path.name)
    subprocess.run([str(ODA), str(tmp_in), str(tmp_out), "ACAD2018", "DXF", "0", "1", "*.DWG"],
                   check=True, timeout=120)
    back = ezdxf.readfile(tmp_out / (dwg_path.stem + ".dxf"))
    cnt = {}
    for e in back.modelspace():
        cnt[e.dxftype()] = cnt.get(e.dxftype(), 0) + 1
    return cnt
