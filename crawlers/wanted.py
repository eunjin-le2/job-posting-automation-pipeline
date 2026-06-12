import requests
import pandas as pd
from datetime import datetime
import time
import os

# ── 설정 ──────────────────────────────────────────
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.wanted.co.kr/",
    "Accept": "application/json, text/plain, */*",
}

JOB_CODES = [
    {"tag_type_id": 656, "label": "데이터분석가"},
]

SKILL_KEYWORDS = [
    "SQL", "MySQL", "BigQuery", "Snowflake", "PostgreSQL",
    "데이터 마트", "데이터마트", "ETL", "데이터 정제", "데이터 전처리", "전처리",
    "Tableau", "Power BI", "Looker Studio", "Looker", "Redash",
    "Google Analytics", "GA4",
    "A/B", "A/B Test", "가설 검정", "가설검정", "p-value",
    "유의성 검정", "실험 설계", "통계",
    "KPI", "North Star Metric", "Funnel", "퍼널",
    "Retention", "리텐션", "Cohort", "코호트",
    "Conversion Rate", "전환율", "Churn Rate", "이탈률",
    "LTV", "CAC", "ROAS",
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
def fetch_job_list(tag_type_id, offset=0, limit=20):
    """공고 목록 가져오기"""
    url = "https://www.wanted.co.kr/api/v4/jobs"
    params = {
        "country":      "kr",
        "job_sort":     "job.latest_order",
        "locations":    "all",
        "years":        -1,
        "tag_type_ids": tag_type_id,
        "limit":        limit,
        "offset":       offset,
    }
    try:
        res = requests.get(url, headers=HEADERS, params=params, timeout=10)
        res.raise_for_status()
        data     = res.json()
        has_next = data.get("links", {}).get("next") is not None
        return data.get("data", []), has_next
    except Exception as e:
        print(f"[오류] 목록 가져오기 실패: {e}")
        return [], False

def fetch_job_detail(job_id):
    url = f"https://www.wanted.co.kr/api/chaos/jobs/v4/{job_id}/details"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        res.raise_for_status()
        return res.json().get("data", {}).get("job", {})
    except Exception as e:
        print(f"[오류] 상세 가져오기 실패 (job_id={job_id}): {e}")
        return {}
    
def extract_skills(detail):
    """스킬 추출 - skill_tags 없으면 requirements에서 키워드 찾기"""
    skill_tags = detail.get("skill_tags", [])
    if skill_tags:
        return ", ".join([s.get("title", "") for s in skill_tags])
    requirements = detail.get("detail", {}).get("requirements", "")
    found = [k for k in SKILL_KEYWORDS if k.lower() in requirements.lower()]
    return ", ".join(found)

def extract_experience(detail):
    """경력 추출 - 숫자로 정규화"""
    annual_from = detail.get("annual_from", None)
    annual_to   = detail.get("annual_to", None)
    if annual_to is not None and annual_to >= 20:
        annual_to = None
    if annual_from == 0:
        return "0"
    elif annual_from is not None:
        return str(annual_from)
    return ""

def is_excluded(title):
    """제외 키워드 포함 여부 확인"""
    return any(kw.lower() in title.lower() for kw in EXCLUDE_KEYWORDS)

def parse_job(item, label):
    """공고 하나 파싱"""
    detail      = fetch_job_detail(item.get("id"))
    time.sleep(0.5)
    title       = item.get("position", "")
    detail_data = detail.get("detail", {})
    description = " ".join(filter(None, [
        detail_data.get("main_tasks", ""),
        detail_data.get("requirements", ""),
        detail_data.get("preferred_points", ""),
    ]))

    # location - 시/도 + 구 합치기
    address = detail.get("address", {}) or item.get("address", {})
    location = address.get("location", "")
    district = address.get("district", "")

    # employment_type 매핑 추가
    employment_type_map = {
        "regular": "정규직",
        "contract": "계약직",
        "intern": "인턴",
        "freelance": "프리랜서",
    }
    emp = detail.get("employment_type", "") or ""

    return {
        "source":           "원티드",
        "job_label":        label,
        "title":            title,
        "company":          item.get("company", {}).get("name", ""),
        "industry":         detail.get("company", {}).get("industry_name", ""),
        "location":         f"{location} {district}".strip() if district else location,
        "skills":           extract_skills(detail),
        "experience":       extract_experience(detail),
        "employment_type":  employment_type_map.get(emp, "미공개"),
        "salary":           "",
        "deadline":         item.get("due_time") or "상시채용",
        "url":              f"https://www.wanted.co.kr/wd/{item.get('id')}",
        "crawled_at":       datetime.now().strftime("%Y-%m-%d %H:%M"),
        "description":      description,
    }

def crawl_wanted(max_per_category=500):
    """전체 크롤링 실행"""
    all_jobs = []

    for code in JOB_CODES:
        print(f"\n[수집 중] {code['label']} ...")
        offset    = 0
        limit     = 20
        collected = 0

        while collected < max_per_category:
            items, has_next = fetch_job_list(
                code["tag_type_id"],
                offset=offset, limit=limit
            )
            if not items:
                break

            print(f"  offset={offset} → {len(items)}개")

            for item in items:
                job   = parse_job(item, code["label"])
                title = job["title"]

                if is_excluded(title):
                    print(f"    → 제외: {title}")
                    continue

                all_jobs.append(job)
                print(f"    ✓ {job['company']} — {title}")

            offset    += limit
            collected += len(items)
            time.sleep(1)

            if not has_next:
                print(f"  → 마지막 페이지 도달")
                break

    df = pd.DataFrame(all_jobs)

    before = len(df)
    df = df.drop_duplicates(subset=["url"], keep="first")
    print(f"\n중복 제거: {before}개 → {len(df)}개")

    os.makedirs("data", exist_ok=True)
    df.to_csv("data/wanted_jobs.csv", index=False, encoding="utf-8")
    print(f"완료! 총 {len(df)}개 → data/wanted_jobs.csv")
    return df

# ── 실행 ──────────────────────────────────────────
if __name__ == "__main__":
    crawl_wanted()