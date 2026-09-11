# Data Next

SSAFY 데이터트랙을 위한 데이터·AI·SW·IT 신입 채용 보드입니다. 기업별 상세 공고, 원문 하이퍼링크와 로그인 후 지원 완료 표시를 제공합니다.

## 사이트

https://ssafy-data-career-picks.packageair284828.chatgpt.site

현재 배포는 Sites(Vinext + Cloudflare Workers/D1)를 사용합니다. GitHub Pages는 사용하지 않습니다. 소스 변경은 Sites에서 빌드·버전 저장·배포해야 합니다.

Node.js 22.13 이상에서 `npm ci`, `npm run dev`로 실행하며 `npm run build`, `npm run typecheck`로 검증합니다. `.openai/hosting.json`의 기존 사이트와 D1 바인딩을 유지하세요.

## 자동 공고 수집

GitHub Actions의 `.github/workflows/update-jobs.yml`이 매일 한국 시간 09:17, 18:17에 실행됩니다. 실제 시작은 GitHub 예약 작업의 대기 시간에 따라 늦어질 수 있습니다.

1. 회귀 테스트를 실행하고 공식 API·채용 HTML·JSON-LD·사이트맵·검색 보조 경로에서 후보를 수집합니다.
2. 데이터·AI·SW·IT·전산 연관성과 신입/인턴 근거, 마감 여부를 검사합니다. EUC-KR 페이지의 한글을 복원하고 API 근거를 우선합니다.
3. `automation/curated-jobs.json`의 사용자 제공 일정과 합칩니다. 별도 출처와 검증 상태를 표시하며, 원문 접근 실패만으로 삭제하지 않습니다. `expiresAt` 이후에는 제외합니다. 같은 기업의 서로 다른 직무는 유지합니다.
4. `jobs.json`, `automation/state.json`, `automation/review-queue.json`을 GitHub에 저장하고 원격 데이터가 일치하는지 확인합니다.
5. 사이트는 요청마다 `lib/feed.ts`를 통해 GitHub의 `jobs.json`을 읽습니다. 공고 데이터 갱신에는 Sites 재배포가 필요하지 않습니다. 원격 읽기 실패 시 배포에 포함된 데이터로 대체하며 화면에 상태를 표시합니다.

수동 실행:

```sh
python -m pip install -r automation/requirements.txt
python -m unittest automation.test_update_jobs
python automation/update_jobs.py
```

`FRESH_START=1`은 기존 자동 게시 목록을 무시하고 다시 수집합니다. 사용자 제공 일정은 유지됩니다. 새 기업은 `automation/companies.json`에 기업별 공식 채용 도메인을 등록하세요. 범용 채용 플랫폼 전체보다 해당 기업의 하위 도메인을 사용하세요.

접근 제한·이미지 전용 공고·자바스크립트 전용 목록은 자동 확인이 어려울 수 있습니다. 수집 상태와 검토 대기열에서 실패를 확인할 수 있습니다. 공고 목록 링크는 상세 공고 원문 링크와 구분해서 표시합니다.
