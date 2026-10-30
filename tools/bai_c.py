"""Test C — scan to CAD: redraw Fig. 263 of C. L. Svensen, "Machine Drawing" (1921, public domain)
from the dimensions printed on the drawing (inches), then overlay the redraw on the scan.

Every value below is either PRINTED on the source drawing or SCALED from the print (not dimensioned in the
source). The scaled ones are listed in SCALED and flagged in the README. Model units: inches, origin = front
view base, left end. Plan (top) view sits above the front view (third-angle, as in the source).
"""
import math
from pathlib import Path

import ezdxf
import numpy as np
from PIL import Image

import common as C

OUT = Path(__file__).resolve().parent.parent / "bai_c"
SRC_PNG = OUT / "source_fig263.png"

# ---------- printed dimensions (inches) ----------
W, BASE_T, FOOT = 12.0, 0.75, 3.5            # overall 12, foot thickness 3/4, 3-1/2 + 5 + 3-1/2
OPEN_W, OPEN_H = 5.0, 4.0                    # opening between the legs 5, height 4
WALL = 0.75                                  # leg / arch wall 3/4
R_IN = 1.0                                   # inner corner radius 1
HUB_D, HUB_TOP = 4.0, 8.0                    # hub width 4, height to top of hub 8
FLANGE_T = 0.5                               # bushing flange 1/2
BUSH_OD, BORE = 2.75, 2.0                    # bushing 2-3/4 OD, 2 bore
BUSH_L = 3.0                                 # bushing length below the flange 3
HUB_H = 3.25                                 # 3-1/4 from top of hub down to the arch top
BRG_T = 0.75                                 # bearing steel 3/4
DEPTH = 4.75                                 # plan depth 4-3/4
HOLE_PITCH_X, HOLE_PITCH_Y, HOLE_D = 9.75, 2.75, 0.875   # 9-3/4, 2-3/4, 7/8 drill
RIB_W = 0.75                                 # rib width in plan 3/4
BRG_R = 2.0                                  # "2R" on the bearing seat

# ---------- not dimensioned on the source: measured on the scan, rounded to 1/8" ----------
# The outer outline of the central rib is drawn but carries no dimension. A least-squares circle through
# 69 edge points of the scan gives R 4.71", centre 2.88" above the base, tangent to the 12" end face
# (max residual 5 px = 0.09"). Rounded: R 4-3/4", centre height 2-7/8".
SCALED = {
    "rib outer arc radius": 4.75,
    "rib arc centre height": 2.875,
    "plan view offset above front view": 10.9,   # layout only, no geometry depends on it
}
R_WEB, Y_WEB = SCALED["rib outer arc radius"], SCALED["rib arc centre height"]
PY0 = SCALED["plan view offset above front view"]

CX = W / 2
LEG_IN = (W - OPEN_W) / 2                    # 3.5  inner face of the leg
LEG_OUT = LEG_IN - WALL                      # 2.75 outer face of the leg
ARCH_TOP_IN = OPEN_H                         # 4.0
ARCH_TOP_OUT = OPEN_H + WALL                 # 4.75 (= HUB_TOP - HUB_H, checked below)
HX0, HX1 = CX - HUB_D / 2, CX + HUB_D / 2    # hub 4..8

L = {"OUTLINE": (50, "Continuous"), "HIDDEN": (25, "DASHED"), "CENTER": (18, "CENTER"), "DIM": (18, "Continuous"),
     "TEXT": (25, "Continuous"), "TITLE": (35, "Continuous"), "HATCH": (18, "Continuous")}
S = 2.0 / 25.4      # sheet (mm) -> model (inch) at 1:2  (A3 sheet, drawing at half size)


def mirror(pts):
    return [(W - x, y) for x, y in pts]


def arc_pts(cx, cy, r, a0, a1, n=24):
    return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * k / n)),
             cy + r * math.sin(math.radians(a0 + (a1 - a0) * k / n))) for k in range(n + 1)]


def build():
    assert abs(ARCH_TOP_OUT - (HUB_TOP - HUB_H)) < 1e-9, "3-1/4 + 4 + 3/4 must close to 8"
    assert abs(2 * FOOT + OPEN_W - W) < 1e-9
    doc = C.new_doc(L, s=1.0)
    doc.header["$INSUNITS"] = 1              # inches
    doc.header["$MEASUREMENT"] = 0
    doc.header["$LTSCALE"] = 1 / 25.4 * 2    # ISO dash lengths are in mm on paper, model is inches at 1:2
    ds = C.add_dimstyle(doc, "INCH", s=1.0, txt=3.5 * S, asz=3.0 * S)
    ds.dxf.dimexe, ds.dxf.dimexo, ds.dxf.dimgap = 2 * S, 1 * S, 1 * S
    msp = doc.modelspace()
    ol = lambda pts, layer="OUTLINE": msp.add_lwpolyline(pts, dxfattribs={"layer": layer})
    ln = lambda a, b, layer="OUTLINE": msp.add_line(a, b, dxfattribs={"layer": layer})

    # ===== FRONT VIEW =====
    a_hub = math.degrees(math.acos((HX0 - R_WEB) / R_WEB))        # arc runs into the hub side
    half = [(0, 0), (0, Y_WEB)] + arc_pts(R_WEB, Y_WEB, R_WEB, 180, a_hub)[1:]
    ol(half)
    ol(mirror(half))
    ln((0, 0), (LEG_IN, 0))
    ln((W - LEG_IN, 0), (W, 0))
    ln((0, BASE_T), (LEG_OUT, BASE_T))                    # foot top
    ln((W - LEG_OUT, BASE_T), (W, BASE_T))
    inner = [(LEG_IN, 0), (LEG_IN, ARCH_TOP_IN - R_IN)] + \
        arc_pts(LEG_IN + R_IN, ARCH_TOP_IN - R_IN, R_IN, 180, 90)[1:] + [(W - LEG_IN - R_IN, ARCH_TOP_IN)] + \
        arc_pts(W - LEG_IN - R_IN, ARCH_TOP_IN - R_IN, R_IN, 90, 0)[1:] + [(W - LEG_IN, 0)]
    ol(inner)
    r_out = R_IN + WALL
    yy = ARCH_TOP_IN - R_IN + math.sqrt(r_out ** 2 - (HX0 - (LEG_IN + R_IN)) ** 2)   # where it meets the hub
    a_end = math.degrees(math.atan2(yy - (ARCH_TOP_IN - R_IN), HX0 - (LEG_IN + R_IN)))
    outer_l = [(LEG_OUT, BASE_T), (LEG_OUT, ARCH_TOP_IN - R_IN)] + \
        arc_pts(LEG_IN + R_IN, ARCH_TOP_IN - R_IN, r_out, 180, a_end)[1:]
    ol(outer_l)
    ol(mirror(outer_l))
    # hub + bushing flange
    ol([(HX0, ARCH_TOP_OUT), (HX0, HUB_TOP + FLANGE_T), (HX1, HUB_TOP + FLANGE_T), (HX1, ARCH_TOP_OUT)])
    ln((HX0, HUB_TOP), (HX1, HUB_TOP))
    # bushing: flange on top of the hub, body 3" down into a 2-3/4" bore; steel bearing 3/4" thick at the
    # bottom of the bushing bore, top face domed 2R (apex 3/4" above the bushing bottom)
    y_bush = HUB_TOP - BUSH_L                                    # 5.0, bottom of bushing = bottom of bore
    apex = y_bush + BRG_T                                        # 5.75
    xs = np.linspace(0, BORE / 2, 11)
    dome = [(x, apex - (BRG_R - math.sqrt(BRG_R ** 2 - x * x))) for x in xs]
    rim = dome[-1][1]
    b0, r0 = CX - BUSH_OD / 2, CX - BORE / 2
    # left half: hidden lines
    ln((b0, y_bush), (b0, HUB_TOP), "HIDDEN")
    ln((r0, y_bush), (r0, HUB_TOP + FLANGE_T), "HIDDEN")
    ln((b0, y_bush), (CX, y_bush), "HIDDEN")
    ol([(CX - x, y) for x, y in dome], "HIDDEN")
    # right half in section (as in the source): brass bushing, steel bearing, cast-iron hub wall
    brass = [(CX + BORE / 2, rim), (CX + BORE / 2, HUB_TOP + FLANGE_T), (HX1, HUB_TOP + FLANGE_T), (HX1, HUB_TOP),
             (CX + BUSH_OD / 2, HUB_TOP), (CX + BUSH_OD / 2, y_bush), (CX + BORE / 2, y_bush)]
    steel = [(CX, y_bush), (CX + BORE / 2, y_bush)] + [(CX + x, y) for x, y in reversed(dome)]
    iron = [(CX, ARCH_TOP_OUT), (HX1, ARCH_TOP_OUT), (HX1, HUB_TOP), (CX + BUSH_OD / 2, HUB_TOP),
            (CX + BUSH_OD / 2, y_bush), (CX, y_bush)]
    for pts, pat in ((brass, "ANSI33"), (steel, "ANSI32"), (iron, "ANSI31")):
        msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": "OUTLINE"})
        h = msp.add_hatch(dxfattribs={"layer": "HATCH"})
        h.set_pattern_fill(pat, scale=2.0 * S / 0.125)       # imperial ANSI patterns: 1/8" pitch -> 2 mm on paper
        h.paths.add_polyline_path(pts, is_closed=True)
    # bolt holes in the feet (hidden), centre lines
    hx = [(W - HOLE_PITCH_X) / 2, (W + HOLE_PITCH_X) / 2]
    for x in hx:
        for dx in (-HOLE_D / 2, HOLE_D / 2):
            ln((x + dx, 0), (x + dx, BASE_T), "HIDDEN")
        ln((x, -0.2), (x, BASE_T + 0.3), "CENTER")
    ln((CX, -0.3), (CX, HUB_TOP + FLANGE_T + 0.4), "CENTER")

    # ===== PLAN VIEW =====
    P = lambda x, y: (x, PY0 + y)
    yc = DEPTH / 2
    ol([P(0, 0), P(W, 0), P(W, DEPTH), P(0, DEPTH), P(0, 0)])
    for xs in (LEG_OUT, W - LEG_OUT):
        ln(P(xs, 0), P(xs, yc - RIB_W / 2))
        ln(P(xs, yc + RIB_W / 2), P(xs, DEPTH))
    for xs in (LEG_IN, W - LEG_IN):
        ln(P(xs, 0), P(xs, yc - RIB_W / 2), "HIDDEN")
        ln(P(xs, yc + RIB_W / 2), P(xs, DEPTH), "HIDDEN")
    xr = CX - math.sqrt((HUB_D / 2) ** 2 - (RIB_W / 2) ** 2)
    for y in (yc - RIB_W / 2, yc + RIB_W / 2):
        ln(P(0, y), P(xr, y))
        ln(P(W - xr, y), P(W, y))
    msp.add_circle(P(CX, yc), HUB_D / 2, dxfattribs={"layer": "OUTLINE"})
    msp.add_circle(P(CX, yc), BUSH_OD / 2, dxfattribs={"layer": "HIDDEN"})
    msp.add_circle(P(CX, yc), BORE / 2, dxfattribs={"layer": "OUTLINE"})
    for x in hx:
        for y in (yc - HOLE_PITCH_Y / 2, yc + HOLE_PITCH_Y / 2):
            msp.add_circle(P(x, y), HOLE_D / 2, dxfattribs={"layer": "OUTLINE"})
            ln(P(x - 0.6, y), P(x + 0.6, y), "CENTER")
            ln(P(x, y - 0.6), P(x, y + 0.6), "CENTER")
    ln(P(-0.3, yc), P(W + 0.3, yc), "CENTER")
    ln(P(CX, -0.3), P(CX, DEPTH + 0.3), "CENTER")

    # ===== DIMENSIONS (real DIMENSION entities; text in fractions as on the source) =====
    d = dict(dimstyle="INCH", dxfattribs={"layer": "DIM"})
    o = 12 * S
    dims = [
        (msp.add_linear_dim(base=(0, -o), p1=(0, 0), p2=(LEG_IN, 0), text='3-1/2"', **d), 3.5),
        (msp.add_linear_dim(base=(0, -o), p1=(LEG_IN, 0), p2=(W - LEG_IN, 0), text='5"', **d), 5.0),
        (msp.add_linear_dim(base=(0, -o), p1=(W - LEG_IN, 0), p2=(W, 0), text='3-1/2"', **d), 3.5),
        (msp.add_linear_dim(base=(0, -2 * o), p1=(0, 0), p2=(W, 0), text='12"', **d), 12.0),
        (msp.add_linear_dim(base=(W + 2 * o, 0), p1=(W, 0), p2=(HX1, HUB_TOP), angle=90, text='8"', **d), 8.0),
        (msp.add_linear_dim(base=(W + o, 0), p1=(W, 0), p2=(W, BASE_T), angle=90, text='3/4"', **d), 0.75),
        (msp.add_linear_dim(base=(CX + 1.3, 0), p1=(CX, 0), p2=(CX, ARCH_TOP_IN), angle=90, text='4"', **d), 4.0),
        (msp.add_linear_dim(base=(0, 1.5), p1=(W - LEG_IN, 1.5), p2=(W - LEG_OUT, 1.5), text='3/4"', **d), 0.75),
        (msp.add_linear_dim(base=(0, HUB_TOP + FLANGE_T + o), p1=(HX0, HUB_TOP + FLANGE_T),
                            p2=(HX1, HUB_TOP + FLANGE_T), text='4"', **d), 4.0),
        (msp.add_linear_dim(base=(0, HUB_TOP + FLANGE_T + o / 2), p1=(CX - BORE / 2, HUB_TOP + FLANGE_T),
                            p2=(CX + BORE / 2, HUB_TOP + FLANGE_T), text='2"', **d), 2.0),
        (msp.add_linear_dim(base=(0, HUB_TOP - 1.0), p1=(CX - BUSH_OD / 2, HUB_TOP - 1.0),
                            p2=(CX + BUSH_OD / 2, HUB_TOP - 1.0), text='2-3/4"', **d), 2.75),
        (msp.add_linear_dim(base=(HX1 + o, 0), p1=(HX1, HUB_TOP), p2=(HX1, HUB_TOP + FLANGE_T), angle=90,
                            text='1/2"', **d), 0.5),
        (msp.add_linear_dim(base=(HX1 + 1.6 * o, 0), p1=(HX1, y_bush), p2=(HX1, HUB_TOP), angle=90,
                            text='3"', **d), 3.0),
        (msp.add_linear_dim(base=(HX1 + 2.4 * o, 0), p1=(HX1, ARCH_TOP_OUT), p2=(HX1, HUB_TOP), angle=90,
                            text='3-1/4"', **d), 3.25),
        (msp.add_linear_dim(base=(HX1 + 0.8 * o, 0), p1=(HX1, y_bush), p2=(HX1, apex), angle=90,
                            text='3/4"', **d), 0.75),
        (msp.add_linear_dim(base=(0, PY0 - o), p1=P(hx[0], yc - HOLE_PITCH_Y / 2), p2=P(hx[1], yc - HOLE_PITCH_Y / 2),
                            text='9-3/4"', **d), 9.75),
        (msp.add_linear_dim(base=(W + 2.4 * o, 0), p1=P(W, 0), p2=P(W, DEPTH), angle=90, text='4-3/4"', **d), 4.75),
        (msp.add_linear_dim(base=(W + 1.6 * o, 0), p1=P(hx[1], yc - HOLE_PITCH_Y / 2),
                            p2=P(hx[1], yc + HOLE_PITCH_Y / 2), angle=90, text='2-3/4"', **d), 2.75),
        (msp.add_linear_dim(base=(W + 0.8 * o, 0), p1=P(W, yc - RIB_W / 2), p2=P(W, yc + RIB_W / 2), angle=90,
                            text='3/4"', **d), 0.75),
    ]
    dims.append((msp.add_radius_dim(center=(LEG_IN + R_IN, ARCH_TOP_IN - R_IN), radius=R_IN, angle=135,
                                    text='R1"', override={"dimtih": 1, "dimtoh": 1}, **d), 1.0))
    dims.append((msp.add_diameter_dim(center=P(hx[1], yc - HOLE_PITCH_Y / 2), radius=HOLE_D / 2,
                                      location=P(W + 0.4, -0.7), text='7/8" DRILL, 4 HOLES',
                                      override={"dimtih": 1, "dimtoh": 1}, **d), 0.875))
    dims.append((msp.add_radius_dim(center=(CX, apex - BRG_R), radius=BRG_R, location=(CX + 0.5, 6.35), text='2"R',
                                    override={"dimtih": 1, "dimtoh": 1}, **d), 2.0))
    for dm, _ in dims:
        dm.render()
    for (x, y), t in (((-5.8, 7.2), "BUSHING - BRASS"), ((-5.8, 6.6), "BEARING - STEEL"),
                      ((-5.8, 6.0), "SUPPORT - CAST IRON")):
        C.text(msp, x, y, t, 3.0 * S)
    C.text(msp, -5.8, 5.4, "FRONT VIEW: RIGHT HALF IN SECTION", 3.0 * S)

    # ===== sheet: A3 at 1:2, frame + ISO 7200-style title block (in inches on the model) =====
    sx0, sy0 = -8.4, -5.3                # centres the two views on the A3 sheet at 1:2
    C_frame(msp, sx0, sy0)
    tb_rows = [
        [("SCALE", "1:2", 25), ("UNITS", "inch", 30), ("SIZE", "A3", 20), ("SHEET", "1/1", 20),
         ("DRAWING NO.", "CST-C-001", 85)],
        [("DRAWN BY", "H. Ha", 45), ("DATE", "2026-10-30", 45), ("MATERIAL", "CI / BRASS / STEEL", 90)],
        [("TITLE", "STEP BEARING (FIG. 263 REDRAWN)", 180)],
        [("SOURCE", "Svensen, Machine Drawing (1921), Fig. 263 - public domain", 180)],
    ]
    title_block_inch(msp, sx0, sy0, tb_rows)
    return doc, dims, half


def C_frame(msp, sx0, sy0):
    w, h = 420 * S, 297 * S
    msp.add_lwpolyline([(sx0, sy0), (sx0 + w, sy0), (sx0 + w, sy0 + h), (sx0, sy0 + h)], close=True,
                       dxfattribs={"layer": "TITLE", "lineweight": 18})
    msp.add_lwpolyline([(sx0 + 20 * S, sy0 + 10 * S), (sx0 + w - 10 * S, sy0 + 10 * S),
                        (sx0 + w - 10 * S, sy0 + h - 10 * S), (sx0 + 20 * S, sy0 + h - 10 * S)], close=True,
                       dxfattribs={"layer": "TITLE", "lineweight": 70})
    return []


def title_block_inch(msp, sx0, sy0, rows):
    x0, y = sx0 + (410 - 180) * S, sy0 + 10 * S
    rh = 8 * S
    for row in rows:
        x = x0
        for label, value, wmm in row:
            w = wmm * S
            msp.add_lwpolyline([(x, y), (x + w, y), (x + w, y + rh), (x, y + rh)], close=True,
                               dxfattribs={"layer": "TITLE", "lineweight": 35})
            C.text(msp, x + 1 * S, y + rh - 2.6 * S, label, 1.8 * S, "TITLE")
            C.text(msp, x + 1.5 * S, y + 1.4 * S, value, (3.5 if len(value) < 26 else 2.5) * S, "TITLE")
            x += w
        y += rh


def check(doc, dims):
    for dm, want in dims:
        got = dm.dimension.get_measurement()
        got = got if isinstance(got, float) else got
        assert abs(float(got) - want) < 1e-6, (dm.dimension.dxf.text, got, want)
    return len(dims)


# ---------------- overlay on the scan ----------------
def dark_peak(arr, axis, lo, hi):
    """Index (row or column) of the darkest line inside [lo, hi] of a grayscale scan."""
    prof = (255 - arr).sum(axis=axis)
    seg = prof[lo:hi]
    return lo + int(np.argmax(seg))


def overlay(doc):
    scan = Image.open(SRC_PNG).convert("L")
    a = np.asarray(scan, dtype=np.int32)
    # register each view on lines that carry printed dimensions: base line, left end, right end (front);
    # top / bottom / left / right edges (plan). Search windows are +-25 px around where the lines are.
    base = dark_peak(a[:, 300:900], 1, 1110, 1160)
    left = dark_peak(a[900:1130, :], 0, 230, 270)
    right = dark_peak(a[900:1130, :], 0, 960, 1000)
    ppi = (right - left) / W
    fx = lambda x: left + x * ppi
    fy = lambda y: base - y * ppi
    ptop, pbot = dark_peak(a[:, 300:900], 1, 170, 205), dark_peak(a[:, 300:900], 1, 455, 490)
    pl, pr = dark_peak(a[200:460, :], 0, 230, 270), dark_peak(a[200:460, :], 0, 960, 1000)
    pppi = (pr - pl) / W
    gx = lambda x: pl + x * pppi
    gy = lambda y: pbot - (y - PY0) * pppi
    # measured checks: printed features located in the scan vs. the redraw
    checks = []
    def meas(name, model_val, pix, scale, origin, sign=1):
        scan_val = (pix - origin) / scale * sign
        checks.append((name, model_val, round(scan_val, 3), round(scan_val - model_val, 3)))
    meas("front: inner leg face, left (3-1/2)", LEG_IN, dark_peak(a[1000:1120, :], 0, 440, 490), ppi, left)
    meas("front: inner leg face, right (8-1/2)", W - LEG_IN, dark_peak(a[1000:1120, :], 0, 740, 790), ppi, left)
    meas("front: top of hub (8)", HUB_TOP, dark_peak(a[:, 500:540], 1, 640, 670), ppi, base, -1)
    meas("front: foot top (3/4)", BASE_T, dark_peak(a[:, 255:300], 1, 1075, 1105), ppi, base, -1)
    meas("plan: depth (4-3/4)", DEPTH, pbot - ptop, pppi, 0)
    meas("plan: scale vs front scale", 1.0, pppi, ppi, 0)
    # draw the redraw (geometry layers only) in red over the scan
    rgb = Image.open(SRC_PNG).convert("RGB")
    from PIL import ImageDraw
    dr = ImageDraw.Draw(rgb)
    msp = doc.modelspace()
    def tr(x, y):
        return (gx(x), gy(y)) if y > PY0 - 1 else (fx(x), fy(y))
    for e in msp:
        lay = e.dxf.layer
        if lay not in ("OUTLINE", "HIDDEN"):
            continue
        col = (220, 0, 0) if lay == "OUTLINE" else (0, 90, 220)
        if e.dxftype() == "LINE":
            dr.line([tr(e.dxf.start.x, e.dxf.start.y), tr(e.dxf.end.x, e.dxf.end.y)], fill=col, width=2)
        elif e.dxftype() == "LWPOLYLINE":
            pts = [tr(x, y) for x, y in e.get_points("xy")]
            if e.closed:
                pts.append(pts[0])
            dr.line(pts, fill=col, width=2)
        elif e.dxftype() == "CIRCLE":
            cx, cy = tr(e.dxf.center.x, e.dxf.center.y)
            r = e.dxf.radius * (pppi if e.dxf.center.y > PY0 - 1 else ppi)
            dr.ellipse([cx - r, cy - r, cx + r, cy + r], outline=col, width=2)
    rgb.save(OUT / "overlay_redraw_on_scan.png")
    return ppi, checks


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    doc, dims, _ = build()
    n = check(doc, dims)
    dxf = OUT / "CST-C-001_step_bearing.dxf"
    doc.saveas(dxf)
    doc2 = ezdxf.readfile(dxf)
    aud = doc2.audit()
    assert not aud.has_errors, aud.errors
    C.export_pdf(doc2, OUT / "CST-C-001_step_bearing.pdf", scale=S)
    dwg = C.export_dwg(dxf, OUT)
    ppi, checks = overlay(doc)
    print("dimensions checked:", n, "| audit errors:", len(aud.errors))
    print("scan scale: %.2f px/in" % ppi)
    for c in checks:
        print("  %-40s model %-6s scan %-7s diff %s" % c)
    print("dwg roundtrip:", C.dwg_roundtrip_count(dwg))
