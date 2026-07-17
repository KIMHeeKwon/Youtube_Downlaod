"""데스크톱 GUI 계층 (tkinter) — downloader.py 재사용, 콘솔 불필요.

Windows에서는 .venv\\Scripts\\pythonw.exe gui.py 로 콘솔 창 없이 실행된다.
"""

import os
import queue
import subprocess
import sys
import threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk

# Windows 설치 스크립트가 받은 ffmpeg(tools/)를 실행 환경에 노출
_ROOT = Path(__file__).resolve().parent
os.environ["PATH"] = str(_ROOT / "tools") + os.pathsep + os.environ["PATH"]

from downloader import (  # noqa: E402  (PATH 설정 후 import)
    DownloadError,
    download,
    download_playlist,
    is_playlist_url,
    validate_url,
)

DOWNLOAD_DIR = _ROOT / "downloads"


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("YouTube 고화질 다운로더")
        root.minsize(560, 360)
        self.events: queue.Queue = queue.Queue()
        self.busy = False

        frm = ttk.Frame(root, padding=12)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="YouTube 주소").grid(row=0, column=0, sticky="w")
        self.url_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.url_var).grid(
            row=1, column=0, columnspan=4, sticky="ew", pady=(2, 8))

        ttk.Label(frm, text="최대 해상도").grid(row=2, column=0, sticky="w")
        self.height_var = tk.StringVar(value="무제한")
        ttk.Combobox(frm, textvariable=self.height_var, state="readonly", width=8,
                     values=["무제한", "2160", "1080", "720"]).grid(row=3, column=0, sticky="w")

        ttk.Label(frm, text="코덱").grid(row=2, column=1, sticky="w")
        self.codec_var = tk.StringVar(value="best")
        ttk.Combobox(frm, textvariable=self.codec_var, state="readonly", width=8,
                     values=["best", "compat"]).grid(row=3, column=1, sticky="w")

        ttk.Label(frm, text="자막 언어 (예: ko,en — 비우면 없음)").grid(
            row=2, column=2, columnspan=2, sticky="w")
        self.subs_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.subs_var, width=16).grid(
            row=3, column=2, sticky="w")

        self.start_btn = ttk.Button(frm, text="다운로드", command=self.start)
        self.start_btn.grid(row=3, column=3, sticky="e")

        self.progress = ttk.Progressbar(frm, maximum=100)
        self.progress.grid(row=4, column=0, columnspan=4, sticky="ew", pady=(12, 2))
        self.status_var = tk.StringVar(value="대기 중")
        ttk.Label(frm, textvariable=self.status_var).grid(
            row=5, column=0, columnspan=3, sticky="w")
        ttk.Button(frm, text="저장 폴더 열기", command=self.open_folder).grid(
            row=5, column=3, sticky="e")

        self.log = tk.Text(frm, height=8, state="disabled")
        self.log.grid(row=6, column=0, columnspan=4, sticky="nsew", pady=(8, 0))
        frm.columnconfigure((0, 1, 2, 3), weight=1)
        frm.rowconfigure(6, weight=1)

        root.after(100, self._poll)

    # --- UI 동작 ---------------------------------------------------------

    def start(self):
        url = self.url_var.get().strip()
        if not url or self.busy:
            return
        if not is_playlist_url(url):
            try:
                validate_url(url)
            except ValueError as e:
                self._log(str(e))
                return
        self.busy = True
        self.start_btn.config(state="disabled")
        self.status_var.set("시작 중...")
        threading.Thread(target=self._worker, args=(url,), daemon=True).start()

    def _worker(self, url: str):
        height = self.height_var.get()
        max_height = None if height == "무제한" else int(height)
        subs = self.subs_var.get().strip()
        subs_langs = [s.strip() for s in subs.split(",") if s.strip()] or None
        DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
        try:
            if is_playlist_url(url):
                paths, failed = download_playlist(
                    url, DOWNLOAD_DIR, max_height, self.codec_var.get(),
                    self._hook, subs_langs)
                msg = f"완료: {len(paths)}건 저장"
                if failed:
                    msg += f" (실패 {failed}건)"
                self.events.put(("done", msg))
            else:
                path = download(url, DOWNLOAD_DIR, max_height,
                                self.codec_var.get(), self._hook, subs_langs)
                self.events.put(("done", f"완료: {path.name}"))
        except DownloadError as e:
            self.events.put(("error", f"다운로드 실패: {e}"))

    def _hook(self, d: dict):
        info = d.get("info_dict") or {}
        idx, count = info.get("playlist_index"), info.get("playlist_count")
        prefix = f"[{idx}/{count}] " if idx and count else ""
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            downloaded = d.get("downloaded_bytes", 0)
            speed = d.get("speed")
            speed_s = f"{speed / 1_000_000:.1f} MB/s" if speed else ""
            if total:
                pct = downloaded / total * 100
                self.events.put(("progress", pct,
                                 f"{prefix}다운로드 중 {pct:.1f}% {speed_s}"))
            else:
                self.events.put(("progress", 0,
                                 f"{prefix}다운로드 중 {downloaded / 1_000_000:.1f} MB {speed_s}"))
        elif d["status"] == "finished":
            self.events.put(("progress", 100, f"{prefix}병합 중 (ffmpeg)..."))

    def _poll(self):
        try:
            while True:
                ev = self.events.get_nowait()
                if ev[0] == "progress":
                    self.progress["value"] = ev[1]
                    self.status_var.set(ev[2])
                elif ev[0] in ("done", "error"):
                    self.progress["value"] = 100 if ev[0] == "done" else 0
                    self.status_var.set(ev[1])
                    self._log(ev[1])
                    self.busy = False
                    self.start_btn.config(state="normal")
        except queue.Empty:
            pass
        self.root.after(100, self._poll)

    def _log(self, msg: str):
        self.log.config(state="normal")
        self.log.insert("end", msg + "\n")
        self.log.see("end")
        self.log.config(state="disabled")

    def open_folder(self):
        DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(DOWNLOAD_DIR)  # noqa: S606
        else:
            subprocess.run(["open", str(DOWNLOAD_DIR)], check=False)


def main():
    root = tk.Tk()
    App(root)
    if "--selftest" in sys.argv:  # CI용: 화면 표시 없이 위젯 생성/파괴만 검증
        root.update_idletasks()
        root.destroy()
        print("selftest ok")
        return
    root.mainloop()


if __name__ == "__main__":
    main()
