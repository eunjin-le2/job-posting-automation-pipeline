from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
import time
import os
import re

# ── 설정 ──────────────────────────────────────────
BASE_URL = "https://www.jobkorea.co.kr"

SEARCH_KEYWORDS = [
    "데이터분석",
    "데이터 분석가",
    "Business Analyst",
    "SQL 분석",
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

LOCATION_KEYWORDS = [
    "서울", "경기", "부산", "인천", "대구", "광주", "대전",
    "울산", "세종", "강원", "충북", "충남", "전북", "전남",
    "경북", "경남", "제주"
]

# ── 함수 ──────────────────────────────────────────
def normalize_deadline(deadline):
    """마감일 형식 통일 → YYYY-MM-DD"""
    if not deadline:
        return "상시채용"
    deadline = str(deadline).strip()

    if deadline in ["상시채용", "채용시", "상시", ""]:
        return "상시채용"

    today = datetime.now()

    # ~6/5(금) 형식 (잡코리아)
    match = re.search(r'~(\d+)/(\d+)', deadline)
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

def parse_detail_page(page, url):
    """상세 페이지에서 정보 추출"""
    try:
        page.goto(url, timeout=15000, wait_until="domcontentloaded")

        try:
            page.wait_for_selector("iframe[title='상세 모집 요강']", timeout=5000)
        except:
            pass

        employment_type = ""
        salary          = ""
        location        = ""
        deadline        = ""
        experience      = ""

        try:
            spans = page.locator('span.whitespace-pre-wrap').all()
            values = []
            for span in spans:
                text = span.text_content(timeout=2000).strip()
                if text:
                    values.append(text)

            # employment_type은 항상 index 1
            employment_type = values[1] if len(values) > 1 else ""

            # 나머지는 키워드 기반 파싱
            for v in values[2:]:
                if not experience and any(k in v for k in ["신입", "경력"]):
                    nums = re.findall(r'\d+', v)
                    if nums:
                        experience = nums[0]
                    elif "신입" in v:
                        experience = "0"
                elif not location and any(k in v for k in LOCATION_KEYWORDS):
                    location = v
                elif not salary and any(k in v for k in ["만원", "연봉", "내규", "협의", "면접 후"]):
                    salary = v
                elif not deadline and "~" in v:
                    deadline = normalize_deadline(v)
                elif not deadline and v in ["상시채용", "채용시", "상시"]:
                    deadline = "상시채용"

        except:
            pass

        # ── iframe 본문 파싱 (직접 접근) ──
        description = ""
        skills = ""
        try:
            gno = url.split('/Recruit/GI_Read/')[1].split('?')[0]
            iframe_url = f"{BASE_URL}/Recruit/GI_Read_Comt_Ifrm?Gno={gno}"
            page.goto(iframe_url, timeout=10000, wait_until="domcontentloaded")
            page.wait_for_timeout(1000)
            description = page.locator("body").inner_text(timeout=5000)
            skills = extract_skills(description)
        except:
            pass

        return {
            "employment_type": employment_type,
            "salary":          salary,
            "location":        location,
            "experience":      experience,
            "deadline":        deadline,
            "description":     description[:2000],
            "skills":          skills,
        }

    except Exception as e:
        print(f"[오류] 상세 파싱 실패: {e}")
        return {
            "employment_type": "",
            "salary":          "",
            "location":        "",
            "experience":      "",
            "deadline":        "상시채용",
            "description":     "",
            "skills":          "",
        }

def parse_jobs_from_page(page, keyword):
    """목록 페이지에서 공고 링크 수집"""
    jobs = []
    seen = set()

    title_links = page.locator('a[href*="/Recruit/GI_Read/"]').all()
    company_spans = page.locator('span.text-typo-b2-16').all()

    INVALID_COMPANIES = ["연관검색어", "전문채용관", "파워링크", "최근 검색어", "Skip to main content"]
    
    companies = []
    for span in company_spans:
        try:
            text = span.text_content(timeout=2000).strip()
            if text and text not in INVALID_COMPANIES:
                companies.append(text)
        except:
            pass

    valid_links = []
    for link in title_links:
        try:
            text = link.text_content(timeout=2000).strip()
            href = link.get_attribute('href') or ''
            rec_id = href.split('/Recruit/GI_Read/')[1].split('?')[0] if '/Recruit/GI_Read/' in href else ''
            if text and rec_id and rec_id not in seen:
                seen.add(rec_id)
                valid_links.append((text, href, rec_id))
        except:
            pass

    for i, (text, href, rec_id) in enumerate(valid_links):
        company_idx = i + 1 if len(companies) > len(valid_links) else i
        company = companies[company_idx] if company_idx < len(companies) else ""
        full_url = f"https://www.jobkorea.co.kr/Recruit/GI_Read/{rec_id}"
        jobs.append({
            "title":   text,
            "company": company,
            "url":     full_url,
            "keyword": keyword,
        })

    return jobs

def crawl_keyword(page, keyword, max_pages=3):
    """키워드별 크롤링"""
    all_jobs = []

    for page_num in range(1, max_pages + 1):
        search_url = (
            f"{BASE_URL}/Search/?stext={keyword}&tabType=recruit&Page_No={page_num}"
        )
        try:
            page.goto(search_url, timeout=15000, wait_until="domcontentloaded")
            page.wait_for_timeout(2000)
        except Exception as e:
            print(f"[오류] 페이지 로딩 실패: {e}")
            break

        jobs = parse_jobs_from_page(page, keyword)
        if not jobs:
            print(f"  → {page_num}페이지 공고 없음, 종료")
            break

        print(f"  → {page_num}페이지 {len(jobs)}개 수집")
        all_jobs.extend(jobs)
        time.sleep(1)

    return all_jobs

def crawl_jobkorea(max_pages=3):
    all_jobs   = []
    final_jobs = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page    = browser.new_page()

        print("=== 1단계: 목록 수집 ===")
        for keyword in SEARCH_KEYWORDS:
            print(f"\n[수집 중] '{keyword}' ...")
            jobs = crawl_keyword(page, keyword, max_pages)
            all_jobs.extend(jobs)
            print(f"  누적: {len(all_jobs)}개")

        seen        = set()
        unique_jobs = []
        for job in all_jobs:
            if job["url"] not in seen:
                seen.add(job["url"])
                unique_jobs.append(job)
        print(f"\n중복 제거: {len(all_jobs)}개 → {len(unique_jobs)}개")

        print("\n=== 2단계: 상세 페이지 수집 ===")
        for i, job in enumerate(unique_jobs):
            title = job["title"]

            if is_excluded(title):
                print(f"  → 제외: {title[:30]}")
                continue

            detail_url = job["url"]
            print(f"  [{i+1}/{len(unique_jobs)}] {job['company']} — {title[:30]}")
            detail = parse_detail_page(page, detail_url)

            final_jobs.append({
                "source":           "잡코리아",
                "keyword":          job["keyword"],
                "title":            title,
                "company":          job["company"],
                "industry":         "",
                "location":         detail["location"],
                "employment_type":  detail["employment_type"],
                "experience":       detail["experience"],
                "skills":           detail["skills"],
                "salary":           detail["salary"],
                "deadline":         detail["deadline"],
                "url":              detail_url,
                "crawled_at":       datetime.now().strftime("%Y-%m-%d %H:%M"),
                "description":      detail["description"],
            })

        browser.close()

    df = pd.DataFrame(final_jobs)
    os.makedirs("data", exist_ok=True)
    df.to_csv("data/jobkorea_jobs.csv", index=False, encoding="utf-8")
    print(f"\n완료! 총 {len(df)}개 → data/jobkorea_jobs.csv")
    return df

# ── 실행 ──────────────────────────────────────────
if __name__ == "__main__":
    crawl_jobkorea(max_pages=3)