import requests
import pandas as pd
from datetime import datetime
import time
import os

# ── 설정 ──────────────────────────────────────────
HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://career.rememberapp.co.kr",
    "Referer": "https://career.rememberapp.co.kr/",
    "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Mobile Safari/537.36",
}

API_URL = "https://career-api.rememberapp.co.kr/job_postings/search"

SEARCH_KEYWORDS = [
    "데이터분석",
    "데이터 분석가",
    "SQL",
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
    # 디자인
    "Designer", "디자이너",
    # 영업/생산직
    "영업사원", "영업직", "영업담당",
    "생산직", "품질관리", "재무회계", "세무",
]

# ── 함수 ──────────────────────────────────────────
def extract_skills(text):
    found = [k for k in SKILL_KEYWORDS if k.lower() in text.lower()]
    return ", ".join(found)

def is_excluded(title):
    return any(kw.lower() in title.lower() for kw in EXCLUDE_KEYWORDS)

def extract_experience(min_exp, max_exp):
    if min_exp is None and max_exp is None:
        return ""
    elif min_exp == 0:
        return "신입"
    elif min_exp is not None and max_exp is not None:
        return f"{min_exp}~{max_exp}년"
    elif min_exp is not None:
        return f"{min_exp}년 이상"
    return ""

def fetch_jobs(keyword, page=1, per=30):
    body = {
        "ai_new_model": False,
        "meta": {"device_uid": "d284c013-31a5-4c85-aee7-96133d8c9efd"},
        "new_function_score": True,
        "page": page,
        "per": per,
        "search": {
            "include_applied_job_posting": False,
            "leader_position": False,
            "organization_type": "all",
            "application_type": "all",
            "keywords": [keyword]
        },
        "seed": 82989910,
        "sort": "starts_at_desc"
    }
    try:
        res = requests.post(API_URL, headers=HEADERS, json=body, timeout=10)
        res.raise_for_status()
        data = res.json()
        return data.get("data", []), data.get("meta", {})
    except Exception as e:
        print(f"[오류] 가져오기 실패 (keyword={keyword}, page={page}): {e}")
        return [], {}

def parse_job(item, keyword):
    # 회사명
    company = item.get("organization", {}).get("name", "")

    # 산업군
    industries = item.get("industries", [])
    industry = ", ".join([i.get("name", "") for i in industries]) if industries else ""

    # 위치
    addresses = item.get("addresses", [])
    location = ""
    if addresses:
        addr = addresses[0]
        location = f"{addr.get('address_level1', '')} {addr.get('address_level2', '')}".strip()

    # 경력
    experience = extract_experience(
        item.get("min_experience"),
        item.get("max_experience")
    )

    # 마감일
    ends_at = item.get("ends_at")
    deadline = ends_at[:10] if ends_at else "상시채용"

    # 연봉
    min_sal = item.get("min_salary")
    max_sal = item.get("max_salary")
    salary = ""
    if min_sal and max_sal:
        salary = f"{min_sal}~{max_sal}만원"
    elif min_sal:
        salary = f"{min_sal}만원 이상"

    # description 합치기 (스킬 추출용)
    description = " ".join(filter(None, [
        item.get("job_description", ""),
        item.get("qualifications", ""),
        item.get("preferred_qualifications", ""),
    ]))

    # 직무 카테고리
    job_categories = item.get("job_categories", [])
    job_label = ""
    if job_categories:
        job_label = job_categories[0].get("level2", "") or job_categories[0].get("level1", "")

    return {
        "source":      "리멤버",
        "keyword":     keyword,
        "job_label":   job_label,
        "title":       item.get("title", ""),
        "company":     company,
        "industry":    industry,
        "location":    location,
        "experience":  experience,
        "skills":      extract_skills(description),
        "salary":      salary,
        "deadline":    deadline,
        "url":         f"https://career.rememberapp.co.kr/job/postings/{item.get('id')}",
        "crawled_at":  datetime.now().strftime("%Y-%m-%d %H:%M"),
        "description": description[:2000],
    }

def crawl_remember(max_pages=5):
    all_jobs = []

    for keyword in SEARCH_KEYWORDS:
        print(f"\n[수집 중] '{keyword}' ...")

        for page in range(1, max_pages + 1):
            items, meta = fetch_jobs(keyword, page=page)

            if not items:
                print(f"  → {page}페이지 공고 없음, 종료")
                break

            print(f"  → {page}페이지 {len(items)}개 발견")

            for item in items:
                title = item.get("title", "")

                if is_excluded(title):
                    continue

                job = parse_job(item, keyword)

                # 스킬 없는 공고 제외
                if not job["skills"]:
                    continue

                all_jobs.append(job)

            time.sleep(0.5)

    df = pd.DataFrame(all_jobs)

    # url 기준 중복 제거
    before = len(df)
    df = df.drop_duplicates(subset=["url"], keep="first")
    print(f"\n중복 제거: {before}개 → {len(df)}개")

    os.makedirs("data", exist_ok=True)
    df.to_csv("data/remember_jobs.csv", index=False, encoding="utf-8")
    print(f"완료! 총 {len(df)}개 → data/remember_jobs.csv")
    return df

# ── 실행 ──────────────────────────────────────────
if __name__ == "__main__":
    crawl_remember(max_pages=3)
