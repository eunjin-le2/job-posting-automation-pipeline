# 📊 데이터 분석가 채용공고 자동화 파이프라인

4개 채용 플랫폼(원티드, 사람인, 잡코리아, 리멤버)에서 데이터 분석가 채용공고를 매일 자동 수집·정제·분류·알림하는 End-to-End 파이프라인입니다.

---

## 주요 기능

- 4개 플랫폼 채용공고 매일 자동 수집 (09:30 crontab)
- 산업군 자동 분류 (10개 산업군)
- 스킬 키워드 자동 추출 (43개)
- 신규 공고 탐지 및 Discord 실시간 알림
- Google Sheets 자동 업데이트

---

## 기술 스택

| 분류 | 기술 |
|------|------|
| 언어 | Python 3.13 |
| 크롤링 | Playwright · BeautifulSoup · requests |
| 데이터 처리 | Pandas |
| 자동화 | n8n · crontab |
| 알림 | Discord Webhook |
| 저장 | Google Sheets · CSV |

---

## 프로젝트 구조
job-posting-automation-pipeline/
```
├── crawlers/

│   ├── wanted.py            # 원티드 JSON API 크롤러

│   ├── saramin.py           # 사람인 PC API 크롤러

│   ├── jobkorea.py          # 잡코리아 Playwright 크롤러

│   ├── remember.py          # 리멤버 POST API 크롤러

│   └── merge.py             # 데이터 정제 파이프라인

├── analysis/

│   ├── 01_crawling_discovery.ipynb   # API 발견 과정

│   └── 02_job_analysis.ipynb         # 채용공고 데이터 분석

├── data/

│   └── active_jobs_06.11.csv         # 수집 데이터 샘플

├── logs/

├── requirements.txt

└── README.md
```
---

## 전체 워크플로우
[수집] 09:30 crontab

원티드 API        → wanted_jobs.csv

사람인 API        → saramin_jobs.csv

잡코리아 Playwright → jobkorea_jobs.csv

리멤버 API        → remember_jobs.csv

↓

[정제] merge.py

① 컬럼 통일 및 BOM 제거

② URL 기준 중복 제거

③ company + title 기준 중복 제거

④ 산업군 자동 분류

⑤ 스킬 키워드 추출 (43개)

⑥ 경력 수치화

⑦ 마감 공고 제거

⑧ 신규 공고 탐지 (전날 URL 비교)

↓

[저장]

all_jobs.csv / active_jobs.csv / new_jobs.csv

↓

[자동화] 10:00 n8n

Google Sheets 업데이트 → Discord 알림

---

## 환경 설정

### 1. 가상환경 생성 및 패키지 설치

```bash
python3.13 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/playwright install chromium
```

### 2. 수동 실행

```bash
.venv/bin/python crawlers/wanted.py
.venv/bin/python crawlers/saramin.py
.venv/bin/python crawlers/jobkorea.py
.venv/bin/python crawlers/remember.py
.venv/bin/python crawlers/merge.py
```

### 3. crontab 설정 (매일 09:30 자동 실행)

```bash
30 9 * * * cd /Users/apple/projects/job-posting-automation-pipeline
&&/Users/apple/projects/job-posting-automation-pipeline/.venv/bin/python crawlers/wanted.py >> logs/cron.log 2>&1
&& /Users/apple/projects/job-posting-automation-pipeline/.venv/bin/python crawlers/saramin.py >> logs/cron.log 2>&1
&& /Users/apple/projects/job-posting-automation-pipeline/.venv/bin/python crawlers/jobkorea.py >> logs/cron.log 2>&1
&& /Users/apple/projects/job-posting-automation-pipeline/.venv/bin/python crawlers/remember.py >> logs/cron.log 2>&1
&& /Users/apple/projects/job-posting-automation-pipeline/.venv/bin/python crawlers/merge.py >> logs/cron.log 2>&1
&& cp /Users/apple/projects/job-posting-automation-pipeline/data/all_jobs.csv /Users/apple/.n8n-files/all_jobs.csv >> logs/cron.log 2>&1
&& cp /Users/apple/projects/job-posting-automation-pipeline/data/new_jobs.csv /Users/apple/.n8n-files/new_jobs.csv >> logs/cron.log 2>&1
&& cp /Users/apple/projects/job-posting-automation-pipeline/data/active_jobs.csv /Users/apple/.n8n-files/active_jobs.csv >> logs/cron.log 2>&1 && echo "$(date) 파일 복사 완료" >> logs/cron.log 2>&1


```

---

## 데이터 수집 현황 (2026.06.12 기준)

| 항목 | 수치 |
|------|------|
| 총 수집 공고 | 430개 |
| 플랫폼 수 | 4개 |
| 산업군 분류 | 10개 |
| 스킬 키워드 | 43개 |
| SQL 요구 비율 | 50.7% |

---

## 주요 트러블슈팅

| 플랫폼 | 문제 | 해결 |
|--------|------|------|
| 원티드 | React SPA로 HTML 스크래핑 불가 | 네트워크 탭 분석으로 내부 JSON API 발견 |
| 사람인 | Playwright 봇 탐지 타임아웃 |  PC API 발견으로 전환 |
| 잡코리아 | UI 요소가 회사명 클래스 공유 | INVALID_COMPANIES 필터링으로 해결 |
| 잡코리아 | 급여 없는 공고에서 파싱 밀림 | 인덱스 기반 → 키워드 기반 파싱 전환 |
| 잡코리아 | 검색 키워드마다 URL 파라미터 달라 중복 발생 | rec_id 추출로 URL 통일 |
| n8n | Clear sheet 420번 반복 실행 → API 초과 | Clear 노드를 Extract from File 앞으로 이동 |
| n8n | NaN 컬럼 미인식 | employment_type · salary 빈값 → 미공개 처리 |
| 공통 | BOM 인코딩으로 컬럼 중복 생성 | utf-8 저장 + clean_columns 함수로 BOM 제거 |

---

## 한계점 및 개선 방향

| 한계점 | 개선 방향 |
|--------|----------|
| 사람인 description 수집 불가 (이미지 렌더링) | OCR로 이미지를 텍스트 데이터로 변환해 description 추출 |
| 로컬 환경 의존 → 절전 모드 시 crontab 미실행 | GCP VM / AWS EC2 클라우드 서버 이전 |
| 키워드 기반 산업군 분류로 오분류 가능 | LLM 기반 분류로 개선 검토 |
| 스킬 추출 표기 방식 다양 → 누락 가능 | NLP 기반 스킬 추출 고도화 |
