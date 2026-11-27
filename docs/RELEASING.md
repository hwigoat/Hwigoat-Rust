# 개발 및 배포 관리

## 저장소 구조

- `hwigoat-source.zip`: 기준 소스 아카이브.
- `ci/prepare_*.py`: 버전별 소스 오버레이.
- `ci/update.go`, `ci/sign_release.py`: 업데이트 에이전트와 서명 도구.
- `release-notes/vX.Y.Z.md`: 버전별 공식 릴리스 설명.
- `.github/workflows/windows-build.yml`: Windows 빌드, 테스트, 서명 및 초안 생성.

## 신규 버전 배포

1. 브라우저·설치기·리소스 버전을 함께 변경하고 새 버전의 릴리스 노트 및 CHANGELOG를 작성합니다.
2. main에 변경을 등록하면 Windows 빌드와 테스트, 서명, 릴리스 초안 생성이 자동 실행됩니다.
3. [Actions](https://github.com/hwigoat/Hwigoat-Rust/actions)에서 빌드 성공을 확인합니다.
4. 초안의 설치기로 아래 수동 체크리스트를 검증한 뒤 [Releases](https://github.com/hwigoat/Hwigoat-Rust/releases)에서 공개합니다.
5. 기존 공개 버전의 설치기 및 서명 파일을 덮어쓰지 않습니다. 변경이 필요하면 버전을 올립니다.

릴리스 노트 파일을 수정하면 전용 워크플로가 기존 릴리스 설명을 동기화합니다. 릴리스의 공개 여부, 태그, 설치 파일과 서명은 변경하지 않습니다.

## 최초 1회 서명 설정 (기존 등록 키 유지)

- [Actions Variables](https://github.com/hwigoat/Hwigoat-Rust/settings/variables/actions): UPDATE_PUBLIC_KEY (32바이트 raw Ed25519 공개키의 Base64).
- [Actions Secrets](https://github.com/hwigoat/Hwigoat-Rust/settings/secrets/actions): UPDATE_SIGNING_KEY (32바이트 private seed의 Base64).
- 기존 사용자와의 신뢰 체인을 유지하려면 동일한 키를 사용해야 합니다. 비밀키는 안전한 오프라인 백업에만 보관하고 소스·채팅에 올리지 않습니다.
- 키 미설정 빌드는 자동 업데이트가 비활성화됩니다.

## 공개 전 Windows 수동 QA

- 신규 설치와 기존 버전 덮어쓰기, 정상 시작.
- 일반 브라우징, 탭 닫기, 설정 복귀, 주소창 및 창 조작.
- 일반/시크릿 세션 분리 및 기록 미저장 확인.
- Claude 및 외부 인증의 실제 동작과 제한 확인.
- 이전 버전에서 서명된 업데이트 확인, 다운로드, 정상 종료, 재실행 및 버전 변경 확인.
- 쿠키, 북마크, 설정 유지 확인.
- 네트워크 오류, 업데이트 중 재실행, 무효 서명 및 해시 불일치 시 안전한 실패 확인.

## 릴리스 자산

EXE: 사용자 설치기 · SHA256.txt: 해시 · update.json: 서명 대상 매니페스트 · update.sig: Ed25519 서명 · Cargo.lock: 빌드 의존성 기록.
