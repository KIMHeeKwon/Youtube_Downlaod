"""로컬 웹 UI 서버 — PHASE2.md §4 참조. 실행: uv run uvicorn webapp:app"""

import threading
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from downloader import download, download_playlist, is_playlist_url, validate_url

DOWNLOAD_DIR = Path("./downloads")
INDEX_HTML = Path(__file__).parent / "static" / "index.html"

app = FastAPI()

_jobs: dict[str, dict] = {}
_id_lock = threading.Lock()
_next_id = 0


class DownloadRequest(BaseModel):
    url: str
    max_height: int | None = None
    codec: str = "best"
    subs: str | None = None


def _make_hook(job: dict):
    """yt-dlp progress_hooks 콜백 — job dict를 제자리 갱신."""

    def hook(d: dict) -> None:
        info = d.get("info_dict") or {}
        if info.get("title"):
            job["title"] = info["title"]
        idx, cnt = info.get("playlist_index"), info.get("playlist_count")
        if idx and cnt:
            job["detail"] = f"[{idx}/{cnt}]"
        if d["status"] == "downloading":
            job["status"] = "downloading"
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            if total:
                job["percent"] = round(d.get("downloaded_bytes", 0) * 100 / total, 1)
            speed = d.get("speed")
            job["speed"] = f"{speed / 1048576:.1f} MiB/s" if speed else ""
        elif d["status"] == "finished":
            job["status"] = "merging"
            job["percent"] = 100.0
            job["speed"] = ""

    return hook


def _run(job: dict, req: DownloadRequest) -> None:
    subs = [s.strip() for s in req.subs.split(",") if s.strip()] if req.subs else None
    try:
        if is_playlist_url(req.url):
            paths, failed = download_playlist(
                req.url, DOWNLOAD_DIR, req.max_height, req.codec,
                _make_hook(job), subs,
            )
            job["detail"] = f"완료 {len(paths)}건 / 실패 {failed}건"
        else:
            download(
                req.url, DOWNLOAD_DIR, req.max_height, req.codec,
                _make_hook(job), subs,
            )
        job["status"] = "done"
        job["percent"] = 100.0
        job["speed"] = ""
    except Exception as e:  # DownloadError 포함 — 원인 문자열을 그대로 노출
        job["status"] = "error"
        job["detail"] = str(e)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(INDEX_HTML)


@app.post("/api/downloads")
def create_download(req: DownloadRequest) -> dict:
    if not is_playlist_url(req.url):
        try:
            validate_url(req.url)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
    global _next_id
    with _id_lock:
        _next_id += 1
        job_id = str(_next_id)
    job = {
        "job_id": job_id, "url": req.url, "title": "",
        "status": "queued", "percent": 0.0, "speed": "", "detail": "",
    }
    _jobs[job_id] = job
    threading.Thread(target=_run, args=(job, req), daemon=True).start()
    return {"job_id": job_id}


@app.get("/api/downloads")
def list_downloads() -> list[dict]:
    return list(_jobs.values())
