# YouTube 고화질 다운로더 — 구현 명세서

작성일: 2026-07-17
기반 문서: [DESIGN.md](DESIGN.md)
구현 환경: CLI (macOS, zsh)

---

## 0. 프로젝트 구조 (최종 형태)

```
youtube_Download/
├── docs/
│   ├── DESIGN.md            # 시스템 설계서
│   ├── IMPLEMENTATION.md    # 본 문서
│   └── WORKLOG.md           # 진행 로그
├── pyproject.toml           # uv 프로젝트 정의 (yt-dlp, pytest)
├── .python-version          # 3.12
├── main.py                  # CLI 계층 (~50줄)
├── downloader.py            # 다운로드 제어 계층 (~80줄)
└── tests/
    └── test_downloader.py   # 단위 테스트 (네트워크 불필요)
```

---

## 1단계. 개발 환경 구성

### 1.1 명령어 (순서대로 실행)

```bash
# ffmpeg (병합기) — 시스템 설치, 프로젝트에 동봉하지 않음 (GPL 이슈 회피, DESIGN §6.1)
brew install ffmpeg

# uv 미설치 시
brew install uv

# 프로젝트 초기화 (작업 디렉토리: ~/Documents/youtube_Download)
uv init --python 3.12 --no-workspace
uv add yt-dlp
uv add --dev pytest
```

### 1.2 검증 기준

```bash
uv run yt-dlp --version     # 날짜형 버전 출력 (예: 2026.xx.xx)
ffmpeg -version             # "ffmpeg version N.x" 출력
uv run python -c "import yt_dlp; print(yt_dlp.version.__version__)"
```

세 명령이 모두 정상 출력되면 1단계 완료.

---

## 2단계. `downloader.py` — 다운로드 제어 계층

### 2.1 공개 인터페이스

```python
class DownloadError(Exception):
    """다운로드 실패. 메시지에 사용자에게 보여줄 원인 포함."""

def validate_url(url: str) -> str:
    """YouTube URL 검증. 유효하면 11자리 영상 ID 반환, 무효하면 ValueError."""

def build_format_selector(max_height: int | None, codec: str) -> str:
    """DESIGN §3.2의 3단계 폴백 규칙 문자열 생성."""

def download(url: str,
             output_dir: Path,
             max_height: int | None,
             codec: str,
             progress_hook: Callable[[dict], None]) -> Path:
    """다운로드 실행. 성공 시 최종 파일 경로 반환, 실패 시 DownloadError."""
```

### 2.2 `validate_url` — 허용 URL 패턴

| 패턴 | 예시 |
|------|------|
| `youtube.com/watch?v=<ID>` | `https://www.youtube.com/watch?v=dQw4w9WgXcQ` |
| `youtu.be/<ID>` | `https://youtu.be/dQw4w9WgXcQ` |
| `youtube.com/shorts/<ID>` | `https://www.youtube.com/shorts/dQw4w9WgXcQ` |

구현: 정규식 1개로 처리. 영상 ID는 `[A-Za-z0-9_-]{11}`.

```python
_URL_RE = re.compile(
    r"(?:https?://)?(?:www\.|m\.)?"
    r"(?:youtube\.com/(?:watch\?(?:.*&)?v=|shorts/)|youtu\.be/)"
    r"([A-Za-z0-9_-]{11})"
)
```

- 매치 실패 → `ValueError("YouTube 영상 URL이 아닙니다: <url>")`
- 재생목록 URL(`list=` 파라미터 포함)이라도 영상 ID가 있으면 **해당 영상 1건만** 처리
  (ydl_opts의 `noplaylist: True`로 보장)

### 2.3 `build_format_selector` — 포맷 규칙 생성

| 입력 (`codec`, `max_height`) | 반환 문자열 |
|------------------------------|-------------|
| `best`, `None` (기본) | `bestvideo+bestaudio/best` |
| `best`, `1080` | `bestvideo[height<=1080]+bestaudio/best[height<=1080]` |
| `compat`, `None` | `bestvideo[ext=mp4][vcodec^=avc1]+bestaudio[ext=m4a]/bestvideo+bestaudio/best` |
| `compat`, `1080` | `bestvideo[ext=mp4][vcodec^=avc1][height<=1080]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best[height<=1080]` |

구현 로직: 높이 필터 `[height<=N]`을 각 video 항목에 삽입하는 문자열 조립 (분기 2개 × 필터 유무).

### 2.4 `download` — yt-dlp 옵션 전체 명세

```python
ydl_opts = {
    "format": build_format_selector(max_height, codec),
    "outtmpl": str(output_dir / "%(title)s [%(id)s].%(ext)s"),
    "merge_output_format": "mp4",       # ffmpeg 무손실 병합 → 단일 mp4
    "noplaylist": True,                 # 재생목록 URL이어도 단일 영상만
    "retries": 3,                       # DESIGN §3.3 네트워크 재시도
    "fragment_retries": 3,
    "continuedl": True,                 # .part 이어받기
    "progress_hooks": [progress_hook],
    "quiet": True,                      # 진행률은 훅으로만 출력
    "noprogress": True,                 # 네이티브 진행률 바 억제 (quiet만으로는 안 꺼짐 — 구현 중 확인)
    "no_warnings": True,
}
```

- 파일명에 `[영상ID]`를 포함해 제목 중복/특수문자 충돌 방지 (yt-dlp가 OS 금지 문자는 자동 치환)
- 실행 및 최종 경로 확보:

```python
with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    info = ydl.extract_info(url, download=True)
final_path = Path(info["requested_downloads"][0]["filepath"])
```

- 예외 매핑: `yt_dlp.utils.DownloadError as e` → `raise DownloadError(str(e))`
  (비공개·삭제·지역제한 사유가 yt-dlp 메시지에 포함되어 그대로 전달됨 — DESIGN §3.3)

---

## 3단계. `main.py` — CLI 계층

### 3.1 CLI 인터페이스 명세

```
usage: main.py [-h] [-o OUTPUT_DIR] [--max-height N] [--codec {best,compat}] url
```

| 인자 | 타입/기본값 | 설명 |
|------|-------------|------|
| `url` (위치) | str, 필수 | YouTube 영상 URL |
| `-o, --output-dir` | Path, `./downloads` | 저장 디렉토리 (없으면 생성) |
| `--max-height` | int, 없음(무제한) | 해상도 상한 (예: 1080) |
| `--codec` | `best`(기본) / `compat` | `best`=최고화질(VP9/AV1 허용), `compat`=H.264 우선 |

### 3.2 실행 흐름 (main 함수)

```
1. argparse 파싱
2. shutil.which("ffmpeg") 확인
   → 없으면 "ffmpeg가 필요합니다: brew install ffmpeg" 출력, sys.exit(1)
3. validate_url(url)
   → ValueError 시 메시지 출력, sys.exit(1)
4. output_dir.mkdir(parents=True, exist_ok=True)
5. download(...) 호출, progress_hook 전달
   → DownloadError 시 메시지 출력, sys.exit(1)
6. 성공: 최종 파일 경로 출력, sys.exit(0)
```

### 3.3 진행률 훅 명세

yt-dlp가 전달하는 dict의 사용 필드:

| status | 사용 필드 | 출력 |
|--------|-----------|------|
| `downloading` | `downloaded_bytes`, `total_bytes`(없으면 `total_bytes_estimate`), `speed`, `eta` | `\r[다운로드] 45.2% │ 12.3 MB/s │ 남은 시간 00:42` |
| `finished` | `filename` | 줄바꿈 후 `[병합] ffmpeg 처리 중...` |

- 한 줄 갱신(`\r`, `flush=True`), 줄 끝 잔여 문자 제거용 공백 패딩
- `total_bytes`가 None인 경우(라이브 아카이브 등) %를 생략하고 받은 용량만 표시
- 영상/음성 2개 스트림이 순차 다운로드되므로 `finished`가 2회 올 수 있음 → 마지막 병합 안내는 중복 출력 허용(단순성 우선)

### 3.4 종료 코드 정의

| 코드 | 의미 |
|------|------|
| 0 | 다운로드·병합 성공 |
| 1 | URL 무효 / ffmpeg 부재 / 다운로드 실패 |
| 2 | argparse 인자 오류 (argparse 기본 동작) |

---

## 4단계. 테스트 및 검증

### 4.1 단위 테스트 — `tests/test_downloader.py` (네트워크 불필요)

**`validate_url` 케이스:**

| 입력 | 기대 결과 |
|------|-----------|
| `https://www.youtube.com/watch?v=dQw4w9WgXcQ` | `"dQw4w9WgXcQ"` |
| `https://youtu.be/dQw4w9WgXcQ` | `"dQw4w9WgXcQ"` |
| `https://www.youtube.com/shorts/dQw4w9WgXcQ` | `"dQw4w9WgXcQ"` |
| `https://www.youtube.com/watch?list=PL123&v=dQw4w9WgXcQ` | `"dQw4w9WgXcQ"` (v가 뒤에 있는 경우) |
| `https://vimeo.com/12345` | `ValueError` |
| `https://www.youtube.com/playlist?list=PL123` | `ValueError` (영상 ID 없음) |
| `잘못된문자열` | `ValueError` |

**`build_format_selector` 케이스:** §2.3 표의 4가지 조합이 정확한 문자열을 반환하는지 확인.

실행: `uv run pytest -v` → 전체 통과가 2단계 완료 기준.

### 4.2 수동 통합 검증 (실제 네트워크, 3단계 완료 기준)

```bash
# 공개 CC 라이선스 영상 등으로 검증 (DESIGN §6.2 적법 범위)
uv run python main.py "https://www.youtube.com/watch?v=<검증용영상ID>"

# 해상도 확인 — YouTube 웹 표시 최고 화질과 일치해야 함
ffprobe -v error -select_streams v:0 \
  -show_entries stream=codec_name,width,height \
  -of default=noprint_wrappers=1 downloads/<파일명>.mp4

# 옵션 동작 확인
uv run python main.py --max-height 720 --codec compat "<같은 URL>"
# → ffprobe 결과: height=720 이하, codec_name=h264
```

### 4.3 오류 경로 검증 (4단계 완료 기준)

```bash
uv run python main.py "https://vimeo.com/123";        echo "exit=$?"   # exit=1, URL 오류 메시지
uv run python main.py "https://youtu.be/aaaaaaaaaaa"; echo "exit=$?"   # exit=1, yt-dlp 원인 메시지
```

---

## 5. 구현 체크리스트

- [ ] 1단계: 환경 구성 → `yt-dlp --version` / `ffmpeg -version` 확인
- [ ] 2단계: `downloader.py` + 단위 테스트 → `uv run pytest` 전체 통과
- [ ] 3단계: `main.py` → 실영상 1건 다운로드, `ffprobe` 해상도 일치 확인
- [ ] 4단계: 오류 경로 → 무효 URL/존재하지 않는 영상에서 exit 1 + 명확한 메시지

## 6. 구현하지 않는 것 (명세 고정)

- 설정 파일, 로깅 프레임워크, 클래스 계층 구조 (함수 5개로 충분)
- 재생목록/채널 처리, 자막, GUI (Phase 2 — DESIGN §7)
- DRM 콘텐츠 접근 (DESIGN §6.2)
