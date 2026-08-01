"""최초 실행 사용법 투어 — 4분할 딤 패널 스포트라이트 (PHASE3 §3.1).

macOS Tk는 -transparentcolor를 지원하지 않으므로(DECISIONS D6), 타깃 위젯 사각형
주위에 반투명 창 4개를 배치해 가운데를 비우는 방식으로 스포트라이트를 만든다.
"""

import tkinter as tk
from dataclasses import dataclass
from tkinter import ttk

DIM_ALPHA = 0.55
PAD = 6           # 스포트라이트 여백
WRAP = 300        # 말풍선 본문 줄바꿈 폭


@dataclass
class Step:
    widgets: list           # 스포트라이트 대상 (복수면 합집합)
    title: str
    body: str


class Tour:
    def __init__(self, root: tk.Tk, steps: list[Step], on_close=None):
        self.root = root
        self.steps = steps
        self.on_close = on_close
        self.index = 0
        self.panels: list[tk.Toplevel] = []
        self.bubble: tk.Toplevel | None = None

    # --- 수명 주기 -------------------------------------------------------

    def start(self):
        if not self.steps or self.bubble is not None:
            return
        self.root.update_idletasks()
        # 투어 중 창 크기가 바뀌면 스포트라이트 좌표가 어긋난다 (PHASE3 §3.1)
        self.root.resizable(False, False)
        self.panels = [self._make_panel() for _ in range(4)]
        self.bubble = self._make_bubble()
        self.root.bind("<Escape>", lambda _e: self.close())
        self._show()

    def close(self):
        for w in self.panels + ([self.bubble] if self.bubble else []):
            w.destroy()
        self.panels = []
        self.bubble = None
        self.root.unbind("<Escape>")
        self.root.resizable(True, True)
        if self.on_close:
            self.on_close()

    def next(self):
        if self.index >= len(self.steps) - 1:
            self.close()
            return
        self.index += 1
        self._show()

    # --- 창 생성 ---------------------------------------------------------

    def _make_panel(self) -> tk.Toplevel:
        p = tk.Toplevel(self.root)
        p.overrideredirect(True)
        p.configure(bg="black")
        p.attributes("-alpha", DIM_ALPHA)
        p.attributes("-topmost", True)
        return p

    def _make_bubble(self) -> tk.Toplevel:
        b = tk.Toplevel(self.root)
        b.overrideredirect(True)
        b.attributes("-topmost", True)

        border = tk.Frame(b, bg="#444444")
        border.pack(fill="both", expand=True)
        box = tk.Frame(border, bg="white", padx=16, pady=14)
        box.pack(fill="both", expand=True, padx=1, pady=1)

        self.title_lbl = tk.Label(box, bg="white", fg="#111111", justify="left",
                                  font=("TkDefaultFont", 13, "bold"))
        self.title_lbl.pack(anchor="w")
        self.body_lbl = tk.Label(box, bg="white", fg="#333333", justify="left",
                                 wraplength=WRAP)
        self.body_lbl.pack(anchor="w", pady=(6, 12))

        bar = tk.Frame(box, bg="white")
        bar.pack(fill="x")
        self.dots_lbl = tk.Label(bar, bg="white", fg="#888888")
        self.dots_lbl.pack(side="left")
        self.next_btn = ttk.Button(bar, text="다음", command=self.next)
        self.next_btn.pack(side="right")
        ttk.Button(bar, text="건너뛰기", command=self.close).pack(side="right", padx=(0, 6))
        return b

    # --- 단계 표시 -------------------------------------------------------

    def _show(self):
        step = self.steps[self.index]
        rect = self._rect(step.widgets)
        self._place_panels(rect)
        self.title_lbl.config(text=step.title)
        self.body_lbl.config(text=step.body)
        self.dots_lbl.config(text=" ".join(
            "●" if i == self.index else "○" for i in range(len(self.steps))))
        last = self.index == len(self.steps) - 1
        self.next_btn.config(text="시작하기" if last else "다음")
        self._place_bubble(rect)

    def _rect(self, widgets) -> tuple[int, int, int, int]:
        """대상 위젯들의 화면 절대 좌표 합집합 (x1, y1, x2, y2)."""
        self.root.update_idletasks()
        x1 = min(w.winfo_rootx() for w in widgets) - PAD
        y1 = min(w.winfo_rooty() for w in widgets) - PAD
        x2 = max(w.winfo_rootx() + w.winfo_width() for w in widgets) + PAD
        y2 = max(w.winfo_rooty() + w.winfo_height() for w in widgets) + PAD
        return x1, y1, x2, y2

    def _place_panels(self, rect):
        x1, y1, x2, y2 = rect
        rx, ry = self.root.winfo_rootx(), self.root.winfo_rooty()
        rw, rh = self.root.winfo_width(), self.root.winfo_height()
        geoms = [
            (rx, ry, rw, y1 - ry),               # 위
            (rx, y2, rw, ry + rh - y2),          # 아래
            (rx, y1, x1 - rx, y2 - y1),          # 왼쪽
            (x2, y1, rx + rw - x2, y2 - y1),     # 오른쪽
        ]
        for panel, (px, py, pw, ph) in zip(self.panels, geoms):
            if pw <= 0 or ph <= 0:   # 타깃이 창 가장자리에 닿은 경우
                panel.withdraw()
            else:
                panel.geometry(f"{pw}x{ph}+{px}+{py}")
                panel.deiconify()

    def _place_bubble(self, rect):
        x1, y1, _x2, y2 = rect
        self.bubble.update_idletasks()
        bw, bh = self.bubble.winfo_reqwidth(), self.bubble.winfo_reqheight()
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        bx = min(max(x1, 8), sw - bw - 8)
        by = y2 + 12 if y2 + 12 + bh < sh else y1 - bh - 12
        self.bubble.geometry(f"{bw}x{bh}+{bx}+{max(by, 8)}")
