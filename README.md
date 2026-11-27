# Hwigoat Rust

Rust 기반 Windows용 Chromium(WebView2) 브라우저 · Public Beta

## 1.0.2 개발 목표
- 흑백 Chrome 스타일 UI, 기존 사용자 설정 및 프로필 유지
- 탭 줄 빈 공간 더블클릭으로 최대화/복원, 이동 제스처 분리
- 성능 모드 및 Discord 피드백 유지
- 개발 도구가 필요 없는 사전 컴파일 설치 패키지

## 빌드 및 배포
1. 최신 `hwigoat-source.zip`을 저장소 루트에 업로드합니다.
2. [Actions](https://github.com/hwigoat/Hwigoat-Rust/actions)에서 Windows precompiled installer 빌드를 확인합니다.
3. 성공한 실행의 Artifacts에서 Hwigoat-Rust-Windows-x64를 다운로드합니다.
4. 실제 Windows PC에서 설치, 웹 렌더링, 창 이동·최대화·복원, 패치 및 사용자 데이터 보존을 확인합니다.
5. Actions에서 수동 실행 시 draft_release 옵션으로 미공개 릴리스 초안을 만들 수 있습니다. 테스트 후 검토하고 공개합니다.

빌드 아티팩트는 코드 서명 전 테스트용이며 자동 공개되지 않습니다. SHA-256은 무결성 확인용이지 배포자 인증용 서명이 아닙니다. 자동 업데이트 클라이언트 및 서명 검증은 아직 구현되지 않았습니다. 기존 사용자는 수동 업데이트가 필요합니다.

[공식 피드백 Discord](https://discord.com/channels/1213126669385338920/1575778721946796062) · [릴리스](https://github.com/hwigoat/Hwigoat-Rust/releases)
