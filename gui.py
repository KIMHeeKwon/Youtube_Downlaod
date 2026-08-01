"""데스크톱 GUI 계층 (tkinter) — downloader.py 재사용, 콘솔 불필요.

Windows에서는 .venv\\Scripts\\pythonw.exe gui.py 로 콘솔 창 없이 실행된다.
"""

import json
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

import tour  # noqa: E402
import updater  # noqa: E402
from downloader import (  # noqa: E402  (PATH 설정 후 import)
    DownloadError,
    download,
    download_playlist,
    is_playlist_url,
    validate_url,
)

DOWNLOAD_DIR = _ROOT / "downloads"
# 설정은 홈에 둔다 — 프로젝트 폴더는 업데이트 시 교체 대상이라 유실될 수 있다 (PHASE3 §4)
CONFIG_PATH = Path.home() / ".youtube_downloader.json"


def load_config() -> dict:
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_config(cfg: dict) -> None:
    try:
        CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass


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
        self.url_entry = ttk.Entry(frm, textvariable=self.url_var)
        self.url_entry.grid(row=1, column=0, columnspan=4, sticky="ew", pady=(2, 8))

        ttk.Label(frm, text="최대 해상도").grid(row=2, column=0, sticky="w")
        self.height_var = tk.StringVar(value="무제한")
        self.height_combo = ttk.Combobox(
            frm, textvariable=self.height_var, state="readonly", width=8,
            values=["무제한", "2160", "1080", "720"])
        self.height_combo.grid(row=3, column=0, sticky="w")

        ttk.Label(frm, text="코덱").grid(row=2, column=1, sticky="w")
        self.codec_var = tk.StringVar(value="best")
        self.codec_combo = ttk.Combobox(
            frm, textvariable=self.codec_var, state="readonly", width=8,
            values=["best", "compat"])
        self.codec_combo.grid(row=3, column=1, sticky="w")

        ttk.Label(frm, text="자막 언어 (예: ko,en — 비우면 없음)").grid(
            row=2, column=2, columnspan=2, sticky="w")
        self.subs_var = tk.StringVar()
        self.subs_entry = ttk.Entry(frm, textvariable=self.subs_var, width=16)
        self.subs_entry.grid(row=3, column=2, sticky="w")

        self.start_btn = ttk.Button(frm, text="다운로드", command=self.start)
        self.start_btn.grid(row=3, column=3, sticky="e")

        self.progress = ttk.Progressbar(frm, maximum=100)
        self.progress.grid(row=4, column=0, columnspan=4, sticky="ew", pady=(12, 2))
        self.status_var = tk.StringVar(value="대기 중")
        ttk.Label(frm, textvariable=self.status_var).grid(
            row=5, column=0, columnspan=2, sticky="w")
        ttk.Button(frm, text="사용법 보기", command=self.show_tour).grid(
            row=5, column=2, sticky="e")
        self.folder_btn = ttk.Button(frm, text="저장 폴더 열기", command=self.open_folder)
        self.folder_btn.grid(row=5, column=3, sticky="e")

        self.log = tk.Text(frm, height=8, state="disabled")
        self.log.grid(row=6, column=0, columnspan=4, sticky="nsew", pady=(8, 0))
        frm.columnconfigure((0, 1, 2, 3), weight=1)
        frm.rowconfigure(6, weight=1)

        self.frm = frm
        self.config = load_config()
        self.tour = None
        root.after(100, self._poll)
        root.after(600, self._startup)   # 창이 자리를 잡은 뒤 투어 좌표를 계산

    # --- 최초 실행 투어 (PHASE3 §1) ---------------------------------------

    def _startup(self):
        if not self.config.get("tour_shown"):
            self.show_tour()
        threading.Thread(target=self._check_updates, daemon=True).start()

    def show_tour(self):
        steps = [
            tour.Step([self.url_entry], "주소를 붙여넣으세요",
                      "YouTube에서 복사한 주소를 여기에 붙여넣습니다. 영상 하나는 물론 "
                      "재생목록·라이브 다시보기 주소도 그대로 넣으면 됩니다."),
            tour.Step([self.height_combo, self.codec_combo, self.subs_entry],
                      "옵션은 건드리지 않아도 됩니다",
                      "기본값으로 두면 그 영상에서 받을 수 있는 가장 좋은 화질로 저장됩니다. "
                      "오래된 기기에서 재생하려면 코덱을 compat으로, 자막이 필요하면 "
                      "ko,en처럼 언어를 적으세요."),
            tour.Step([self.start_btn], "누르면 시작됩니다",
                      "진행률과 속도가 아래 막대에 표시됩니다. 화질이 높을수록 시간이 걸리며, "
                      "창을 닫지 않고 기다리면 됩니다."),
            tour.Step([self.folder_btn], "받은 영상은 여기에",
                      "다운로드가 끝나면 이 버튼으로 저장 폴더를 엽니다. 파일은 downloads "
                      "폴더에 '제목 [영상ID].mp4' 형식으로 저장됩니다."),
        ]
        self.tour = tour.Tour(self.root, steps, on_close=self._tour_done)
        self.tour.start()

    def _tour_done(self):
        self.config["tour_shown"] = True
        save_config(self.config)

    # --- 업데이트 (PHASE3 §2) ---------------------------------------------

    def _check_updates(self):
        try:
            changed = updater.update_ytdlp()
            if changed:
                self.events.put(
                    ("log", f"yt-dlp를 갱신했습니다 ({changed[0]} → {changed[1]})"))
        except Exception:
            pass   # 기존 버전으로 계속 동작하므로 알리지 않는다 (PHASE3 §2.1)
        try:
            rel = updater.check_app_update()
            if rel and rel.tag != self.config.get("skip_version"):
                self.events.put(("update", rel))
        except Exception:
            pass

    def _show_update_banner(self, rel):
        bar = tk.Frame(self.root, bg="#fff4ce")
        tk.Label(bar, text=f"새 버전 {rel.tag}이(가) 나왔습니다.",
                 bg="#fff4ce", fg="#4a3b00").pack(side="left", padx=12, pady=6)
        ttk.Button(bar, text="업데이트",
                   command=lambda: self._start_update(rel, bar)).pack(
                       side="right", padx=(0, 12), pady=4)
        ttk.Button(bar, text="나중에",
                   command=lambda: self._skip_update(rel, bar)).pack(side="right", padx=6)
        bar.pack(side="top", fill="x", before=self.frm)

    def _skip_update(self, rel, bar):
        self.config["skip_version"] = rel.tag
        save_config(self.config)
        bar.destroy()

    def _start_update(self, rel, bar):
        bar.destroy()
        threading.Thread(target=self._update_worker, args=(rel,), daemon=True).start()

    def _update_worker(self, rel):
        try:
            updater.apply_app_update(
                rel, lambda m: self.events.put(("progress", 0, m)))
            self.events.put(("quit", None))
        except Exception as e:
            self.events.put(("error", f"업데이트 실패: {e}"))

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
                elif ev[0] == "log":
                    self._log(ev[1])
                elif ev[0] == "update":
                    self._show_update_banner(ev[1])
                elif ev[0] == "quit":
                    self.root.destroy()
                    return
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
    app = App(root)
    if "--selftest" in sys.argv:  # CI용: 화면 표시 없이 위젯 생성/파괴만 검증
        root.update_idletasks()
        app.show_tour()           # 투어 위젯 생성/파괴까지 확인 (PHASE3 §8)
        root.update_idletasks()
        app.tour.on_close = None  # 셀프테스트가 사용자 설정을 건드리지 않도록
        app.tour.close()
        root.destroy()
        print("selftest ok")
        return
    root.mainloop()


if __name__ == "__main__":
    main()
