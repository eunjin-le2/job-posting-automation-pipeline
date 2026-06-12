import requests
import pandas as pd
from datetime import datetime, timedelta
import time
import os
from bs4 import BeautifulSoup
import re

# ── 설정 ──────────────────────────────────────────
BASE_URL = "https://www.saramin.co.kr"
API_URL  = "https://www.saramin.co.kr/zf_user/search/get-recruit-list"

SEARCH_KEYWORDS = [
    "데이터분석",
    "데이터 분석가",
    "SQL 분석",
    "Business Analyst",
]

SKILL_KEYWORDS = [
    "SQL", "MySQL", "BigQuery", "Snowflake", "PostgreSQL",
    "데이터 마트", "데이터마트", "ETL", "데이터 정제", "전처리",
    "Tableau", "Power BI", "Looker Studio", "Looker", "Redash",
    "Google Analytics", "GA4", "Adobe Analytics",
    "A/B", "가설 검정", "가설검정", "p-value", "유의성 검정", "통계",
    "KPI", "Funnel", "퍼널", "Retention", "리텐션",
    "Cohort", "코호트", "전환율", "이탈률", "LTV", "ROAS",
    "Python", "Pandas", "NumPy", "scikit-learn", "Jupyter",
    "Amplitude", "Mixpanel", "Databricks",
]

EXCLUDE_KEYWORDS = [
    # 개발직군
    "백엔드", "back-end", "backend", "서버 개발", "서버개발",
    "Spring", "Node.js", "Django", "FastAPI", "Flask",
    "프론트엔드", "front-end", "frontend",
    "React", "Vue", "Angular",
    "iOS", "Android", "Flutter", "Swift", "Kotlin",
    "DevOps", "인프라", "SRE", "Kubernetes", "Docker",
    "풀스택", "Full-stack", "Fullstack",
    "Software Engineer", "소프트웨어 엔지니어",
    # AI/ML 엔지니어 (분석가 아님)
    "ML Engineer", "Machine Learning Engineer",
    "딥러닝 엔지니어", "Perception Engineer",
    # 마케팅/디자인
    "Designer", "디자이너",
    # 영업/생산직
    "영업사원", "영업직", "영업담당",
    "생산직", "품질관리", "재무회계", "세무",
]

DATA_TITLE_KEYWORDS = [
    "데이터 분석", "데이터분석", "data analyst", "business analyst",
    "데이터 사이언티스트", "data scientist",
    "growth analyst", "product analyst",
    "분석가", "애널리스트", "analyst",
    "DA ", "DA|", "BI "
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.saramin.co.kr/",
}

# ── 함수 ──────────────────────────────────────────
def normalize_deadline(deadline):
    """마감일 형식 통일 → YYYY-MM-DD"""
    if not deadline:
        return "상시채용"
    deadline = str(deadline).strip()

    if deadline in ["상시채용", "채용시", "상시", ""]:
        return "상시채용"

    today = datetime.now()

    # 오늘마감
    if "오늘" in deadline:
        return today.strftime("%Y-%m-%d")

    # 내일마감
    if "내일" in deadline:
        return (today + timedelta(days=1)).strftime("%Y-%m-%d")

    # D-2 형식
    d_match = re.search(r'D-(\d+)', deadline)
    if d_match:
        days = int(d_match.group(1))
        return (today + timedelta(days=days)).strftime("%Y-%m-%d")

    # ~06.12(금) 형식 (사람인)
    match = re.search(r'~(\d+)\.(\d+)', deadline)
    if match:
        month = int(match.group(1))
        day = int(match.group(2))
        year = today.year
        if month < today.month:
            year += 1
        return f"{year}-{month:02d}-{day:02d}"

    # ~ 06/14(일) 형식 (사람인 PC API)
    match = re.search(r'~\s*(\d+)/(\d+)', deadline)
    if match:
        month = int(match.group(1))
        day = int(match.group(2))
        year = today.year
        if month < today.month:
            year += 1
        return f"{year}-{month:02d}-{day:02d}"

    return deadline

def extract_skills(text):
    found = [k for k in SKILL_KEYWORDS if k.lower() in text.lower()]
    return ", ".join(found)

def is_excluded(title):
    return any(kw.lower() in title.lower() for kw in EXCLUDE_KEYWORDS)

def is_data_related(title):
    return any(kw.lower() in title.lower() for kw in DATA_TITLE_KEYWORDS)

def fetch_page(keyword, page=1):
    params = {
        "searchword":      keyword,
        "searchType":      "search",
        "recruitPage":     page,
        "recruitPageCount": 20,
    }
    try:
        res = requests.get(API_URL, headers=HEADERS, params=params, timeout=10)
        res.raise_for_status()
        data = res.json()
        return data.get("innerHTML", ""), int(data.get("count", "0").replace(",", ""))
    except Exception as e:
        print(f"[오류] 페이지 가져오기 실패 (keyword={keyword}, page={page}): {e}")
        return "", 0

def parse_jobs(html, keyword):
    soup    = BeautifulSoup(html, "html.parser")
    jobs    = soup.find_all("div", class_="item_recruit")
    results = []

    for job in jobs:
        try:
            # 제목
            tit = job.find("h2", class_="job_tit")
            if not tit:
                continue
            a_tag = tit.find("a")
            if not a_tag:
                continue
            title = a_tag.get("title", "").strip()
            if not title:
                title = a_tag.get_text(strip=True)

            if is_excluded(title):
                continue
            if not is_data_related(title):
                continue

            # 회사명
            corp = job.find("strong", class_="corp_name")
            company = corp.get_text(strip=True) if corp else ""

            # rec_idx & URL
            rec_idx = job.get("value", "")
            job_url = f"{BASE_URL}/zf_user/jobs/relay/view?rec_idx={rec_idx}" if rec_idx else ""

            # job_condition에서 location, experience, employment_type 파싱
            location        = ""
            experience      = ""
            employment_type = ""

            condition = job.find("div", class_="job_condition")
            if condition:
                spans = condition.find_all("span")
                for span in spans:
                    text = span.get_text(strip=True)
                    # location - a 태그 있는 span
                    if span.find("a") and not location:
                        location = " ".join([a.get_text(strip=True) for a in span.find_all("a")])
                    # experience
                    elif any(k in text for k in ["신입", "경력", "무관"]):
                        experience = text
                    # employment_type
                    elif any(k in text for k in ["정규직", "계약직", "인턴", "프리랜서", "파견직"]):
                        employment_type = text

            # deadline
            date_span = job.find("span", class_="date")
            deadline = normalize_deadline(date_span.get_text(strip=True) if date_span else "상시채용")

            # skills
            skills = extract_skills(title)

            results.append({
                "source":          "사람인",
                "keyword":         keyword,
                "title":           title,
                "company":         company,
                "industry":        "",
                "location":        location,
                "experience":      experience,
                "employment_type": employment_type,
                "skills":          skills,
                "salary":          "",
                "deadline":        deadline,
                "url":             job_url,
                "crawled_at":      datetime.now().strftime("%Y-%m-%d %H:%M"),
                "description":     "",
            })

        except Exception as e:
            print(f"[오류] 공고 파싱 실패: {e}")
            continue

    return results

def crawl_saramin(max_pages=5):
    all_jobs = []

    for keyword in SEARCH_KEYWORDS:
        print(f"\n[수집 중] '{keyword}' ...")
        for page in range(1, max_pages + 1):
            html, total = fetch_page(keyword, page)
            if not html:
                break
            jobs = parse_jobs(html, keyword)
            if not jobs:
                print(f"  → {page}페이지 공고 없음, 종료")
                break
            all_jobs.extend(jobs)
            print(f"  → {page}페이지 {len(jobs)}개 수집 (누적: {len(all_jobs)}개)")
            time.sleep(1)

    seen        = set()
    unique_jobs = []
    for job in all_jobs:
        if job["url"] not in seen:
            seen.add(job["url"])
            unique_jobs.append(job)
    print(f"\n중복 제거: {len(all_jobs)}개 → {len(unique_jobs)}개")

    df = pd.DataFrame(unique_jobs)
    os.makedirs("data", exist_ok=True)
    df.to_csv("data/saramin_jobs.csv", index=False, encoding="utf-8")
    print(f"완료! 총 {len(df)}개 → data/saramin_jobs.csv")
    return df

# ── 실행 ──────────────────────────────────────────
if __name__ == "__main__":
    crawl_saramin(max_pages=5)