"""Test A — mounting plate 120x80x6, AL 6061. A3 landscape, 1:1, first-angle (ISO E) projection.

Part coordinates: x 0..120, y 0..80 (front view, origin bottom-left), z 0..6 (thickness, z=6 faces the viewer).
Sheet placement (first angle): plan view BELOW the front view, left-side view to the RIGHT.
"""
import math
from pathlib import Path

import ezdxf
from ezdxf.enums import TextEntityAlignment as TA

import common as C

OUT = Path(__file__).resolve().parent.parent / "bai_a"
L = {"OUTLINE": (50, "Continuous"), "HIDDEN": (25, "DASHED"), "CENTER": (18, "CENTER"), "DIM": (18, "Continuous"),
     "TEXT": (25, "Continuous"), "TITLE": (35, "Continuous"), "HATCH": (18, "Continuous")}

# ---- part geometry (single source of truth; checked at the end) ----
W, H, T = 120.0, 80.0, 6.0
HOLES = [(10, 10), (110, 10), (10, 70), (110, 70)]
HOLE_D = 6.6
SLOT_C, SLOT_LEN, SLOT_W = (60.0, 40.0), 30.0, 8.0          # centre, centre-to-centre length, width (R4 ends)
FILLET, CHAMFER = 3.0, 5.0
TAP_X, TAP_D, TAP_DRILL, TAP_DEPTH, DRILL_DEPTH = 60.0, 5.0, 4.2, 10.0, 12.0   # M5: tap drill 4.2 (ISO 2306)

FX, FY = 60.0, 160.0          # front view origin on the sheet
T0 = FY - 28.0                # plan view: z = 0 (back face) line; z grows DOWNWARD (first angle)
SX = FX + W + 40.0            # left view: z = 0 at SX, z grows to the RIGHT (first angle)
AX, AY = 245.0, T0 - T        # section A-A origin (x along part x, y along z)


def F(x, y):  # front view
    return FX + x, FY + y


def P(x, z):  # plan view (from above)
    return FX + x, T0 - z


def S(z, y):  # left-side view
    return SX + z, FY + y


def outline_front(msp):
    b = math.tan(math.radians(90) / 4)        # bulge of a 90 deg arc
    r, c = FILLET, CHAMFER
    pts = [(r, 0, 0), (W - r, 0, b), (W, r, 0), (W, H - c, 0), (W - c, H, 0), (r, H, b), (0, H - r, 0), (0, r, b)]
    msp.add_lwpolyline([(*F(x, y), 0, 0, bg) for x, y, bg in pts], format="xyseb", close=True,
                       dxfattribs={"layer": "OUTLINE"})


def slot_front(msp):
    (cx, cy), h, r = SLOT_C, SLOT_LEN / 2, SLOT_W / 2
    pts = [(cx - h, cy - r, 0), (cx + h, cy - r, 1), (cx + h, cy + r, 0), (cx - h, cy + r, 1)]
    msp.add_lwpolyline([(*F(x, y), 0, 0, bg) for x, y, bg in pts], format="xyseb", close=True,
                       dxfattribs={"layer": "OUTLINE"})


def cl(msp, a, b):
    msp.add_line(a, b, dxfattribs={"layer": "CENTER"})


def hid(msp, a, b):
    msp.add_line(a, b, dxfattribs={"layer": "HIDDEN"})


def ol(msp, a, b):
    msp.add_line(a, b, dxfattribs={"layer": "OUTLINE"})


def tapped_hole_profile(hx, hy0, sign, axis_view):
    """Hidden-line profile of the M5 blind tapped hole (thread depth 10, tap-drill 4.2 to 12, 118 deg point).
    axis_view(u, v): u = across the axis, v = along the axis (from the entry face)."""
    rd, rm = TAP_DRILL / 2, TAP_D / 2
    tip = DRILL_DEPTH + rd / math.tan(math.radians(59))
    segs = [((-rm, 0), (-rm, TAP_DEPTH)), ((rm, 0), (rm, TAP_DEPTH)), ((-rm, TAP_DEPTH), (rm, TAP_DEPTH)),
            ((-rd, 0), (-rd, DRILL_DEPTH)), ((rd, 0), (rd, DRILL_DEPTH)),
            ((-rd, DRILL_DEPTH), (0, tip)), ((rd, DRILL_DEPTH), (0, tip))]
    return [(axis_view(u, v1), axis_view(u2, v2)) for (u, v1), (u2, v2) in segs], tip


def build():
    doc = C.new_doc(L)
    C.add_dimstyle(doc, "ISO-A", s=1.0)
    msp = doc.modelspace()
    C.frame(msp)

    # ===== FRONT VIEW =====
    outline_front(msp)
    slot_front(msp)
    for hx, hy in HOLES:
        msp.add_circle(F(hx, hy), HOLE_D / 2, dxfattribs={"layer": "OUTLINE"})
        cl(msp, F(hx - 6, hy), F(hx + 6, hy))
        cl(msp, F(hx, hy - 6), F(hx, hy + 6))
    (sx, sy), h = SLOT_C, SLOT_LEN / 2
    cl(msp, F(sx - h - 7, sy), F(sx + h + 7, sy))
    for ex in (sx - h, sx + h):
        cl(msp, F(ex, sy - 7), F(ex, sy + 7))
    segs, tip = tapped_hole_profile(TAP_X, 0, 1, lambda u, v: F(TAP_X + u, v))
    for a, b in segs:
        hid(msp, a, b)
    cl(msp, F(TAP_X, -3), F(TAP_X, tip + 3))

    # ===== PLAN VIEW (looking down -y; first angle: below the front view, front face z=6 at the bottom) =====
    msp.add_lwpolyline([P(0, 0), P(W, 0), P(W, T), P(0, T)], close=True, dxfattribs={"layer": "OUTLINE"})
    ol(msp, P(W - CHAMFER, 0), P(W - CHAMFER, T))                     # top face / chamfer edge
    for hx in (10, 110):
        hid(msp, P(hx - HOLE_D / 2, 0), P(hx - HOLE_D / 2, T))
        hid(msp, P(hx + HOLE_D / 2, 0), P(hx + HOLE_D / 2, T))
        cl(msp, P(hx, -3), P(hx, T + 3))
    for ex in (sx - h - SLOT_W / 2, sx + h + SLOT_W / 2):
        hid(msp, P(ex, 0), P(ex, T))
    cl(msp, P(sx, -3), P(sx, T + 3))
    for d in (TAP_D, TAP_DRILL):                                      # tapped hole seen end-on (hidden)
        # Small circles (perimeter ~13-16 mm): half-scale dashes so the hidden pattern stays readable.
        msp.add_circle(P(TAP_X, T / 2), d / 2, dxfattribs={"layer": "HIDDEN", "ltscale": 0.4})
    cl(msp, P(TAP_X - 5, T / 2), P(TAP_X + 5, T / 2))

    # ===== LEFT-SIDE VIEW (looking +x; first angle: right of the front view, front face z=6 on the right) =====
    msp.add_lwpolyline([S(0, 0), S(T, 0), S(T, H), S(0, H)], close=True, dxfattribs={"layer": "OUTLINE"})
    for hy in (10, 70):
        hid(msp, S(0, hy - HOLE_D / 2), S(T, hy - HOLE_D / 2))
        hid(msp, S(0, hy + HOLE_D / 2), S(T, hy + HOLE_D / 2))
        cl(msp, S(-3, hy), S(T + 3, hy))
    for ey in (sy - SLOT_W / 2, sy + SLOT_W / 2):
        hid(msp, S(0, ey), S(T, ey))
    cl(msp, S(-3, sy), S(T + 3, sy))
    hid(msp, S(0, H - CHAMFER), S(T, H - CHAMFER))                    # chamfer edge behind the left face
    segs, tip = tapped_hole_profile(TAP_X, 0, 1, lambda u, v: S(T / 2 + u, v))
    for a, b in segs:
        hid(msp, a, b)
    cl(msp, S(T / 2, -3), S(T / 2, tip + 3))

    # ===== SECTION A-A (offset plane: y=10 through holes, y=40 through slot; viewed in +y) =====
    cut = [(-8, 10), (30, 10), (30, 40), (90, 40), (90, 10), (W + 8, 10)]
    msp.add_lwpolyline([F(x, y) for x, y in cut], dxfattribs={"layer": "CENTER"})
    for (x, y), d in (((-8, 10), 1), ((W + 8, 10), -1)):           # thick ends + arrows (view direction +y)
        msp.add_line(F(x, y), F(x + 6 * d, y), dxfattribs={"layer": "OUTLINE", "lineweight": 70})
        ax, ay = F(x + 2 * d, y)
        msp.add_solid([(ax - 1.2, ay + 4), (ax + 1.2, ay + 4), (ax, ay + 7.5)], dxfattribs={"layer": "DIM"})
        msp.add_line((ax, ay), (ax, ay + 4), dxfattribs={"layer": "DIM"})
        C.text(msp, ax, ay + 9, "A", 5, align=TA.BOTTOM_CENTER)
    for i in range(1, len(cut) - 1):                                  # thick short legs at changes of direction
        c = F(*cut[i])
        for nb in (cut[i - 1], cut[i + 1]):
            n = F(*nb)
            L_ = math.dist(c, n)
            msp.add_line(c, (c[0] + (n[0] - c[0]) * 3 / L_, c[1] + (n[1] - c[1]) * 3 / L_),
                         dxfattribs={"layer": "OUTLINE", "lineweight": 70})

    gaps = [(10 - HOLE_D / 2, 10 + HOLE_D / 2), (sx - h - SLOT_W / 2, sx + h + SLOT_W / 2),
            (110 - HOLE_D / 2, 110 + HOLE_D / 2)]
    A = lambda x, z: (AX + x, AY + z)
    msp.add_lwpolyline([A(0, 0), A(W, 0), A(W, T), A(0, T)], close=True, dxfattribs={"layer": "OUTLINE"})
    edges = [0.0] + [v for g in gaps for v in g] + [W]
    for g0, g1 in gaps:
        ol(msp, A(g0, 0), A(g0, T))
        ol(msp, A(g1, 0), A(g1, T))
    hatch = msp.add_hatch(dxfattribs={"layer": "HATCH"})
    hatch.set_pattern_fill("ANSI31", scale=0.4, angle=0)
    for x0, x1 in zip(edges[0::2], edges[1::2]):
        hatch.paths.add_polyline_path([A(x0, 0), A(x1, 0), A(x1, T), A(x0, T)], is_closed=True)
    for gx in (10, sx, 110):
        cl(msp, A(gx, -3), A(gx, T + 3))
    C.text(msp, AX + W / 2, AY + T + 8, "A-A", 5, align=TA.BOTTOM_CENTER)

    # ===== DIMENSIONS (real DIMENSION entities, ISO 129) =====
    d = dict(dimstyle="ISO-A", dxfattribs={"layer": "DIM"})
    tol = {"dimtol": 1, "dimtp": 0.1, "dimtm": 0.1, "dimtfac": 0.7}
    dims = [
        msp.add_linear_dim(base=F(0, -9), p1=F(0, 0), p2=F(10, 0), **d),
        msp.add_linear_dim(base=F(0, -9), p1=F(10, 0), p2=F(110, 0), override=tol, **d),
        msp.add_linear_dim(base=F(0, -18), p1=F(0, 0), p2=F(W, 0), **d),
        msp.add_linear_dim(base=F(-9, 0), p1=F(0, 0), p2=F(0, 10), angle=90, **d),
        msp.add_linear_dim(base=F(-9, 0), p1=F(0, 10), p2=F(0, 70), angle=90, override=tol, **d),
        msp.add_linear_dim(base=F(-18, 0), p1=F(0, 0), p2=F(0, H), angle=90, **d),
        msp.add_linear_dim(base=F(0, H + 9), p1=F(0, H), p2=F(sx, sy), **d),             # slot x-position 60
        msp.add_linear_dim(base=F(W + 20, 0), p1=F(W, 0), p2=F(sx + h, sy), angle=90, **d),  # slot y-position 40
        msp.add_linear_dim(base=F(0, sy + 12), p1=F(sx - h, sy), p2=F(sx + h, sy), **d),   # slot length 30
        slot_w := msp.add_linear_dim(base=F(sx + h + 12, 0), p1=F(sx + h, sy - SLOT_W / 2),
                                     p2=F(sx + h, sy + SLOT_W / 2), angle=90,
                                     override={"dimtih": 1, "dimtoh": 1}, **d),        # slot width 8
        msp.add_diameter_dim(center=F(110, 70), radius=HOLE_D / 2, angle=35, text="4x <> THRU", override={"dimtih": 1, "dimtoh": 1}, **d),
        msp.add_radius_dim(center=F(FILLET, H - FILLET), radius=FILLET, angle=135, text="3x <>", override={"dimtih": 1, "dimtoh": 1}, **d),
        msp.add_linear_dim(base=P(0, T + 9), p1=P(0, T), p2=P(TAP_X, T / 2), **d),        # M5 position 60
        msp.add_linear_dim(base=P(-9, 0), p1=P(0, 0), p2=P(0, T), angle=90, **d),          # thickness 6
        msp.add_linear_dim(base=S(0, -9), p1=S(0, 0), p2=S(T, 0), **d),                    # thickness 6
    ]
    # 8 mm is too short for the text between the arrows -> move it out on a leader (DIMTMOVE=1).
    slot_w.set_location(F(sx + h + 26, sy + 12), leader=True)
    for dm in dims:
        dm.render()
    # chamfer and thread callouts: leader + note (notes, not measurements)
    ch = F(W - CHAMFER / 2, H - CHAMFER / 2)
    msp.add_leader([ch, (ch[0] + 10, ch[1] + 10), (ch[0] + 16, ch[1] + 10)], dimstyle="ISO-A",
                   dxfattribs={"layer": "DIM"})
    C.text(msp, ch[0] + 17, ch[1] + 9, "5x45°", 3.5, layer="DIM", style="ISO")
    tp = S(T / 2 + TAP_D / 2, TAP_DEPTH / 2)
    msp.add_leader([tp, (tp[0] + 14, tp[1] - 8), (tp[0] + 20, tp[1] - 8)], dimstyle="ISO-A",
                   dxfattribs={"layer": "DIM"})
    C.text(msp, tp[0] + 21, tp[1] - 9, "M5 - 10 DEEP", 3.5, layer="DIM")
    C.text(msp, tp[0] + 21, tp[1] - 14, "(tap drill Ø4.2 - 12 deep)", 2.5, layer="DIM", style="ISO")

    # ===== NOTES, ROUGHNESS, TITLE BLOCK =====
    notes = ["NOTES:", "1. DIMENSIONS IN mm.", "2. GENERAL TOLERANCES ISO 2768-m.",
             "3. HOLE CENTRE DISTANCES ±0.1.", "4. REMOVE BURRS, BREAK SHARP EDGES."]
    for i, t in enumerate(notes):
        C.text(msp, 30, 70 - i * 6, t, 3.5 if i == 0 else 3.0, style="ISO")
    C.roughness_general(msp, 240, 52, "Ra 3.2")        # ISO 1302 general indication, next to the title block
    C.title_block(msp, 1.0, [
        [("SCALE", "1:1", 25), ("PROJECTION", "", 30), ("SIZE", "A3", 20), ("SHEET", "1/1", 20),
         ("DRAWING NO.", "CST-A-001", 85)],
        [("DRAWN BY", "H. Ha", 45), ("DATE", "2026-10-30", 45), ("MATERIAL", "AL 6061-T6", 90)],
        [("TITLE", "MOUNTING PLATE 120x80x6", 120), ("REV", "A", 20), ("UNITS", "mm", 40)],
        [("LEGAL OWNER", "Ha Phan Thanh Hai", 180)],
    ])
    C.first_angle_symbol(msp, 230 + 25 + 10, 10 + 0.8)
    return doc


def check(doc):
    """Re-read checks on the written geometry — fails loudly if a spec value drifted."""
    msp = doc.modelspace()
    circles = [(round(c.dxf.center.x - FX, 3), round(c.dxf.center.y - FY, 3), round(c.dxf.radius * 2, 3))
               for c in msp.query('CIRCLE[layer=="OUTLINE"]')]
    assert sorted(circles) == sorted((float(x), float(y), HOLE_D) for x, y in HOLES), circles
    dims = list(msp.query("DIMENSION"))
    assert len(dims) == 15, len(dims)
    meas = sorted(round(dm.get_measurement() if not hasattr(dm.get_measurement(), "x") else 0, 3) for dm in dims
                  if dm.dimtype in (0, 1))
    for v in (10, 100, 120, 10, 60, 80, 60, 40, 30, 8, 60, 6, 6):
        assert v in meas, (v, meas)
    assert len(msp.query("HATCH")) == 1
    for name, (lw, lt) in L.items():
        lay = doc.layers.get(name)
        assert lay.dxf.lineweight == lw and lay.dxf.linetype == lt, name
    tol_dims = [dm for dm in dims if dm.get_dim_style() and dm.dxf.hasattr("dimstyle")
                and doc.dimstyles.get(dm.dxf.dimstyle) and dm.override().get("dimtol")]
    assert len(tol_dims) == 2, "phai co dung 2 kich thuoc tam lo +-0.1"
    return {"circles": len(circles), "dimensions": len(dims), "measurements": meas}


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    doc = build()
    info = check(doc)
    dxf = OUT / "CST-A-001_mounting_plate.dxf"
    doc.saveas(dxf)
    doc2 = ezdxf.readfile(dxf)
    auditor = doc2.audit()
    assert not auditor.has_errors, auditor.errors
    C.export_pdf(doc2, OUT / "CST-A-001_mounting_plate.pdf", scale=1)
    dwg = C.export_dwg(dxf, OUT)
    print("check:", info)
    print("audit errors:", len(auditor.errors), "fixes:", len(auditor.fixes))
    print("dwg roundtrip:", C.dwg_roundtrip_count(dwg))
