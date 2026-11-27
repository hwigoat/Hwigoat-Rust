# Hwigoat Rust

**일상의 브라우징을 더 가볍고 편리하게.**

Rust 기반 Windows x64용 브라우저 · Chromium(WebView2) 렌더링 엔진 · Public Beta

[최신 공개 베타](https://github.com/hwigoat/Hwigoat-Rust/releases) · [변경 기록](CHANGELOG.md) · [피드백 Discord](https://discord.com/channels/1213126669385338920/1575778721946796062)

## 주요 기능

| 기능 | 설명 |
| --- | --- |
| 브라우징 | 탭, 독립 창(최대 12개), 주소창 검색, 북마크, 방문 기록 |
| 인터페이스 | 흑백 테마, Chrome 스타일 창 조작, 주소창 첫 클릭 전체 선택 |
| 메모리 관리 | 성능 모드와 비활성 탭 관리 |
| 시크릿 탭 | WebView2 InPrivate 확인 후 별도 세션 사용 |
| 자동 업데이트 | 시작 시 및 실행 중 30분 간격 확인, 검증된 파일 다운로드 후 정상 종료 시 적용 |

## 다운로드

1. [Releases](https://github.com/hwigoat/Hwigoat-Rust/releases)에서 가장 최근 공개된 베타 버전을 선택합니다.
2. Assets에서 `Hwigoat_Rust_Setup_v버전_x64.exe`를 다운로드합니다.
3. 설치기를 실행합니다. 별도의 Rust 및 C++ 개발 도구 설치는 필요하지 않습니다.

Windows x64 및 Microsoft Edge WebView2 Runtime이 필요합니다. 설치기는 Authenticode 미서명이며 공식 업데이트 매니페스트는 Ed25519로 서명합니다.

## 업데이트

자동 업데이트 기능을 이용하려면 공개키가 포함된 1.0.3 이상을 설치해야 합니다. 설정에서 업데이트 확인 및 상태 조회를 할 수 있습니다. 다운로드 완료 후 브라우저를 정상 종료하고 다시 실행하면 새 버전이 적용되도록 설계되어 있습니다. 문제가 있으면 최신 공식 설치기로 수동 업데이트할 수 있습니다.

## 버전 기록

| 버전 | 핵심 변경 사항 |
| --- | --- |
| [1.0.6](release-notes/v1.0.6.md) | 독립 창, 창별 탭 및 공통 프로필 관리 (개발 후보) |
| [1.0.5](release-notes/v1.0.5.md) | 마지막 탭 종료, 설정 뒤로가기, 시크릿 탭, 업데이트 개선 |
| [1.0.4](release-notes/v1.0.4.md) | 주소창 클릭 전체 선택 |
| [1.0.3](release-notes/v1.0.3.md) | 서명된 자동 업데이트, 로그인 호환성 |

## 베타 안내

Windows CI 빌드와 테스트는 통과했지만 실제 Windows에서 자동 업데이트, 시크릿 세션 격리 및 외부 인증 서비스 호환성은 추가 검증이 필요합니다. WebView2 기반이므로 Google OAuth 등 임베디드 브라우저 로그인 제한이 있을 수 있습니다. 시크릿 모드는 익명 접속 기능이 아닙니다.

## 개발 및 기여

[개발·배포 관리 가이드](docs/RELEASING.md) · [보안 안내](SECURITY.md) · [GitHub Issues](https://github.com/hwigoat/Hwigoat-Rust/issues)

문의 시 브라우저 버전, Windows 버전, 재현 순서 및 오류 메시지를 공유해 주세요. 쿠키, 비밀번호, 인증 토큰 또는 개인 정보는 포함하지 마세요.
