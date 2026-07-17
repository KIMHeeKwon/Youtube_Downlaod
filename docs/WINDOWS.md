# Windows 원클릭 설치 가이드

작성일: 2026-07-17
대상: 개발 지식이 없는 일반 Windows 10/11 사용자

---

## 1. 설치 방법 (3단계)

1. **다운로드**: GitHub 저장소 페이지에서 `Code ▸ Download ZIP` 클릭
   (https://github.com/KIMHeeKwon/Youtube_Downlaod)
2. **압축 해제**: 받은 ZIP을 원하는 위치(예: `C:\Apps\`)에 풀기
3. **설치 실행**: 폴더 안 `windows\install.bat` **더블클릭**

설치가 자동으로 진행됩니다 (관리자 권한 불필요, 수 분 소요):

| 단계 | 내용 |
|------|------|
| uv | Python 3.12 및 라이브러리를 프로젝트 폴더 안에 격리 설치 |
| deno | yt-dlp의 전체 화질 추출에 필요한 JS 런타임 |
| ffmpeg | 공식 빌드(gyan.dev)에서 내려받아 `tools\`에 배치 |
| 바로가기 | 바탕화면에 **"YouTube Downloader"** 생성 |

완료 후 바탕화면의 **YouTube Downloader**를 더블클릭하면 **GUI 앱 창이 바로 열립니다**
(콘솔 창 없음 — `pythonw.exe`로 실행). 주소를 붙여넣고 [다운로드]를 누르면
진행률 바가 표시되고, [저장 폴더 열기]로 결과를 바로 확인할 수 있습니다.
해상도 상한·코덱·자막 언어·재생목록 일괄 다운로드를 모두 지원합니다.

## 2. 구성 파일

| 파일 | 역할 |
|------|------|
| `gui.py` | 데스크톱 GUI 앱 (tkinter, 바탕화면 바로가기의 대상) |
| `windows/install.bat` | 더블클릭 진입점 (install.ps1을 실행 정책 우회로 호출) |
| `windows/install.ps1` | 실제 설치 로직 (uv/deno/ffmpeg/의존성/바로가기) |
| `windows/start.bat` | (보조) 웹 UI 기동 + 브라우저 자동 오픈 — GUI 대신 브라우저를 선호할 경우 |

## 3. 설계 원칙

- **ffmpeg 비동봉**: GPL 재배포 의무 회피를 위해 저장소에 바이너리를 포함하지 않고
  (DESIGN §6.1), 설치 시점에 사용자 PC가 공식 소스에서 직접 내려받는다.
  `tools/`는 .gitignore로 커밋이 차단된다.
- **시스템 비오염**: 모든 구성요소는 사용자 폴더(`%USERPROFILE%`)와 프로젝트 폴더
  안에만 설치된다. 관리자 권한·레지스트리 변경 없음.
- **CI 검증**: `.github/workflows/ci.yml`의 `windows-install` 잡이 실제
  windows-latest 러너에서 install.ps1 실행 → ffmpeg 인식 → pytest → GUI
  위젯 생성(selftest) → 웹 UI 기동/400 응답까지 자동 검증한다.

## 4. 문제 해결

| 증상 | 해결 |
|------|------|
| "Windows에서 PC를 보호했습니다" 경고 | [추가 정보] → [실행] (서명되지 않은 스크립트라 표시됨) |
| 다운로드가 어느 날 안 됨 | 터미널에서 프로젝트 폴더로 이동 후 `uv sync --upgrade` (yt-dlp 갱신) |
| 포트 충돌 (8000 사용 중) | `windows\start.bat`의 `--port 8000`을 다른 번호로 수정 |
