# WORKLOG

## 2026-07-17

- **목표**: YouTube 고화질 다운로더 프로젝트 시스템 설계 수립
- **결정사항**:
  - 다운로드 엔진으로 yt-dlp(Python API) 채택 — 직접 구현·pytube 대비 유지보수성 우위
  - 고화질 핵심은 DASH 분리 스트림(bestvideo+bestaudio) 선택 + ffmpeg 무손실 병합
  - MVP는 CLI 2개 파일(main.py, downloader.py) 구조로 최소화, GUI/재생목록은 Phase 2로 보류
- **산출물**: `docs/DESIGN.md` (시스템 설계서)
- **현재 진행도**: 설계 완료, 구현 미착수
- **남은 미해결**: ffmpeg·yt-dlp 미설치 (환경 구성 필요), 시스템 Python 3.9 → 프로젝트 전용 venv 필요
- **다음 단계**: 설계 승인 후 1단계(환경 구성) → 2~4단계(구현·검증) 진행

### 2차 작업 (같은 날)
- **목표**: 설계서 시각화 및 라이선스/저작권 분석 보강
- **결정사항**:
  - ffmpeg(GPL v2+)는 동봉 배포하지 않고 시스템 설치 전제 → 본 코드 라이선스 자유 확보
  - 콘텐츠 저작권은 코드 라이선스와 분리 평가, 사용 범위를 본인 콘텐츠·CC·사적 이용으로 한정
- **산출물**: `docs/DESIGN.md` 6절(라이선스/저작권) 추가, 시각화 설계서 아티팩트 발행
  (https://claude.ai/code/artifact/76ff96b3-e366-4d02-ac35-1f895c76d9c0)
- **현재 진행도**: 설계 문서 완성, 구현 미착수

### 3차 작업 (같은 날)
- **목표**: 설계 기반 CLI 구현 명세서 작성 (함수 시그니처·yt-dlp 옵션·명령어 수준 구체화)
- **결정사항**:
  - 프로젝트 관리: uv + Python 3.12, 의존성은 yt-dlp / pytest(dev) 2개로 한정
  - 공개 인터페이스 확정: `validate_url`, `build_format_selector`, `download` + `DownloadError`
  - 파일명 규칙: `%(title)s [%(id)s].%(ext)s` (제목 충돌 방지), 출력 기본 경로 `./downloads`
  - CLI 옵션 확정: `url`, `-o/--output-dir`, `--max-height`, `--codec {best,compat}`
  - 단위 테스트는 네트워크 불필요 범위(URL 검증, 포맷 규칙)로 한정, 실 다운로드는 수동 통합 검증
- **산출물**: `docs/IMPLEMENTATION.md` (구현 명세서)
- **현재 진행도**: 설계·구현 명세 완료, 코드 미착수
- **남은 미해결**: ffmpeg·uv 환경 구성 필요 (명세 1단계)
- **다음 단계**: 명세 승인 후 1단계(환경 구성)부터 체크리스트 순서로 구현

### 4차 작업 (같은 날) — 구현 및 실검증 완료
- **목표**: IMPLEMENTATION.md 체크리스트 1~4단계 전체 구현·검증 (테스트 데이터: live URL 2건)
- **결정사항**:
  - 테스트 URL이 `youtube.com/live/<ID>` 형식이라 URL 정규식에 `live/` 패턴 추가 (명세 §2.2 갱신)
  - yt-dlp 2026.x의 JS 런타임 부재 경고("일부 포맷 누락 가능") 대응으로 deno 설치를 환경 요건에 추가
  - `quiet: True`만으로 네이티브 진행률 바가 억제되지 않는 결함 발견 → `noprogress: True` 추가 (명세 §2.4 갱신)
- **산출물**:
  - 코드: `downloader.py`, `main.py`, `tests/test_downloader.py`, `pyproject.toml`(pytest pythonpath)
  - 환경: Python 3.12.13(uv), yt-dlp 2026.7.4, pytest 9.1.1, ffmpeg 8.1.2, deno
  - 다운로드 검증 파일 2건: `downloads/` (E1M1-mkrfnA 1.6GB, IEfM972ODcU 1.9GB)
- **검증 결과**:
  - 단위 테스트 13/13 통과 (`uv run pytest`)
  - 통합: 4시간짜리 라이브 아카이브 2건 다운로드 성공, ffprobe로 h264 1920×1080(가용 최고 화질) 확인
  - 오류 경로(에이전트 검증): 무효 URL exit 1 / 미존재 영상 exit 1 + 원인 메시지 / 인자 누락 exit 2 — 3/3 PASS
- **현재 진행도**: MVP 완성 (체크리스트 4/4)
- **남은 미해결**: 기본 `codec=best`에서 음성이 opus로 선택되어 opus-in-MP4 산출 가능 — 일부 구형 플레이어 비호환 (필요 시 `--codec compat` 사용으로 회피, 방침 결정 대기)
- **다음 단계**: Phase 2 착수 여부 사용자 판단 (재생목록/웹 UI/자막 — DESIGN §7)

### 4차 작업 (같은 날)
- **목표**: git 저장소 연결
- **결정사항**: .gitignore에 다운로드 산출물(downloads/, *.mp4, *.part 등)·.venv·로컬 설정 제외
- **산출물**: 로컬 git 저장소 초기 커밋 (6264d02, 11개 파일 — 코드·문서·의존성 잠금)
- **현재 진행도**: 구현 완료(main.py, downloader.py, tests), 로컬 커밋 완료
- **남은 미해결**: GitHub 원격 저장소 연결 (저장소 URL 필요 또는 gh CLI 설치·인증 필요)
- **다음 단계**: 원격 저장소 URL 확보 → `git remote add origin` → `git push -u origin main`

### 5차 작업 (같은 날) — GitHub 연결 완료
- **목표**: 다중 GitHub 계정 체계 구축 및 원격 푸시
- **결정사항**: gh CLI 멀티 계정(`gh auth switch`)으로 KIMHeeKwon(개인)/ETRI-ULSOO(업무) 전환 관리, 전역 CLAUDE.md에 지침 명문화
- **산출물**: https://github.com/KIMHeeKwon/Youtube_Downlaod 에 main 브랜치 푸시 완료 (커밋 3건)
- **현재 진행도**: MVP 구현·검증·원격 연결 모두 완료
- **다음 단계**: Phase 2 착수 여부 판단 (재생목록/웹 UI/자막), opus-in-MP4 호환성 방침 결정

### 6차 작업 (같은 날) — CI 구축
- **목표**: GitHub Actions workflow 설정
- **산출물**: `.github/workflows/ci.yml` — main push/PR 시 ubuntu-latest에서 uv sync → pytest 실행 (setup-uv 캐시 사용)
- **검증 결과**: 첫 실행 성공 (run 29552693396, 10초)
- **현재 진행도**: CI 가동 중. Phase 2 웹 UI(webapp.py, static/)는 로컬 미커밋 상태로 진행 중

## 2026-07-24

### 웹 UI 다크 테마 대응 및 테마 전환 기능
- **목표**: 다크 테마 브라우저에서 글씨가 검게 보여 읽을 수 없는 문제 수정 + 테마 수동 전환 기능
- **원인**: index.html이 글자색(#222)만 지정하고 배경 미지정 → 다크 브라우저에서 어두운 배경 + 검은 글씨
- **결정사항**: CSS 커스텀 프로퍼티 토큰 체계 도입 — 시스템 테마 추종(prefers-color-scheme) 기본, 수동 선택(data-theme + localStorage)이 시스템 설정보다 우선
- **산출물**: `static/index.html` (테마 토큰 12종 × 라이트/다크, 우상단 전환 버튼), `.claude/launch.json` (webapp 실행 설정)
- **검증 결과**: 브라우저 실검증 — 다크 렌더링 정상, 라이트↔다크 전환 정상, localStorage 저장 확인
- **다음 단계**: 없음 (완결)

### ffmpeg 다운로드 재시도 로직 (windows/install.ps1)
- **목표**: CI windows-install 잡이 gyan.dev 일시 장애(503)로 실패하던 문제의 구조적 해결
- **결정사항**: URL별 3회 재시도(10s→20s→30s 백오프) + 실패 시 GitHub BtbN 공식 빌드 미러로 폴백. 두 소스 모두 GPL 빌드이며 설치 시점 다운로드 방식이라 재배포 아님 (DESIGN §6.1 구조 유지)
- **산출물**: `windows/install.ps1` ffmpeg 다운로드 절 개정
- **검증 결과**: CI windows-install 잡 통과로 확인 (로컬 pwsh 부재)

### CI 액션 버전 상향 (Node 20 경고 해소)
- **목표**: actions/checkout·setup-uv의 Node 20 지원 종료 경고 제거
- **결정사항**: checkout v4→v7, setup-uv v5→v9.0.0 (v9 별칭 태그가 없어 정확 버전으로 고정 — 1차 시도 실패에서 확인)
- **검증 결과**: CI 전체 통과 + 어노테이션 0건 (run 30674758086)

### CI 워크플로 잡별 분리 + README 배지 교체
- **목표**: README에 잡별(test / windows-install) 상태 배지 노출
- **결정사항**: GitHub 배지는 워크플로 단위로만 제공되므로 ci.yml을 test.yml / windows-install.yml 두 파일로 분리 (잡 내용은 동일, 트리거 동일)
- **산출물**: `.github/workflows/test.yml`, `.github/workflows/windows-install.yml` (ci.yml 삭제), README 배지 2종 교체 (branch=main 한정)
- **검증 결과**: 분리된 두 워크플로 모두 첫 실행 성공 (커밋 a357767)

### 7차 작업 (같은 날) — Phase 2 구현·검증 완료 (재생목록·자막·웹 UI)
- **목표**: DESIGN §7 Phase 2 후보 3건 전체 구현 및 실전 검증 (사용자 확정: 3건 모두, 코덱 기본값은 현행 유지)
- **결정사항**:
  - 명세 우선 작성: `docs/PHASE2.md` (증분 확장, 기존 인터페이스 하위 호환 유지)
  - `watch?v=..&list=..`는 단일 영상 유지, `playlist?list=` URL만 일괄 모드
  - 재생목록은 `ignoreerrors`로 개별 실패 건너뛰기, `%(playlist_title)s/` 하위 폴더 저장
  - 자막은 `--subs LANGS` 옵션 → 수동+자동 자막, FFmpegSubtitlesConvertor로 .srt 변환
- **산출물**:
  - `downloader.py` 확장: `is_playlist_url`, `download_playlist`, `download(subs_langs=)`, `_base_opts` 공통화
  - `main.py` 확장: `--subs`, 재생목록 분기, `[n/m]` 진행 접두, 완료 요약
  - 신규: `webapp.py`(FastAPI, 103줄), `static/index.html`(단일 파일 UI, 110줄), `docs/PHASE2.md`
  - 의존성 추가: fastapi, uvicorn
- **검증 결과** (에이전트 2기 병렬 검증):
  - 단위 테스트 19/19 통과 (is_playlist_url 6케이스 추가)
  - 자막: `--subs ko,en` → .en.srt 생성·형식 유효 (ko는 영상에 원천 부재 — 정상)
  - 재생목록: 공개 재생목록 10건 전량 다운로드, `[1/10]`~`[10/10]` 표시, 요약 정확 (지정 테스트 재생목록이 전항목 삭제 상태라 에이전트가 대체 재생목록 정찰·확정)
  - 웹 UI: 기동→POST→진행률 폴링(percent 상승 실측)→done→파일 확인→무효 URL 400 — 전 항목 PASS
- **현재 진행도**: Phase 2 완성. 로컬 미커밋 (webapp.py, static/, PHASE2.md, downloader/main/tests 수정분)
- **다음 단계**: 커밋·푸시 여부 사용자 판단, 검증용 다운로드 파일 정리 여부 판단

### 8차 작업 (같은 날) — Windows 원클릭 설치 + 데스크톱 GUI
- **목표**: 일반 Windows 사용자가 ZIP 해제 → install.bat 더블클릭만으로 설치·사용 (터미널 불필요, 사용자 요구로 네이티브 GUI 추가)
- **결정사항**:
  - 단일 exe(PyInstaller) 대신 설치 스크립트 방식 채택 — ffmpeg GPL 동봉 회피(DESIGN §6.1), yt-dlp 수시 갱신 필요, macOS에서 exe 검증 불가
  - ffmpeg는 설치 시점에 공식 빌드(gyan.dev)에서 사용자 PC가 직접 다운로드 → `tools/` (재배포 아님, .gitignore로 커밋 차단)
  - GUI는 tkinter(gui.py) — downloader.py 재사용, 스레드+큐로 진행률 표시, 바로가기는 pythonw.exe(무콘솔) 대상
  - 웹 UI(start.bat)는 보조 실행 수단으로 유지
- **산출물**: `gui.py`, `windows/install.bat`, `windows/install.ps1`, `windows/start.bat`, `docs/WINDOWS.md`, ci.yml `windows-install` 잡(설치→ffmpeg→pytest→GUI selftest→웹 UI 스모크), .gitignore(tools/)
- **검증 결과**: 로컬 pytest 19/19, gui.py --selftest 통과 (macOS). Windows 실검증은 CI windows-latest 러너에서 수행 (PR CI)
- **현재 진행도**: windows-installer 브랜치에서 PR 진행
- **다음 단계**: CI green 확인 후 main 병합

### 9차 작업 (같은 날) — 퍼블릭 공개 준비: 라이선스·면책·README
- **목표**: 저장소 퍼블릭 전환 대비 라이선스/저작권 명시 + 설치·사용법 상세 가시화 문서 (사용자 요구)
- **결정사항**:
  - 코드 라이선스는 MIT 채택 — "개인 용도 허용 + 상업적 이용·수정 배포 시 무책임" 요구를 AS IS/무책임 표준 조항으로 충족
  - 콘텐츠 저작권·YouTube 약관·서드파티 라이선스 준수 책임은 사용자에게 있음을 README 면책 조항 4개 항으로 명문화
  - ffmpeg(GPL)는 저장소 미포함·사용자 직접 취득 구조임을 서드파티 표에 명시 (동봉 재배포 시 GPL 의무는 재배포자 몫)
- **산출물**: `LICENSE`(MIT), `README.md` 전면 작성(뱃지, mermaid 동작 원리·설치 흐름도, GUI ASCII 화면 구성, 3가지 사용법·CLI 예제 모음, 문제 해결·서드파티 라이선스 표), pyproject 메타데이터(license, description)
- **검증 결과**: uv sync 정상, pytest 19/19 유지
- **현재 진행도**: PR #1에 통합 (CI green 후 사용자 병합 대기 — 자체 병합은 정책상 차단)
- **다음 단계**: 사용자가 PR #1 병합 → 저장소 퍼블릭 전환 (GitHub Settings ▸ General ▸ Visibility)

### 10차 작업 (같은 날) — PR #1 병합·퍼블릭 배포 완료
- **결과**: 사용자가 PR #1 병합(a782c2b, 04:15 UTC), README 렌더링 이상 없음 확인. main CI success(run 29554408244, ubuntu 테스트 + Windows 설치·GUI·웹 UI 검증). 저장소 PUBLIC 상태. windows-installer 브랜치 로컬·원격 삭제.
- **현재 진행도**: 프로젝트 공개 배포 상태 완성 — ZIP 다운로드 → install.bat → GUI 사용 가능
- **남은 미해결**: 없음

## 2026-08-01

### Phase 3 설계 — 배포·사용성 개선 (G2 인터뷰 → G4.5 계획)
- **목표**: "다운받아 쓰기 어렵다"는 문제의 원인 진단과 해결 설계
- **결정사항** (DECISIONS D1~D6):
  - D1 배포 대상은 연구실 동료 수십 명, 호스팅형 웹 서비스 배제 (설치형 유지)
  - D2 설치 여정 5단계 중 ②실행 경고·④사용법·⑤고장만 개선, ①입수·③설치 과정은 현행 유지
  - D3 업데이트는 2단 구조 — yt-dlp 전자동 + 앱 본체 원클릭
  - D4 새 버전 판정은 GitHub Releases 태그 기준 (main 커밋 아님)
  - D5 튜토리얼은 인터랙티브 오버레이 투어 (최초 실행 자동 + 수동 재호출)
  - D6 스포트라이트는 4분할 딤 패널(-alpha) — macOS Tk 9.0.3이 -transparentcolor 미지원임을
    실측 확인, 투명색 컷아웃 기법은 MacBook에서 검증 불가하여 기각
- **산출물**: `DECISIONS.md`(신규), `docs/PHASE3.md`(구현 계획 — 투어 문안·모듈 인터페이스·
  자기 교체 절차·검증 기준)
- **현재 진행도**: 설계·계획 완료, 구현 미착수
- **남은 미해결**: 앱 본체 자기 교체가 유일한 고위험 구간 (PHASE3 §5에서 교체 범위 최소화 +
  백업 복원으로 대응 설계)
- **다음 단계**: 계획 승인 후 구현 착수 (tour.py → updater.py → gui.py 통합 → README → 릴리스)
