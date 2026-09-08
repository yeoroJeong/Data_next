# Data Next

SSAFY 데이터반을 위한 데이터·AI·SW 신입 채용 공고 보드입니다. 83개 대기업·주요 테크 기업의 공식 채용 페이지를 대상으로 합니다.

## 로컬 실행

Node.js 20 이상이 필요합니다.

```bash
npm install
npm run dev
```

브라우저에서 `http://localhost:3000`을 열면 됩니다. 정적 배포용 빌드는 `npm run build`로 생성하며 결과물은 `out/`에 저장됩니다.

## 채용 데이터 자동화

GitHub Actions가 매일 한국 시간 오전 9시 17분과 오후 6시 17분에 `automation/update_jobs.py`를 실행합니다.

자동화는 기존 게시 공고의 원문을 다시 열어 마감·기간 변경을 확인합니다. 새 공고는 공식 채용 API(NAVER·카카오), 공식 채용 홈, JSON-LD, 사이트맵, 검색 보조 경로를 합쳐 찾습니다. 그런 다음 공식 도메인·핵심 데이터 역량·신입/인턴 근거·마감 상태를 모두 확인한 경우만 게시합니다. 원문에 일시적으로 접근할 수 없으면 기존 공고를 즉시 삭제하지 않고 `automation/review-queue.json`에 기록합니다.

수동 실행:

```bash
python -m pip install -r automation/requirements.txt
python automation/update_jobs.py
```

기존 게시 목록을 무시하고 전체를 새로 구성하려면 `FRESH_START=1`을 환경 변수로 설정합니다.

## 배포

`main` 브랜치에 push하면 `.github/workflows/deploy-pages.yml`이 Next.js 정적 사이트를 빌드하고 GitHub Pages에 배포합니다. 저장소의 **Settings → Pages → Build and deployment → Source**를 **GitHub Actions**로 한 번 선택해야 합니다.

배포 후 기본 주소는 `https://yeorojeong.github.io/Data_next/`입니다.
