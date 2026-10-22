# KnitCode — 팀 정적분석 + GitHub 변경 분석

이 브랜치는 팀 `GreatJung1/KnitCode`의 정적분석 엔진에 기존 Git Insights를 연결한 통합 버전입니다.
원본 엔진과 테스트는 `static_analysis/`에 보관하고, 기존 Git 분석 실행 방식도 유지합니다.
가져온 소스와 기준 커밋은 [UPSTREAM_STATIC_ANALYSIS.md](UPSTREAM_STATIC_ANALYSIS.md)에 기록했습니다.

## 통합 실행 (Windows)

Python 3.10 이상과 Git이 필요합니다. 추가 pip 패키지는 없습니다.

```powershell
py integrated_cli.py https://github.com/dbader/schedule --commits 50 --output integrated_output
start integrated_output\index.html
```

또는 `run_integrated_windows.bat`를 실행하고 대상 URL/로컬 Git 경로를 입력합니다.
다시 분석할 때는 기존 결과를 덮어쓰지 않도록 `--output integrated_output_2`처럼 새 폴더를 지정하세요.

```powershell
py integrated_cli.py "C:\Users\우성한\Downloads\target_repo" --revision main --commits 100 --output integrated_output_2
```

- `--revision`: 분석할 브랜치·태그·커밋. 기본 HEAD.
- `--source-root src`: 팀 엔진에 전달할 import 루트. 반복 지정 가능, 생략 시 자동 감지.
- `--since YYYY-MM-DD`, `--until YYYY-MM-DD`, `--aliases aliases.json`, `--pair-limit 40`: Git 분석 범위.
- `--github-api --api-commits 20`: GitHub URL의 PR·Issue·Checks·Status 조회. `GITHUB_TOKEN`은 선택 환경변수.
- `--static-timeout 600`: 정적분석 최대 시간(초).

### 통합 결과

| 파일 | 내용 |
|---|---|
| `index.html` | 함수별 작성자·변경 근거·기준 커밋의 직접 호출 후보, 검색·필터, 개별 보고서 링크 |
| `integrated_result.json` | 동일 커밋을 기준으로 연결한 구조화 결과 |
| `static/report.html` | 팀 정적분석 보고서 |
| `static/*_result.json` | AST, 심볼, 호출 그래프 원본 분석 결과 |
| `git/report.html` | 기존 Git Insights 전체 보고서 |
| `git/git_insights.json` | 작성자, 함수 변경, 동시 수정, 집중 영역, 테스트 후보, 선택적 API 결과 |

통합 실행은 분석 대상의 커밋을 한 번 확정하고 해당 커밋의 파일을 임시 폴더에 복원합니다.
로컬 미커밋 변경과 무관하게 정적분석·Git 분석의 커밋이 일치하며, 대상 Python 코드는 실행하지 않습니다.
심볼릭 링크와 서브모듈 내부는 제외하고 경고를 기록합니다. Git이 추적하는 일반 파일을 복사하므로
대형 저장소는 임시 디스크 공간과 시간이 필요합니다. GitHub 입력은 전체 Git 이력을 한 번 clone합니다.

**연결 의미:** `파일 경로 + 한정 함수명`이 같은 기준 커밋의 심볼 후보를 찾습니다.
삭제·이동·이름 변경은 미연결될 수 있고 중복 정의는 연결을 보류합니다.
과거 함수와 현재 함수의 동일성, 과거 호출 관계, 실제 실행 영향 범위를 증명하지 않습니다.
직접 호출 관계는 팀 엔진의 may-call·확실성 근거를 그대로 유지합니다.
파일 동시 수정 관계는 호출 관계와 구분하여 기존 Git 보고서에서 확인합니다.

테스트 실행 방법: [UPSTREAM_STATIC_ANALYSIS.md](UPSTREAM_STATIC_ANALYSIS.md#회귀-검증).

---

# 기존 Knitcode Git Insights v2 사용법

외부 Python 프로젝트의 GitHub URL을 받아 Git 변경 이력만 분석합니다.
기존 v0.6 폴더에 덮어쓸 필요 없는 독립 실행본이며 모든 Python·HTML 소스를 편집할 수 있습니다.

## Windows 시작

1. ZIP을 완전히 압축 해제합니다.
2. Python 3.10 이상과 Git이 설치되어 있어야 합니다. 추가 pip 설치는 없습니다.
3. `run_windows.bat`를 더블클릭합니다.
4. 분석 대상 주소(예: https://github.com/dbader/schedule)를 붙여넣습니다.
5. 분석할 최대 커밋 수를 입력하거나 Enter를 누릅니다. 처음에는 50개 정도로 확인할 수 있습니다.
6. 완료하면 브라우저에 보고서가 열립니다. `reports/실행시각/report.html`에 저장됩니다.

터미널에서도 실행할 수 있습니다.

```powershell
py main.py
```

고급 옵션:

```powershell
py git_insights_cli.py https://github.com/dbader/schedule --commits 100 --output my_report
start my_report\report.html
```

주소만 바꾸면 다른 대상 저장소를 분석합니다. 로컬 Git 경로도 CLI 위치 인자로 사용할 수 있습니다.
`--revision 브랜치/태그/커밋`, `--since 2024-01-01`, `--until 2025-12-31`,
`--pair-limit 40`, `--aliases aliases.json`을 지원합니다.
이메일 별칭 파일 예: `{"old@example.com": "person@example.com"}`.

## 보고서에 포함되는 내용

- 작성자별 주요 수정 파일·함수와 작업 유형 분포
- 오류 수정으로 추정한 커밋의 메시지, 분류 근거, 실제 코드 diff
- 작성자 × 폴더 히트맵과 작업 유형 누적 막대그래프
- 파일 동시 변경 네트워크, 함께 바뀐 횟수, 방향별 조건부 비율, Jaccard
- 함수 추가·삭제·수정, 시그니처와 조건 분기·return·raise 수, 호출 표현의 추가·제거
- 작성자·유형·날짜·검색 필터, 관계를 선택하면 근거 커밋 표시
- 시간순 커밋에서 파일을 펼치면 함수 변경 요약과 실제 diff 표시

오류 수정만 보고 싶으면 상단 작업 유형에서 '오류 수정'을 선택합니다.
특정 함수 이력은 검색창에 함수명을 입력하고 파일 상세를 펼칩니다.
HTML은 생성된 결과를 보는 파일입니다. 새 주소 분석은 실행기를 다시 실행해야 합니다.

## 편집 위치

- `main.py`: URL 입력과 로컬 실행
- `git_insights_cli.py`: 대상 clone, 분석 옵션, HTML·JSON 저장
- `analyzer/git_insights.py`: 작성자·작업 유형·동시 변경·함수 비교 로직
- `analyzer/repository_source.py`: GitHub URL 해석
- `analyzer/templates/git_insights.html`: 화면 디자인·그래프·필터
- `tests/test_git_insights.py`: 별도 대상 저장소를 이용한 통합 테스트
- `sample_report/report.html`: dbader/schedule의 실제 3개 커밋으로 만든 소규모 결과 예시

## 분석 범위와 한계

기본 브랜치 HEAD에서 도달 가능한 커밋 중 최대 500개를 위상 순서로 선택합니다.
전체 이력을 clone하므로 큰 저장소는 다운로드·분석 시간이 오래 걸릴 수 있습니다.
모든 브랜치를 합산하지 않으며 분석 상한과 제외 기준은 보고서에 표시합니다.
공개 저장소는 일반적으로 별도 인증 없이 사용합니다. 비공개 저장소는 Git 인증과 권한이 필요합니다.
clone 제한 시간은 300초입니다. 네트워크 오류나 권한 문제는 콘솔에 표시합니다.

작성자는 Git 이름·이메일 기준이며 인증된 GitHub 계정과 동일하다고 보장하지 않습니다.
오류 수정 여부와 작업 유형은 커밋 메시지 규칙에 의한 추정입니다. Issue/PR 본문 분석이나
실제 오류 해결 검증은 하지 않습니다. 함수 구조 변화와 diff를 함께 확인하세요.
Python 구문을 해석할 수 없는 파일은 진단을 표시하고 나머지를 계속 분석합니다.
주석/공백만 변경된 경우 함수 AST 변화로 집계하지 않습니다.
함수 이름 변경·이동은 추가/삭제로 나타날 수 있습니다.

동시 변경은 코드 의존성이나 원인 관계가 아닙니다. 최초·병합·40개 초과 파일 변경 커밋은
동시 변경 집계에서 제외합니다. 병합 커밋의 충돌 해결 변경 상세도 분석하지 않습니다.
대상 코드 실행·의존성 설치·AI 자동 수정 기능은 포함하지 않습니다.

## 검증

```powershell
py -m unittest discover -s tests -v
```

외부 URL의 네트워크 전송만 별도 로컬 테스트 저장소로 대체하고 실제 clone →
작성자/커밋/함수 분석 → HTML 생성까지 확인합니다. 추가로 dbader/schedule 실제 URL을
이용한 3커밋 분석 결과를 예시로 동봉했습니다.

# v2 추가 기능과 API 설정

## 1. 변경 집중 영역

최초·병합·얕은 clone 경계 커밋을 제외하고 파일/함수별 변경 횟수, 작성자 수,
오류 수정 추정 횟수와 근거 커밋을 집계합니다. 화면의 필터와 연동됩니다.
분석 대상 커밋 범위 안에서의 통계이며 전체 프로젝트 품질 점수는 아닙니다.

## 2. 코드·테스트 동반 변경

분석 기준 리비전의 테스트 파일 최대 200개를 AST import와 파일명 규칙으로 색인합니다.
코드 파일별 관련 테스트 후보, 해당 후보의 동반 변경 여부, 같은 커밋에서 바뀐
테스트 전체 목록과 변경 함수를 보여줍니다. 이는 함수 수준 실행 커버리지나
역사적 테스트 연결을 보장하지 않습니다. 삭제된 테스트나 동적 import는 놓칠 수 있습니다.

## 3. Issue·PR·CI 연결

실행기에서 API 조회 질문에 y를 입력하거나 아래 명령을 사용합니다.

```powershell
py git_insights_cli.py https://github.com/dbader/schedule --commits 100 --github-api --api-commits 20 --output my_report
```

API는 선택 옵션입니다. 공개 데이터는 토큰 없이 시도할 수 있지만 GitHub 호출 제한을
받을 수 있습니다. 기본 API 조회 대상은 분석 순서의 앞 20개 커밋이며 한 번 실행에
최대 120번 요청, 엔드포인트당 최대 3페이지(100건/페이지), 커밋당 Issue 참조 최대 20개입니다.
실패/권한 부족/호출 한도는 HTML에 기록되며 나머지 Git 분석은 유지합니다.
Checks와 Status가 비어 있으면 통과로 판정하지 않습니다.
PR의 CI가 아니라 분석 대상 커밋 SHA의 수집 시점 CI 기록입니다.
Issue 연결은 커밋/PR의 #번호 또는 Issue URL 참조 후보이며 실제 해결 확정은 아닙니다.

### 필요한 API

모두 GitHub REST API이며 별도 AI API는 필요 없습니다.

| 용도 | GET 엔드포인트 | Fine-grained PAT 저장소 권한 |
|---|---|---|
| 커밋에 연결된 PR | /repos/{owner}/{repo}/commits/{sha}/pulls | Pull requests: Read-only |
| 참조된 Issue | /repos/{owner}/{repo}/issues/{number} | Issues: Read-only |
| 테스트·빌드 등 검사 | /repos/{owner}/{repo}/commits/{sha}/check-runs | Checks: Read-only |
| 기존 CI 상태 | /repos/{owner}/{repo}/commits/{sha}/status | Commit statuses: Read-only |

공개 리소스는 위 권한/인증 없이 조회 가능한 API입니다. 인증이 필요한 대상은
토큰 소유자에게 원래 접근 권한이 있어야 합니다. 비공개 저장소 clone 인증은
로컬 Git 자격 증명으로 별도 처리하며 GITHUB_TOKEN을 clone URL에 넣지 않습니다.
Actions 실행 로그/아티팩트 다운로드 API는 이번 구현에 포함하지 않았습니다.

### 토큰 설정 (선택)

GitHub Settings → Developer settings → Personal access tokens → Fine-grained tokens에서
대상과 읽기 권한을 지정해 발급합니다. 다른 사람의 공개 저장소를 읽는 경우 해당
소유자를 선택할 수 없는 상황도 있으므로 우선 무인증 조회를 사용할 수 있습니다.
비공개 조직 저장소에는 조직 승인이 필요할 수 있습니다.

PowerShell에서 압축을 푼 폴더로 이동한 다음, 아래 방식으로 토큰을 화면에 표시하지 않고 입력합니다.
현재 PowerShell에서 실행한 Python에만 전달됩니다. 토큰을 소스/README에 적지 마세요.

```powershell
$secureToken = Read-Host "GitHub token" -AsSecureString
$env:GITHUB_TOKEN = [System.Net.NetworkCredential]::new("", $secureToken).Password
py main.py
Remove-Item Env:GITHUB_TOKEN
```

토큰은 환경변수에서만 읽고 HTML/JSON에 저장하지 않습니다.

공식 참고:
- https://docs.github.com/en/rest/commits/commits#list-pull-requests-associated-with-a-commit
- https://docs.github.com/en/rest/issues/issues#get-an-issue
- https://docs.github.com/en/rest/checks/runs#list-check-runs-for-a-git-reference
- https://docs.github.com/en/rest/commits/statuses#get-the-combined-status-for-a-specific-reference

기존 README의 'Issue/PR 본문 분석을 하지 않음'은 API 미사용 모드에 해당합니다.
v2 API 모드에서는 연결된 PR과 참조 Issue의 제목/본문을 표시하며, 내용에 대한
AI 원인 분석이나 수정 성공 판정은 수행하지 않습니다.

## 이번 실행 검증 결과

통합 테스트 6개 통과. 실제 dbader/schedule의 3개 커밋 분석과 PR API 연결 확인.
일부 Issue/CI 요청은 GitHub HTTP 403 호출 제한으로 미수집되어 예시 보고서에
경고가 포함됩니다. 인증 토큰을 이용한 비공개 저장소 조회는 검증하지 않았습니다.

