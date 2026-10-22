"""Render the ThreatRAG architecture as a static PNG and an animated GIF of request flows.

Usage:  python3 docs/diagrams/render_architecture.py      (needs Pillow)
Outputs: docs/diagrams/threatrag-architecture.png / .gif
"""
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from diagram_layout import FLOWS, GROUPS, NODES, H, W, Flow, Point

OUT = Path(__file__).parent
BG, PANEL, NODE, LINE = "#0f161d", "#141f29", "#1b2935", "#2b3b4a"
INK, MUTED, ALERT = "#e3eaf0", "#8fa1b1", "#f2827a"
SPEED, HOLD = 26.0, 14  # logical px per frame, pause frames between flows


def _font(size: int, bold: bool = False, mono: bool = False) -> ImageFont.FreeTypeFont:
    path = "/System/Library/Fonts/Menlo.ttc" if mono else "/System/Library/Fonts/HelveticaNeue.ttc"
    try:
        return ImageFont.truetype(path, size, index=1 if bold and not mono else 0)
    except OSError:
        return ImageFont.load_default(size)


class Canvas:
    def __init__(self, scale: float):
        self.s = scale
        self.img = Image.new("RGB", (int(W * scale), int(H * scale)), BG)
        self.d = ImageDraw.Draw(self.img)
        self.f = {k: _font(int(v * scale), b, m) for k, (v, b, m) in {
            "h1": (22, True, False), "title": (13, True, False), "sub": (10, False, False),
            "group": (10, True, True), "cap": (13, False, False), "step": (15, True, False),
        }.items()}

    def p(self, pt: Point) -> tuple[float, float]:
        return (pt[0] * self.s, pt[1] * self.s)

    def rect(self, x: float, y: float, w: float, h: float, fill: str, outline: str, width: float = 1, r: float = 8) -> None:
        self.d.rounded_rectangle([self.p((x, y)), self.p((x + w, y + h))], radius=r * self.s,
                                 fill=fill, outline=outline, width=max(1, int(width * self.s)))

    def text(self, xy: Point, s: str, font: str, fill: str, anchor: str = "la") -> None:
        self.d.text(self.p(xy), s, font=self.f[font], fill=fill, anchor=anchor)

    def poly(self, pts: list[Point], fill: str, width: float) -> None:
        self.d.line([self.p(q) for q in pts], fill=fill, width=max(1, int(width * self.s)), joint="curve")

    def dot(self, pt: Point, r: float, fill: str) -> None:
        x, y = self.p(pt)
        rr = r * self.s
        self.d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=fill)


def _mix(hex_a: str, hex_b: str, t: float) -> str:
    a = [int(hex_a[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(hex_b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(a, b))


def draw_base(c: Canvas, active: Flow | None, lit: set[str], all_paths: bool) -> None:
    c.text((24, 30), "ThreatRAG · system architecture", "h1", INK)
    c.text((1256, 36), "MITRE ATT&CK · OWASP · NVD  »  cited answers & multi-agent investigations", "sub", MUTED, "ra")
    for g in GROUPS:
        c.rect(g.x, g.y, g.w, g.h, PANEL, LINE, r=12)
        c.text((g.x + 12, g.y + 10), g.title, "group", MUTED)
    flows = FLOWS if all_paths or active is None else [active]
    for f in flows:
        tone = f.color if all_paths else _mix(BG, f.color, 0.55)
        c.poly(f.path, _mix(BG, tone, 0.5 if all_paths else 1.0), 2)
    for node in NODES.values():
        on = node.key in lit
        border = active.color if (on and active) else LINE
        fill = _mix(NODE, active.color, 0.22) if (on and active) else NODE
        c.rect(node.x, node.y, node.w, node.h, fill, border, 2 if on else 1)
        if node.sub:
            c.text((node.x + 12, node.y + node.h / 2 - 9), node.title, "title", INK)
            c.text((node.x + 12, node.y + node.h / 2 + 7), node.sub, "sub", MUTED)
        else:
            c.text((node.x + 12, node.y + node.h / 2), node.title, "title", INK, "lm")


def draw_caption(c: Canvas, flows: list[Flow], active: Flow | None) -> None:
    c.rect(24, 724, 1234, 62, PANEL, LINE, r=10)
    x = 40.0
    for f in flows:
        on = f is active
        c.dot((x + 5, 744), 5, f.color if on or active is None else _mix(PANEL, f.color, 0.35))
        c.text((x + 16, 744), f.title, "title", INK if on or active is None else MUTED, "lm")
        x += 150
    msg = active.caption if active else "Four request flows share one service layer, one vector store and one LLM gateway."
    c.text((40, 770), msg, "cap", INK, "lm")
    c.text((1244, 744), "Kimchi primary · Gemini fallback · Ollama embeddings", "sub", MUTED, "rm")


def _sample(path: list[Point]) -> list[Point]:
    out: list[Point] = []
    carry = 0.0
    for (x1, y1), (x2, y2) in zip(path, path[1:]):
        seg = math.dist((x1, y1), (x2, y2))
        t = carry
        while t < seg:
            out.append((x1 + (x2 - x1) * t / seg, y1 + (y2 - y1) * t / seg))
            t += SPEED
        carry = t - seg
    return out + [path[-1]]


def _inside(pt: Point, key: str) -> bool:
    nd = NODES[key]
    m = SPEED / 2 + 4  # sampled points step SPEED px, so allow half a step past the edge
    return nd.x - m <= pt[0] <= nd.x + nd.w + m and nd.y - m <= pt[1] <= nd.y + nd.h + m


def render_gif(scale: float = 1.0) -> Path:
    frames: list[Image.Image] = []
    for flow in FLOWS:
        pts = _sample(flow.path)
        lit: set[str] = set()
        alerted = False
        for i, pt in enumerate(pts + [pts[-1]] * HOLD):
            lit |= {k for k in flow.nodes if _inside(pt, k)}
            if flow.alert_at and math.dist(pt, flow.alert_at) < SPEED:
                alerted = True
            c = Canvas(scale)
            draw_base(c, flow, lit, all_paths=False)
            for j in range(1, 7):  # fading trail
                k = max(0, min(i, len(pts) - 1) - j)
                c.dot(pts[k], 6 - j * 0.7, _mix(BG, flow.color, 1 - j / 8))
            c.dot(pt, 8, _mix(flow.color, "#ffffff", 0.35))
            c.dot(pt, 5, flow.color)
            if alerted and flow.alert_at:
                ax, ay = NODES["kimchi"].x + NODES["kimchi"].w - 34, NODES["kimchi"].y + 8
                c.rect(ax, ay, 28, 18, ALERT, ALERT, r=5)
                c.text((ax + 14, ay + 9), flow.alert_text, "sub", BG, "mm")
            draw_caption(c, FLOWS, flow)
            frames.append(c.img.convert("P", palette=Image.Palette.ADAPTIVE, colors=96))
    out = OUT / "threatrag-architecture.gif"
    frames[0].save(out, save_all=True, append_images=frames[1:], duration=45, loop=0, optimize=True, disposal=1)
    return out


def render_png(scale: float = 2.0) -> Path:
    c = Canvas(scale)
    draw_base(c, None, set(), all_paths=True)
    draw_caption(c, FLOWS, None)
    out = OUT / "threatrag-architecture.png"
    c.img.save(out, optimize=True)
    return out


if __name__ == "__main__":
    for path in (render_png(), render_gif()):
        print(f"{path}  {path.stat().st_size / 1024:.0f} KB")
