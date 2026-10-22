# 팀 정적분석 코드 출처

- 저장소: https://github.com/GreatJung1/KnitCode
- 기준 브랜치: main
- 기준 커밋: `06422ca2f57cff436efdf6b415a597d5c547c986`
- 가져온 날짜: 2026-10-22
- 위치: `static_analysis/`
- 범위: 루트 소스·문서·검증 스크립트, `tests/`, `examples/`를 원본 그대로 포함.
- 제외: `validation/`에 저장된 과거 분석 결과. 실행에 필요한 소스는 제외하지 않음.

기존 Git 분석 기준: `M0282/knitcode_github`의
`9222562174b6d8afedf08bf728604747288fe33e`.

이 작업 브랜치는 기존 `knitcode_github/main`에서 분기한 통합 브랜치다.
팀 저장소의 Fork나 Git 병합 커밋은 아니며, 위 커밋의 소스 스냅샷을 포함한다.
팀 코드 갱신 시 해당 폴더와 기준 커밋을 함께 갱신하고 회귀 테스트를 실행한다.
Git 분석과 연결하는 어댑터는 루트의 `static_bridge.py`, `integrated_cli.py`,
`analyzer/integration.py`에 있다. 팀 엔진의 분석 규칙은 변경하지 않았다.

## 회귀 검증

```powershell
py -m unittest discover -s tests -v
Push-Location static_analysis
py -m unittest discover -s tests -v
Pop-Location
```

각 테스트 묶음은 서로의 루트 모듈 이름이 충돌하지 않도록 별도 프로세스에서 실행한다.
팀 README에는 현재 저장소에 없는 과거 문서 링크가 포함되어 있을 수 있다.

## 이번 통합 검증 결과

- 팀 정적분석 기존 테스트 265개 통과.
- 기존 Git 분석 6개 + 새 통합 테스트 4개, 총 10개 통과.
- 실제 임시 Git 저장소에서 작성자 변경, 함수 수정·삭제, 직접 호출 연결,
  미커밋 변경 격리, 과거 커밋 선택, 단일 clone과 원격 브랜치 선택을 검증.
- GitHub URL 테스트는 네트워크 전송만 로컬 Git 저장소로 대체했다.
  실제 GitHub clone 및 인증 API 네트워크 요청은 이번 환경에서 검증하지 않았다.
- HTML/JSON 생성과 스크립트 삽입 방어를 검증했다.
  실행 환경에 브라우저 실행 파일이 없어 브라우저 화면 검증은 수행하지 못했다.
