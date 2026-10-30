"""Test B — studio floor plan, 1:50, mm. Model space at full size; sheet, text and dims scaled x50.

Coordinates: clear interior x 0..6000, y 0..4500 (origin = inner bottom-left corner), walls 200 outside that.
"""
import math
from pathlib import Path

import ezdxf
from ezdxf.enums import TextEntityAlignment as TA

import common as C

OUT = Path(__file__).resolve().parent.parent / "bai_b"
S = 50.0
L = {"WALL": (50, "Continuous"), "DOOR": (25, "Continuous"), "WINDOW": (35, "Continuous"),
     "DIM": (18, "Continuous"), "TEXT": (25, "Continuous"), "FURN": (18, "Continuous"),
     "TITLE": (35, "Continuous"), "CENTER": (18, "CENTER")}

IW, IH, WT = 6000.0, 4500.0, 200.0                  # clear interior, wall thickness
DOOR_X0, DOOR_W = 600.0, 900.0                      # bottom wall, hinge at the left jamb, opens inward
WIN_W = 1200.0
WIN_TOP = ((IW - WIN_W) / 2, (IW + WIN_W) / 2)      # centred on the top wall
WIN_RIGHT = ((IH - WIN_W) / 2, (IH + WIN_W) / 2)    # centred on the right wall
WC_W, WC_H, PT = 1800.0, 1500.0, 100.0              # WC clear size, partition thickness
WC_Y0 = IH - WC_H                                    # 3000: WC clear starts here
WCD_Y0, WCD_W = 3200.0, 700.0                        # WC door in the vertical partition, opens out to the studio

OX, OY = 3400.0, 4200.0                              # sheet position of interior origin (model units)


def M(x, y):
    return OX + x, OY + y


def rect(x0, y0, x1, y1):
    return [M(x0, y0), M(x1, y0), M(x1, y1), M(x0, y1)]


def wall_pieces():
    """Solid wall rectangles (openings left out)."""
    e, t = -WT, IW + WT
    return [
        (e, -WT, DOOR_X0, 0), (DOOR_X0 + DOOR_W, -WT, t, 0),                     # bottom wall, door gap
        (e, IH, WIN_TOP[0], IH + WT), (WIN_TOP[1], IH, t, IH + WT),             # top wall, window gap
        (e, 0, 0, IH),                                                          # left wall
        (IW, 0, t, WIN_RIGHT[0]), (IW, WIN_RIGHT[1], t, IH),                    # right wall, window gap
        (0, WC_Y0 - PT, WC_W + PT, WC_Y0),                                      # WC horizontal partition
        (WC_W, WC_Y0, WC_W + PT, WCD_Y0), (WC_W, WCD_Y0 + WCD_W, WC_W + PT, IH),  # WC vertical partition, door gap
    ]


def build():
    doc = C.new_doc(L, s=S)
    ds = C.add_dimstyle(doc, "ARCH-50", s=S, txt=2.5, asz=2.0, arch=True)
    ds.dxf.dimdec = 0
    msp = doc.modelspace()
    C.frame(msp, s=S)

    # ---- walls: outline + solid poche ----
    hatch = msp.add_hatch(dxfattribs={"layer": "WALL"})
    hatch.set_pattern_fill("ANSI31", scale=S * 0.4)
    for x0, y0, x1, y1 in wall_pieces():
        msp.add_lwpolyline(rect(x0, y0, x1, y1), close=True, dxfattribs={"layer": "WALL"})
        hatch.paths.add_polyline_path(rect(x0, y0, x1, y1), is_closed=True)

    # ---- windows: wall faces + double glazing line ----
    def window_h(x0, x1, y_in, y_out):
        for y in (y_in, (y_in + y_out) / 2, y_out):               # 3-line symbol: faces + glass
            msp.add_line(M(x0, y), M(x1, y), dxfattribs={"layer": "WINDOW"})

    def window_v(y0, y1, x_in, x_out):
        for x in (x_in, (x_in + x_out) / 2, x_out):
            msp.add_line(M(x, y0), M(x, y1), dxfattribs={"layer": "WINDOW"})

    window_h(*WIN_TOP, IH, IH + WT)
    window_v(*WIN_RIGHT, IW, IW + WT)

    # ---- doors: leaf (40 thick, drawn open 90 deg) + swing arc ----
    def door(hinge, leaf_dir, closed_dir, width):
        hx, hy = hinge
        lx, ly = leaf_dir
        cx_, cy_ = closed_dir
        tip = (hx + lx * width, hy + ly * width)
        nx, ny = -ly * 40 if lx == 0 else 0, lx * 40 if ly == 0 else 0
        side = 1 if (cx_ * (ly) - cy_ * (lx)) > 0 else -1
        leaf = [(hx, hy), tip, (tip[0] + cx_ * 40, tip[1] + cy_ * 40), (hx + cx_ * 40, hy + cy_ * 40)]
        msp.add_lwpolyline([M(*p) for p in leaf], close=True, dxfattribs={"layer": "DOOR"})
        a_closed = math.degrees(math.atan2(cy_, cx_))
        a_open = math.degrees(math.atan2(ly, lx))
        start, end = (a_closed, a_open) if ((a_open - a_closed) % 360) == 90 else (a_open, a_closed)
        msp.add_arc(M(hx, hy), width, start, end, dxfattribs={"layer": "DOOR"})
        return tip

    door((DOOR_X0, 0.0), (0, 1), (1, 0), DOOR_W)                      # main door: hinge left jamb, opens inward
    door((WC_W + PT, WCD_Y0), (1, 0), (0, 1), WCD_W)                  # WC door: hinge low jamb, opens to studio

    # ---- sanitary fixtures (FURN) ----
    msp.add_lwpolyline(rect(1250, IH - 200, 1650, IH), close=True, dxfattribs={"layer": "FURN"})   # cistern
    msp.add_ellipse(M(1450, IH - 450), major_axis=(0, 260), ratio=0.7, dxfattribs={"layer": "FURN"})  # WC pan
    msp.add_lwpolyline(rect(150, IH - 450, 650, IH), close=True, dxfattribs={"layer": "FURN"})     # basin unit

    # ---- room names + areas (clear floor area, partitions excluded) ----
    a_wc = WC_W * WC_H / 1e6
    a_studio = IW * IH / 1e6 - (WC_W + PT) * (WC_H + PT) / 1e6
    for name, area, (x, y) in (("STUDIO", a_studio, (3900, 2000)), ("WC", a_wc, (800, 3300))):
        C.text(msp, *M(x, y), name, 3.5 * S, align=TA.BOTTOM_CENTER)
        C.text(msp, *M(x, y - 80), f"{area:.2f} m²", 2.5 * S, align=TA.TOP_CENTER)

    # ---- chain dimensions outside the walls ----
    d = dict(dimstyle="ARCH-50", dxfattribs={"layer": "DIM"})
    dims = []

    def chain(points, fixed, outward, horizontal):
        off1, off2 = outward * (WT + 600), outward * (WT + 1300)
        for a, b in zip(points, points[1:]):
            if horizontal:
                dims.append(msp.add_linear_dim(base=M(0, fixed + off1), p1=M(a, fixed), p2=M(b, fixed), **d))
            else:
                dims.append(msp.add_linear_dim(base=M(fixed + off1, 0), p1=M(fixed, a), p2=M(fixed, b),
                                               angle=90, **d))
        a, b = points[0], points[-1]
        if horizontal:
            dims.append(msp.add_linear_dim(base=M(0, fixed + off2), p1=M(a, fixed), p2=M(b, fixed), **d))
        else:
            dims.append(msp.add_linear_dim(base=M(fixed + off2, 0), p1=M(fixed, a), p2=M(fixed, b),
                                           angle=90, **d))

    chain([-WT, 0, DOOR_X0, DOOR_X0 + DOOR_W, IW, IW + WT], -WT, -1, True)              # bottom
    chain([-WT, 0, WIN_TOP[0], WIN_TOP[1], IW, IW + WT], IH + WT, +1, True)            # top
    chain([-WT, 0, WIN_RIGHT[0], WIN_RIGHT[1], IH, IH + WT], IW + WT, +1, False)       # right
    chain([-WT, 0, WC_Y0 - PT, WC_Y0, IH, IH + WT], -WT, -1, False)                    # left (incl. partition)
    # WC clear size inside
    # WC clear width (its 1500 depth is already in the left chain)
    dims.append(msp.add_linear_dim(base=M(0, 3700), p1=M(0, 3700), p2=M(WC_W, 3700), **d))
    for dm in dims:
        dm.render()

    # ---- notes + title block ----
    notes = ["NOTES:", "1. DIMENSIONS IN mm, SCALE 1:50 ON A3.", "2. WALLS 200, WC PARTITIONS 100.",
             "3. AREAS ARE CLEAR FLOOR AREAS.", "4. WC DOOR OPENS OUTWARD TO THE STUDIO."]
    for i, t in enumerate(notes):
        C.text(msp, 260 * S, (250 - i * 7) * S, t, (3.5 if i == 0 else 3.0) * S)
    C.title_block(msp, S, [
        [("SCALE", "1:50", 25), ("PROJECTION", "-", 30), ("SIZE", "A3", 20), ("SHEET", "1/1", 20),
         ("DRAWING NO.", "CST-B-001", 85)],
        [("DRAWN BY", "H. Ha", 45), ("DATE", "2026-10-30", 45), ("TOTAL CLEAR AREA", f"{IW * IH / 1e6:.2f} m²", 90)],
        [("TITLE", "STUDIO APARTMENT - FLOOR PLAN", 120), ("REV", "A", 20), ("UNITS", "mm", 40)],
        [("LEGAL OWNER", "Ha Phan Thanh Hai", 180)],
    ])
    return doc, dims, a_studio, a_wc


def check(doc, dims, a_studio, a_wc):
    msp = doc.modelspace()
    meas = [round(dm.dimension.get_measurement()) for dm in dims]
    want_bottom = [200, 600, 900, 4500, 200, 6400]
    want_top = [200, 2400, 1200, 2400, 200, 6400]
    want_right = [200, 1650, 1200, 1650, 200, 4900]
    want_left = [200, 2900, 100, 1500, 200, 4900]
    assert meas[:24] == want_bottom + want_top + want_right + want_left, meas
    assert meas[24:] == [1800], meas[24:]
    assert abs(a_studio - 23.96) < 1e-9 and abs(a_wc - 2.70) < 1e-9
    arcs = sorted(round(a.dxf.radius) for a in msp.query("ARC[layer=='DOOR']"))
    assert arcs == [700, 900], arcs
    assert WIN_TOP == (2400, 3600) and WIN_RIGHT == (1650, 2850)
    for name, (lw, lt) in L.items():
        assert doc.layers.get(name).dxf.lineweight == lw
    return {"dims": len(dims), "measurements": meas, "studio_m2": round(a_studio, 2), "wc_m2": a_wc}


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    doc, dims, a_s, a_w = build()
    info = check(doc, dims, a_s, a_w)
    dxf = OUT / "CST-B-001_studio_plan.dxf"
    doc.saveas(dxf)
    doc2 = ezdxf.readfile(dxf)
    auditor = doc2.audit()
    assert not auditor.has_errors, auditor.errors
    C.export_pdf(doc2, OUT / "CST-B-001_studio_plan.pdf", scale=S)
    dwg = C.export_dwg(dxf, OUT)
    print("check:", info)
    print("audit errors:", len(auditor.errors))
    print("dwg roundtrip:", C.dwg_roundtrip_count(dwg))
