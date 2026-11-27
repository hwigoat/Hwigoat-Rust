# Hwigoat Rust

Rust 기반 Windows용 Chromium(WebView2) 브라우저 · Public Beta

## 1.0.3 개발 후보
- 1.0.2 소스 ZIP과 `ci/prepare_103.py` 오버레이를 함께 빌드합니다.
- 로그인 사이트의 새 창 요청을 기존 탭과 연결되는 WebView2 기본 팝업으로 처리합니다. 인증 사이트는 비활성 탭 메모리 절약 및 해제에서 보호합니다.
- Google OAuth 등 임베디드 브라우저 자체 제한은 우회하지 않습니다. 기본 브라우저에서 Claude 열기를 제공합니다. 세션 자동 이전은 지원하지 않습니다.
- 서명된 업데이트를 실행 시 확인하고 정상 종료 후 설치합니다. 재실행 시 새 버전이 적용됩니다. 사용자 프로필을 삭제하지 않습니다.
- 기존 사용자는 공개키가 내장된 1.0.3을 먼저 수동 설치해야 합니다.

## 최초 1회 서명 설정
1. 신뢰할 수 있는 로컬 환경에서 Ed25519 키를 생성합니다.
2. [Actions Variables](https://github.com/hwigoat/Hwigoat-Rust/settings/variables/actions)에 UPDATE_PUBLIC_KEY (32바이트 raw 공개키의 Base64)를 등록합니다.
3. [Actions Secrets](https://github.com/hwigoat/Hwigoat-Rust/settings/secrets/actions)에 UPDATE_SIGNING_KEY (32바이트 private seed의 Base64)를 등록합니다. 비밀키를 GitHub 소스 파일이나 채팅에 올리지 마세요.
4. 키를 내장한 빌드를 위해 [Actions](https://github.com/hwigoat/Hwigoat-Rust/actions/workflows/windows-build.yml)에서 Run workflow를 실행합니다. draft_release 옵션은 서명된 미공개 릴리스 초안을 생성합니다.
5. 실제 Windows에서 설치, 로그인, 정상 종료, 기존 데이터 유지, 서명 실패 및 업데이트 동작을 검증하고 릴리스 초안을 공개합니다.

비밀키는 안전하게 오프라인 백업하고 동일한 키를 유지하세요. 키를 설정하지 않은 빌드는 자동 업데이트를 비활성화합니다. 업데이트 매니페스트의 Ed25519 서명은 Windows Authenticode 서명과 별개입니다. 현재 설치기는 Authenticode 미서명입니다.

[공식 피드백 Discord](https://discord.com/channels/1213126669385338920/1575778721946796062) · [릴리스](https://github.com/hwigoat/Hwigoat-Rust/releases)
