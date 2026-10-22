# KnitCode 변경 검토 패치

2026-10-22 / 대상: `M0282/knitcode_github`의 팀 정적분석 통합본.
확인한 main 커밋: `eab5430b5bbf6b20caf9acf6e46acb3f88398bcf`.

이 패치는 새 파일만 추가한다. 기존 `integrated_cli.py`, `main.py`, 팀 정적분석
엔진과 기존 보고서 실행 방식은 유지된다. 새 기능은 `change_review_cli.py`로 실행한다.
Python 3.10 이상과 Git이 필요하며 추가 pip 설치나 AI API 키는 필요 없다.

이 버전은 변경 검토 보고서와 함께 기존 GitHub·Git 변경 분석 보고서도 생성한다.
결과 첫 화면의 `GitHub·Git 변경 분석` 링크에서 작성자별 변경, 함수 이력,
파일 동시 수정, 집중 영역, 테스트 후보를 확인한다. PR·Issue·CI는 선택 옵션이다.

## 1. 가장 간단한 실행: 최근 커밋의 변화

프로젝트 폴더에서 PowerShell을 열고 실행한다.

```powershell
py change_review_cli.py https://github.com/dbader/schedule
start reports\change_review\index.html
```

PR·Issue·Checks·Status까지 연결하려면 GitHub URL과 다음 옵션을 사용한다.

```powershell
py change_review_cli.py https://github.com/aboul3la/Sublist3r --github-api --api-commits 20 --output reports\sublist3r_review
start reports\sublist3r_review\index.html
```

토큰 없이 공개 API를 시도할 수 있지만 호출 제한을 받을 수 있다. 필요하면 기존
README의 방식대로 `GITHUB_TOKEN` 환경변수를 설정한다. 토큰은 보고서에 저장하지 않는다.
로컬 저장소 경로를 입력하면 PR·Issue·CI API는 사용할 수 없고 Git 이력 분석은 유지된다.

주소는 분석할 저장소의 주소로 바꾼다. 기본 비교는 `HEAD~1` → `HEAD`이며,
단일 최초 커밋만 있는 저장소에서는 이전 커밋이 없어 실행할 수 없다.
병합 커밋의 기본 비교는 첫 번째 부모와의 차이다.
이번 변경 파일과 후보가 적거나 추천이 없는 것은 정상일 수 있다.

## 2. 로컬 Git 저장소 비교

```powershell
py change_review_cli.py "C:\Users\우성한\Downloads\target_repo" --base "HEAD~3" --head HEAD --output reports\review_last3
start reports\review_last3\index.html
```

두 끝점 사이의 최종 상태 차이를 분석한다. 중간 커밋에서 수정 후 원복한 내용은
순변경에서 제외된다. 로컬 미커밋·스테이지·미추적 파일은 분석에 포함하지 않는다.
미커밋 작업을 포함하려면 분석 대상 저장소에서 먼저 원하는 변경을 커밋한다.

## 3. PR 방식으로 브랜치 변경 비교

```powershell
py change_review_cli.py "C:\Users\우성한\Downloads\target_repo" --base main --head feature/my-change --merge-base --output reports\review_feature
start reports\review_feature\index.html
```

`main`, `feature/my-change`는 실제 대상 저장소의 브랜치명으로 바꾼다.
`--merge-base`는 두 브랜치의 공통 조상부터 feature 끝점까지 비교한다.
로컬 경로 입력은 자동 fetch를 하지 않으므로 필요하면 먼저 대상 저장소에서
`git fetch origin`을 실행하고 `origin/main`, `origin/feature/my-change`를 지정한다.
GitHub URL 입력은 한 번 clone한 뒤 원격 브랜치 이름도 해석한다.
서로 다른 Fork의 브랜치를 자동으로 가져오는 기능은 포함하지 않았다.

## 4. 보고서 읽는 방법

| 탭 | 분석 내용 | 해석 |
|---|---|---|
| 변경 내용 | 파일·함수 추가/삭제/본문·시그니처 변화 | 시그니처 변화는 호출부 검토 신호이며 호환성 오류 확정 아님 |
| 구조 비교 | CALLS, INSTANTIATES, INHERITS, CONTAINS 관계 추가/제거 | 두 스냅샷의 정적 관계 집합 차이 |
| 영향 후보 | 변경 함수를 직접·간접 호출하는 후보, 거리와 경로 | 실제 런타임 영향이나 결함 발생을 확정하지 않음 |
| 테스트 후보 | 호출 경로, 절대 import, 파일명, 테스트 자체 변경 | 실행 커버리지나 테스트 성공을 보장하지 않음 |
| 동시 수정 후보 | 과거 같이 바뀌었으나 이번에는 빠진 파일 | 수정 누락 확정이 아닌 검토 권고 |

`base`는 변경 전, `head`는 변경 후다. 삭제된 함수의 기존 호출부를 놓치지 않도록
두 시점의 영향 후보를 따로 제공한다. 테스트를 실제 실행할 때는 `head` 후보를
확인한다. `base`의 테스트는 삭제·이동되었을 수 있다.
호출 경로를 펼치면 팀 엔진이 생성한 may-call, 추론 규칙, 위치 근거를 볼 수 있다.
미변경 파일 표시는 그 파일이 두 끝점 사이에서 바뀌지 않았다는 뜻이다.
변경 파일 표시만으로 해당 호출부까지 수정되었다고 판단하지 않는다.

### 동시 수정 추천의 기준

- 비교 시작 `base` 및 그 조상만 학습한다. `head`나 이후 변경은 학습하지 않는다.
- 기본 최대 200커밋, 같은 두 파일이 3회 이상 함께 변경된 경우.
- 변경 파일 A가 바뀐 적격 커밋 중 B도 바뀐 비율이 60% 이상인 경우.
- 최초·병합·40개 초과 파일 변경·얕은 clone 경계는 기존 집계 규칙에 따라 제외.
- B가 이번 변경에 이미 포함되어 있거나 head에서 존재하지 않으면 추천하지 않음.
- 경로 변경의 장기 이력 통합은 하지 않는다. 이번 범위의 Git 파일 rename만 대응.

이력이 짧으면 결과가 없을 수 있다. 시연할 때만 임계값을 낮출 수 있으나
작은 표본은 신뢰도가 낮다. 퍼센트는 버그 확률이 아닌 관측된 조건부 비율이다.

```powershell
py change_review_cli.py https://github.com/OWNER/REPO --base "HEAD~5" --head HEAD --commits 300 --min-support 2 --min-confidence 0.5 --output reports\review_demo
```

## 5. 설정

| 옵션 | 기본값 | 의미 |
|---|---|---|
| `--base` / `--head` | `HEAD~1` / `HEAD` | 비교 시작/종료 리비전 |
| `--merge-base` | 꺼짐 | 공통 조상 기준 PR 방식 비교 |
| `--commits` | 200 | base까지의 과거 이력 최대 개수 |
| `--pair-limit` | 40 | 동시 수정 집계의 커밋당 파일 수 상한 |
| `--max-depth` | 5 | 역방향 CALLS 탐색 깊이 |
| `--max-nodes` | 500 | 변경 심볼 하나당 영향 노드 상한 |
| `--min-support` | 3 | 최소 동시 수정 횟수 |
| `--min-confidence` | 0.6 | 방향별 동시 수정 비율 하한 |
| `--source-root` | 자동 | import 루트, 반복 지정 가능 |
| `--static-timeout` | 600 | 시점별 정적분석 시간 제한(초) |
| `--source-limit` | 500000 | 함수 이력 비교용 소스 크기 상한(byte), 정적 엔진 상한과 별개 |
| `--output` | `reports/change_review` | 결과 폴더 |

이 실행기는 두 시점의 정적분석을 수행하므로 기존 단일 스냅샷 분석보다 시간이
더 걸릴 수 있다. 출력 폴더가 비어 있지 않으면 중단한다. 다시 실행할 때는
`--output reports/review_2`처럼 새 이름을 사용한다.

## 6. 산출물과 검증

- `index.html`: 인터넷 없이 열 수 있는 보고서, 검색·시점 필터·상세 근거.
- `change_review.json`: 전체 결과, 이력 범위·상한·경고·근거 커밋.
- `base/`, `head/`: 각 시점의 원본 정적분석 HTML·JSON·CSV.
- `git/report.html`, `git/git_insights.json`: head 기준 기존 GitHub·Git 변경 분석.

동시 수정 누락 후보는 미래 정보가 섞이지 않도록 base까지의 이력으로 계산하지만,
`git/report.html`은 사용자가 방금 비교한 head 커밋까지 포함해서 보여준다.

```powershell
py -m unittest discover -s tests -p test_change_review.py -v
py -m unittest discover -s tests -v
```

이번 패치 검증 범위:
실제 임시 Git 이력을 생성하여 시그니처·삭제 함수·직접/간접 호출·테스트 추천,
동시 수정의 과거 시점 제한, 미커밋 격리, 파일 rename, 구문 오류, 탐색 상한,
순환·중복 정의, 원격 브랜치 선택과 merge-base를 검증한다.
원격 URL 테스트는 네트워크 전송만 로컬 저장소로 대체한다. 실제 외부 네트워크와
인증은 이번 패치 검증에 포함하지 않았다. 대상 코드나 테스트 자체는 실행하지 않는다.
브라우저 실행 파일이 없는 환경이므로 실제 브라우저 화면 검증은 수행하지 못했다.
HTML 데이터 삽입 방어·JSON·JavaScript 문법·보고서 링크는 검사한다.

## 7. 남은 한계

함수 이동/이름 변경은 보통 삭제+추가다. 중복 정의는 후보를 모두 표시한다.
현재 엔진의 정적 호출 해석 한계를 그대로 가지며, 전역 상수·클래스 속성·설정
변경에 대한 일반적인 데이터 의존성 전파는 구현하지 않았다.
함수 AST 변화가 없어도 동작이 바뀔 수 있으므로 전체 변경 파일도 확인해야 한다.
새로운 미해결 호출의 원인을 자동 판정하거나 인자 타입 호환성을 검사하지 않는다.
그래프 관계 비교는 경로·종류·정규 이름 기준이므로 단순 줄 이동을 변화로
세지 않지만, 동일 관계의 호출 횟수·근거 변화는 별도 차이로 출력하지 않는다.
테스트 통과 개수는 구현 회귀 검증 결과이며 추천 정확도(Precision/Recall)가 아니다.
