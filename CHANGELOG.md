# 변경 기록 · Changelog

공개 베타 버전별 주요 변경 사항을 최신순으로 기록합니다.

## [1.1.1](release-notes/v1.1.1.md) — Fluid Motion (개발 후보)
- 탭 바 내부에서 포인터에 고정된 탭 미리보기, 화면 프레임에 맞춘 transform.
- 네이티브 드래그 위치 갱신 목표 간격 8ms, 화면 가장자리에서 미리보기 기준점 유지.
- 도킹 표시의 연속 이동 및 경계 깜빡임 완화, 취소 시 잔상 제거 회귀 테스트.

## [1.1.0](release-notes/v1.1.0.md) — Precision & Stability
- 네이티브 DWM 드래그 미리보기 창의 실시간 마우스 추적.
- 넓어진 도킹 감지 영역, 강조 표시 및 원본 탭 보존.
- 네이티브 마우스 종료/취소 처리, 중복 IPC 방지, 다중 모니터 창 위치 보정.
- 블랙 테마 가독성 개선 및 빠른 CI 문법/회귀 테스트, 생성 소스 아티팩트.

## [1.0.8](release-notes/v1.0.8.md) — Tab Docking & Visual Clarity
- 기존 창의 탭 바에 놓아 탭 합치기, 같은 창의 탭 순서 변경.
- 드래그 중 삽입 위치 표시, 활성 탭 및 도구 모음 대비 개선.
- 마지막 탭 이동 후 빈 원래 창만 닫기, 기존 WebView 유지.

## [1.0.7](release-notes/v1.0.7.md) — Tab Tear-Off
- 탭 바 밖으로 드래그 후 놓아 독립 창으로 분리.
- 활성 WebView 재부착 및 프로세스 전체에서 고유한 탭 ID로 이벤트 라우팅.
- 분리 취소, 일반 클릭 구분, 단일 탭 창 이동.

## [1.0.6](release-notes/v1.0.6.md) — Multi-Window Experience
- 독립 창 열기, 창별 탭과 탐색 관리.
- 하나의 프로필 및 세션 기록 저장기로 로그인·북마크·설정 공유.
- 마지막 창 종료 시에만 자동 업데이트 적용.

## [1.0.5](release-notes/v1.0.5.md) — Browser Experience Update
- 마지막 탭 닫기 시 정상 종료.
- 설정 뒤로가기와 키보드 탐색 개선.
- 시크릿 탭 전용 표시 및 InPrivate 확인.
- 시작 시 및 30분 간격 업데이트 확인, 종료 시 다운로드 경쟁 조건 개선.
- 자동 서명 릴리스 초안 생성.

## [1.0.4](release-notes/v1.0.4.md) — Address Bar Experience
- 주소창 최초 클릭 전체 선택, 재클릭 편집.
- 주소 입력값 유지 및 UI 회귀 테스트.

## [1.0.3](release-notes/v1.0.3.md) — Auto Update & Login Compatibility
- 서명된 자동 업데이트 에이전트 및 설정 메뉴.
- 주요 OAuth 팝업·인증 사이트 처리 개선.
- 기본 브라우저에서 Claude 열기.

## 1.0.2 — Windows Experience & Distribution
- 상단 더블클릭 최대화·복원 및 드래그 구분.
- Windows 사전 컴파일 설치기와 GitHub Actions 기반 빌드.

각 버전의 실제 검증 상태와 제한 사항은 해당 릴리스 노트를 참조하세요.
