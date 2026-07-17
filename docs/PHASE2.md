# Phase 2 — 재생목록 · 자막 · 로컬 웹 UI 설계/구현 명세

작성일: 2026-07-17
기반 문서: [DESIGN.md](DESIGN.md) §7, [IMPLEMENTATION.md](IMPLEMENTATION.md)
전제: MVP(단일 영상 CLI) 완성 상태에서의 **증분 확장**. 기존 공개 인터페이스는 하위 호환 유지.

---

## 1. 범위

| 기능 | 방식 |
|------|------|
| 자막 동시 다운로드 | CLI `--subs LANGS` 옵션 (예: `--subs ko,en`) → .srt 저장 |
| 재생목록 일괄 다운로드 | `youtube.com/playlist?list=<ID>` URL 자동 감지 → 전체 순차 다운로드 |
| 로컬 웹 UI | FastAPI + 단일 HTML. URL 입력 → 백그라운드 다운로드 + 진행률 표시 |

**변경하지 않는 것**: 기본 코덱 방침(`best`, opus 허용 — 사용자 확정), 기존 CLI 인터페이스,
`watch?v=..&list=..` URL의 단일 영상 처리(noplaylist 유지).

---

## 2. `downloader.py` 확장

### 2.1 자막 — `download()`에 `subs_langs` 키워드 인자 추가

```python
def download(url, output_dir, max_height, codec, progress_hook,
             subs_langs: list[str] | None = None) -> Path
```

`subs_langs`가 주어지면 ydl_opts에 추가:

```python
"writesubtitles": True,        # 업로더 제공 자막
"writeautomaticsub": True,     # 자동 생성 자막 (수동 자막 없는 영상 대비)
"subtitleslangs": subs_langs,  # 예: ["ko", "en"]
"postprocessors": [{"key": "FFmpegSubtitlesConvertor", "format": "srt"}],
```

- 산출: 영상과 같은 폴더에 `<제목> [<ID>].<lang>.srt`
- 요청 언어 자막이 없어도 **오류 아님** (영상만 저장)

### 2.2 재생목록 — URL 감지 + `download_playlist()`

```python
_PLAYLIST_RE = re.compile(
    r"(?:https?://)?(?:www\.|m\.)?youtube\.com/playlist\?(?:.*&)?list=([A-Za-z0-9_-]+)"
)

def is_playlist_url(url: str) -> bool

def download_playlist(url, output_dir, max_height, codec, progress_hook,
                      subs_langs=None) -> tuple[list[Path], int]
    """(성공 파일 경로 목록, 실패 건수) 반환. 전부 실패 시 DownloadError."""
```

단일 영상 대비 ydl_opts 차이:

| 옵션 | 값 | 이유 |
|------|-----|------|
| `outtmpl` | `<output_dir>/%(playlist_title)s/%(title)s [%(id)s].%(ext)s` | 재생목록별 하위 폴더 |
| `noplaylist` | 제거 | 전체 항목 처리 |
| `ignoreerrors` | `True` | 비공개/삭제 항목 1건 때문에 전체 중단 방지 |

- 결과 수집: `info["entries"]`에서 실패 항목(None) 제외, 각 entry의
  `requested_downloads[0].filepath` 수집. 실패 건수 = None 개수.

## 3. `main.py` 확장

- `--subs LANGS` 옵션 추가 (쉼표 구분, 기본 없음)
- URL 분기: `is_playlist_url()` → 재생목록 모드, 아니면 기존 `validate_url()` 단일 모드
- 진행률 훅: `info_dict`에 `playlist_index`/`playlist_count`가 있으면 `[3/12]` 접두 표시
- 재생목록 완료 시 요약 출력: `완료: N건 저장 (실패 M건) → <폴더>`
- 종료 코드: 기존 유지. 재생목록에서 일부 실패는 exit 0 + 요약에 명시, 전부 실패만 exit 1

## 4. 웹 UI — `webapp.py` + `static/index.html`

### 4.1 구조 (최소 구성)

| 파일 | 책임 |
|------|------|
| `webapp.py` | FastAPI 앱. 정적 페이지 서빙 + REST 2개 + 백그라운드 다운로드 스레드 |
| `static/index.html` | 단일 페이지: URL 입력폼, 옵션(해상도/코덱/자막), 작업 목록·진행률 (fetch 폴링 1초) |

의존성 추가: `uv add fastapi uvicorn`. 실행: `uv run uvicorn webapp:app` (기본 127.0.0.1:8000, 로컬 전용).

### 4.2 API

| 메서드/경로 | 요청 | 응답 |
|-------------|------|------|
| `GET /` | — | index.html |
| `POST /api/downloads` | `{url, max_height?, codec?, subs?}` | `{job_id}` — URL 무효 시 400 |
| `GET /api/downloads` | — | 전체 작업 목록 (아래 상태 객체 배열) |

작업 상태 객체: `{job_id, url, title, status: queued|downloading|merging|done|error,
percent, speed, detail}` — 진행률 훅이 인메모리 dict 갱신, 스레드 1개씩 `threading.Thread`로 실행.

- 재생목록 URL도 동일 엔드포인트로 접수 (status에 `[n/m]` 반영)
- 영속화·인증·동시성 제한 없음 (로컬 1인용 — 의도적 최소화)

## 5. 검증 기준

| 항목 | 방법 | 기준 |
|------|------|------|
| 단위 테스트 | `is_playlist_url` 유효/무효 케이스 추가 | `uv run pytest` 전체 통과 |
| 자막 | 자막 보유 공개 영상 1건 `--subs ko,en` | `.srt` 파일 생성 + 영상 정상 |
| 재생목록 | 소규모 공개 재생목록 (`--max-height 144`로 용량 최소화) | 하위 폴더에 전체 항목 저장, (성공, 실패) 요약 정확 |
| 웹 UI | 서버 기동 → POST → 폴링 → 파일 확인 (curl) | done 상태 도달 + 파일 존재 |

## 6. 구현하지 않는 것

- 다운로드 큐 영속화, 사용자 인증, 외부 노출(0.0.0.0 바인딩), WebSocket
- 채널 전체 다운로드 (재생목록 URL만 지원)
- 자막 번역·후처리
