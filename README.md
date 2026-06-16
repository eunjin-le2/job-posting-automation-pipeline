# 📊 데이터 분석가 채용공고 자동화 파이프라인

## 시연 영상
[![시연영상](https://img.youtube.com/vi/4VhyUd81Ueg/0.jpg)](https://youtu.be/4VhyUd81Ueg)

## 🎯 프로젝트 배경

데이터 분석 직무로 이직을 준비하며 채용공고를 수집하던 중,
플랫폼별로 공고가 분산되어 있고 반복적으로 확인해야 하는 불편함이 있었습니다.

이를 해결하기 위해 여러 채용 플랫폼의 공고를 자동 수집하고,
신규 공고를 실시간으로 확인할 수 있는 자동화 파이프라인을 구축했습니다.

또한 수집된 데이터를 활용하여 산업군별 채용시장과 요구 역량을 분석했습니다.

---

## 기술 스택

![Python](https://img.shields.io/badge/Python-3.13-3776AB?style=flat&logo=python&logoColor=white)
![Playwright](https://img.shields.io/badge/Playwright-45ba4b?style=flat&logo=playwright&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-150458?style=flat&logo=pandas&logoColor=white)
![n8n](https://img.shields.io/badge/n8n-EA4B71?style=flat&logo=n8n&logoColor=white)
![Google Sheets](https://img.shields.io/badge/Google_Sheets-34A853?style=flat&logo=googlesheets&logoColor=white)
![Discord](https://img.shields.io/badge/Discord-5865F2?style=flat&logo=discord&logoColor=white)

---

## 프로젝트 구조
```
job-posting-automation-pipeline/
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

## 파이프라인 구조

| 단계 | 내용 | 결과 |
|------|------|------|
| 🔍 **수집** (09:30 crontab) | 원티드 API · 사람인 API · 잡코리아 Playwright · 리멤버 API | 플랫폼별 CSV 저장 |
| 🔧 **정제** (merge.py) | 컬럼 통일 → 중복 제거 → 산업군 분류 (10개) → 스킬 추출 (43개) → 경력 수치화 → 마감 공고 제거 → 신규 공고 탐지 | all_jobs.csv · active_jobs.csv · new_jobs.csv |
| 🤖 **자동화** (10:00 n8n) | Google Sheets 전체 갱신 → Discord 신규 공고 알림 | 실시간 모니터링 |

## 🏗️ 아키텍처

```text
Wanted API
Saramin API
JobKorea Playwright
Remember API
        │
        ▼
    Crawlers
        │
        ▼
     merge.py
        │
        ▼
 ┌─────────────┐
 │ active_jobs │
 │  new_jobs   │
 │  all_jobs   │
 └─────────────┘
        │
        ▼
       n8n
    ┌───────┐
    ▼       ▼
Google   Discord
Sheets   Alert

```
데이터 분석 관련 채용공고를 4개 플랫폼에서 수집하고,
정제 파이프라인을 거쳐 Google Sheets와 Discord로 자동 배포하는 구조로 설계했습니다.

## n8n 워크플로우

<img width="1283" height="331" alt="image" src="https://github.com/user-attachments/assets/9fe9f576-919e-439c-8dbe-26013a3e96ae" />

### 상단 플로우 (전체 공고 관리)

1. active_jobs.csv 파일을 읽어온다.
2. 기존 Google Sheets 데이터를 초기화한다.
3. 최신 채용공고 데이터를 시트에 일괄 업로드한다.
4. 필터 및 대시보드에서 활용할 수 있도록 데이터 상태를 최신으로 유지한다.

### 하단 플로우 (신규 공고 알림)

1. new_jobs.csv 파일을 읽어온다.
2. 신규 공고가 존재하는 경우에만 후속 작업을 수행한다.
3. JavaScript Code 노드에서 Discord 메시지 형식으로 가공한다.
4. Discord Webhook을 통해 신규 채용공고를 실시간 전송한다

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
30 9 * * * cd /path/to/job-posting-automation-pipeline && \
.venv/bin/python crawlers/wanted.py >> logs/cron.log 2>&1 && \
.venv/bin/python crawlers/saramin.py >> logs/cron.log 2>&1 && \
.venv/bin/python crawlers/jobkorea.py >> logs/cron.log 2>&1 && \
.venv/bin/python crawlers/remember.py >> logs/cron.log 2>&1 && \
.venv/bin/python crawlers/merge.py >> logs/cron.log 2>&1 && \
cp data/all_jobs.csv ~/.n8n-files/all_jobs.csv >> logs/cron.log 2>&1 && \
cp data/new_jobs.csv ~/.n8n-files/new_jobs.csv >> logs/cron.log 2>&1 && \
cp data/active_jobs.csv ~/.n8n-files/active_jobs.csv >> logs/cron.log 2>&1 && \
echo "$(date) 파일 복사 완료" >> logs/cron.log 2>&1
```

> n8n은 `~/.n8n-files/` 경로에서 파일을 읽습니다. 크롤링 완료 후 자동으로 복사됩니다.
---

## 데이터 수집 현황 (2026.06.12 기준)

| 총 공고 | 플랫폼 | 산업군 | 스킬 키워드 | SQL 요구 비율 |
|--------|--------|--------|------------|-------------|
| 430개 | 4개 | 8개 | 43개 | 50.7% |

## 📈 주요 분석 결과

430건의 데이터 분석 채용공고를 분석한 결과 다음과 같은 특징을 확인하였습니다.

- SQL은 전체 공고의 50.7%에서 요구되는 핵심 역량으로 나타남
- Python, Tableau 등 데이터 분석 및 시각화 역량 수요가 높게 확인됨
- 이커머스·유통 산업군의 채용 비중이 가장 높게 나타남
- 금융·보험 산업군은 KPI 관리, 전략 수립, 고객 분석 중심의 비즈니스 분석 역할 비중이 높음
- 이커머스·유통 산업군은 고객 행동 분석 및 Product Analytics 역량 수요가 높음
- IT·플랫폼·SaaS 산업군은 데이터 파이프라인, 클라우드, AI 활용 역량 비중이 높음
- 
---

## 주요 트러블슈팅

| 플랫폼 | 문제 | 해결 |
|--------|------|------|
| 원티드 | React SPA로 HTML 스크래핑 불가 | 네트워크 탭 분석으로 내부 JSON API 발견 |
| 사람인 | Playwright 봇 탐지 타임아웃 |  PC API 발견으로 전환 |
| 잡코리아 | UI 요소가 회사명 클래스 공유 | 카드 단위 파싱으로 전환 |
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

