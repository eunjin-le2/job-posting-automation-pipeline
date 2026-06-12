import pandas as pd
import os
import re
from datetime import datetime
from collections import Counter

# ── 설정 ──────────────────────────────────────────
DATA_DIR = "data"
LOG_DIR  = "logs"

CSV_FILES = {
    "원티드":  f"{DATA_DIR}/wanted_jobs.csv",
    "사람인":  f"{DATA_DIR}/saramin_jobs.csv",
    "잡코리아": f"{DATA_DIR}/jobkorea_jobs.csv",
    "리멤버":  f"{DATA_DIR}/remember_jobs.csv",
}

COLUMNS_ORDER = [
    "source", "company", "title", "industry", "location",
    "experience", "employment_type", "salary", "skills",
    "deadline", "url", "description", "crawled_at",
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

# ── 산업군 분류 ──────────────────────────────────────────
COMPANY_INDUSTRY_MAP = {
    "쿠팡": "이커머스·유통",
    "쿠팡(주)": "이커머스·유통",
    # IT·플랫폼·SaaS
    "우아한형제들(배달의민족)": "IT·플랫폼·SaaS",
    "브레이브모바일(숨고,Soomgo)": "IT·플랫폼·SaaS",
    "(주)브레이브모바일": "IT·플랫폼·SaaS",
    "여기어때컴퍼니": "IT·플랫폼·SaaS",
    "(주)여기어때컴퍼니": "IT·플랫폼·SaaS",
    "채널코퍼레이션": "IT·플랫폼·SaaS",
    "(주)채널코퍼레이션": "IT·플랫폼·SaaS",
    "메가존클라우드(주)": "IT·플랫폼·SaaS",
    "메가존클라우드㈜": "IT·플랫폼·SaaS",
    "(주)포티투닷": "IT·플랫폼·SaaS",
    "(주)리멤버앤컴퍼니": "IT·플랫폼·SaaS",
    "이팝소프트(말해보카)": "IT·플랫폼·SaaS",
    "(주)미리디": "IT·플랫폼·SaaS",
    "(주)딥다이브": "IT·플랫폼·SaaS",
    "(주)올빅뎃": "IT·플랫폼·SaaS",
    "(주)백패커": "IT·플랫폼·SaaS",
    "스위치원": "IT·플랫폼·SaaS",
    # 금융·보험
    "주식회사 빗썸": "금융·보험",
    "(주)빗썸": "금융·보험",
    "빗썸": "금융·보험",
    "토스씨엑스": "금융·보험",
    "블록스퀘어서울": "금융·보험",
    "제이투케이": "금융·보험",
    # 미디어·콘텐츠
    "넷플릭스(Netflix)": "미디어·콘텐츠",
    "(주)이노션": "미디어·콘텐츠",
    "㈜이노션": "미디어·콘텐츠",
    # 헬스케어·바이오
    "(주)메디트": "헬스케어·바이오",
}

HEADHUNTER_KEYWORDS = [
    "써치", "서치", "헤드헌팅", "헤드헌터", "스카우트",
    "맨파워", "유니코", "에버브레인", "리앤파트너",
    "인재채용", "채용대행", "컨설팅", "파트너스",
    "아데코", "리레코", "포커스", "커리어커넥트",
    "글로벌서치", "제이앤피", "파워에이치알",
]

INDUSTRY_KEYWORDS = {
    "헬스케어·바이오": [
        "병원", "의료", "헬스케어",
        "제약", "바이오", "임상",
        "ngs", "genomics", "생물정보",
        "세포", "전사체",
        "방사선",
        "한의", "한방",
        "의원", "클리닉", "clinic",
        "pharmaceutical", "medical",
    ],
    "금융·보험": [
        "보험", "생명", "손해보험", "insurance",
        "은행", "증권", "카드",
        "캐피탈", "자산운용",
        "핀테크", "결제", "송금",
        "투자은행", "투자증권", "신용평가",
        "가상자산", "암호화폐", "블록체인",
        "fintech", "공시",
        "뱅크",
        "저축은행", "대출", "여신",
        "카카오페이", "네이버페이", "토스페이",
    ],
    "이커머스·유통": [
        "커머스", "쇼핑",
        "유통", "물류",
        "배송", "리테일",
        "마켓", "주문",
        "자사몰", "온라인몰",
        "리만", "도미노", "쿠팡",
    ],
    "미디어·콘텐츠": [
        "콘텐츠", "방송", "게임",
        "엔터테인먼트", "웹툰",
        "광고", "미디어",
        "마케팅", "크리에이티브",
    ],
    "교육": [
        "교육", "에듀", "학습",
        "강의", "학원",
        "대학교", "산학협력",
        "진학", "입시", "e-learning",
        "온라인교육", "원격교육",
        "코딩교육", "코딩학원",
    ],
    "제조·모빌리티": [
        "자동차", "모빌리티", "반도체",
        "전자", "제조", "생산",
        "공장", "배터리", "로봇",
        "소재", "화학", "에너지",
        "드론", "항공", "방산",
        "ess", "충전",
    ],
    "공공기관": [
        "공공", "정부", "국립",
        "공사", "공단", "협회",
        "국방", "위원회", "재단",
        "지자체", "공기업",
        "공공기관", "공공부문",
        "한국전자통신연구원", "국가연구", "정부출연"
    ],
    "IT·플랫폼·SaaS": [
        "플랫폼", "소프트웨어", "SaaS",
        "클라우드", "AI", "인공지능",
        "API", "IT서비스", "데이터플랫폼",
        "솔루션", "시스템", "테크",
        "리서치", "시장조사", "닐슨",
        "스타트업", "날씨", "웨더", "weather",
    ],
}

WANTED_MAPPING = {
    "금융": "금융·보험",
    "보험": "금융·보험",
    "교육": "교육",
    "의료": "헬스케어·바이오",
    "미디어": "미디어·콘텐츠",
    "게임": "미디어·콘텐츠",
    "유통": "이커머스·유통",
    "제조": "제조·모빌리티",
    "IT": "IT·플랫폼·SaaS",
}

def clean_columns(df):
    """BOM 제거 + 중복 컬럼 제거 + 컬럼 정렬"""
    df = df.copy()
    df.columns = df.columns.astype(str).str.replace("\ufeff", "", regex=False).str.strip()
    df = df.loc[:, ~df.columns.duplicated()]
    for col in COLUMNS_ORDER:
        if col not in df.columns:
            df[col] = ""
    df = df.fillna("")
    # employment_type, salary 빈값 미공개로 채우기
    df["employment_type"] = df["employment_type"].replace("", "미공개")
    df["salary"] = df["salary"].replace("", "미공개")
    return df[COLUMNS_ORDER]

def classify_industry(row):
    company       = str(row.get("company", ""))
    title         = str(row.get("title", ""))
    description   = str(row.get("description", ""))
    orig_industry = str(row.get("industry", ""))

    if company in COMPANY_INDUSTRY_MAP:
        return COMPANY_INDUSTRY_MAP[company]

    if any(kw.lower() in company.lower() for kw in HEADHUNTER_KEYWORDS):
        return "헤드헌팅"

    for key, mapped in WANTED_MAPPING.items():
        if key in orig_industry:
            return mapped

    search_text = (description + " " + title + " " + company + " ").lower()
    for industry, keywords in INDUSTRY_KEYWORDS.items():
        if any(kw.lower() in search_text for kw in keywords):
            return industry

    return "기타"

def extract_experience_from_description(row):
    exp = str(row.get("experience", ""))
    if exp and exp not in ["nan", ""]:
        return exp

    desc = str(row.get("description", ""))
    title = str(row.get("title", ""))
    text = desc + " " + title

    patterns = [
        (r'경력\s*(\d+)년\s*이상', lambda m: m.group(1)),
        (r'경력\s*(\d+)\s*~\s*(\d+)년', lambda m: m.group(1)),
        (r'(\d+)년\s*이상\s*경력', lambda m: m.group(1)),
        (r'경력\s*(\d+)년', lambda m: m.group(1)),
        (r'신입\s*[·/]\s*경력', lambda m: "0"),
        (r'경력\s*무관', lambda m: "0"),
        (r'신입행원', lambda m: "0"),
        (r'신입', lambda m: "0"),
        (r'대리급', lambda m: "3"),
        (r'과장급', lambda m: "5"),
        (r'차장급', lambda m: "7"),
        (r'부장급', lambda m: "10"),
    ]

    for pattern, handler in patterns:
        match = re.search(pattern, text)
        if match:
            return handler(match)

    return ""

def normalize_experience(exp):
    exp = str(exp).strip()
    if not exp or exp in ["nan", ""]:
        return ""
    if "신입" in exp and "경력" not in exp:
        return "0"
    if "무관" in exp:
        return "0"
    nums = re.findall(r'\d+', exp)
    if not nums:
        return ""
    return str(int(nums[0]))

def extract_skills_from_description(row):
    existing = str(row.get("skills", ""))
    if existing and existing not in ["", "nan"]:
        return existing

    description = str(row.get("description", ""))
    title = str(row.get("title", ""))
    source = str(row.get("source", ""))

    text = description + " " + title
    if not text.strip():
        return ""

    found = [k for k in SKILL_KEYWORDS if k.lower() in text.lower()]

    if not found and source == "사람인":
        return "미확인"

    return ", ".join(found)

def infer_employment_type(row):
    existing = str(row.get("employment_type", ""))
    if existing and existing not in ["", "nan", "미공개"]:
        return existing

    title = str(row.get("title", "")).lower()
    desc = str(row.get("description", ""))[:200].lower()
    text = title + " " + desc

    if any(k in title for k in ["인턴", "intern"]):
        return "인턴"
    if any(k in text for k in ["계약직", "계약 직", "contract"]):
        return "계약직"
    if any(k in text for k in ["프리랜서", "freelance"]):
        return "프리랜서"
    if any(k in text for k in ["정규직", "정규 직"]):
        return "정규직"
    return "미공개"

# ── 함수 ──────────────────────────────────────────
def load_csv(path, source_name):
    if not os.path.exists(path):
        print(f"  [경고] {source_name} 파일 없음: {path}")
        return pd.DataFrame()
    df = pd.read_csv(path, encoding="utf-8-sig")
    df = clean_columns(df)
    print(f"  {source_name}: {len(df)}개 로드")
    return df

def normalize_columns(df, source_name):
    df = clean_columns(df)
    df["source"] = source_name
    return df[COLUMNS_ORDER]

def save_crawling_log(stats):
    os.makedirs(LOG_DIR, exist_ok=True)
    log_path = f"{LOG_DIR}/crawling_log.csv"
    log_row = {
        "date":     datetime.now().strftime("%Y-%m-%d"),
        "time":     datetime.now().strftime("%H:%M"),
        "wanted":   stats.get("원티드", 0),
        "saramin":  stats.get("사람인", 0),
        "jobkorea": stats.get("잡코리아", 0),
        "remember": stats.get("리멤버", 0),
        "total":    sum(stats.values()),
    }
    if os.path.exists(log_path):
        log_df = pd.read_csv(log_path, encoding="utf-8")
        log_df = pd.concat([log_df, pd.DataFrame([log_row])], ignore_index=True)
    else:
        log_df = pd.DataFrame([log_row])
    log_df.to_csv(log_path, index=False, encoding="utf-8")
    print(f"\n실행 로그 저장 → {log_path}")

def save_job_history(df_new, df_existing):
    os.makedirs(LOG_DIR, exist_ok=True)
    history_path = f"{LOG_DIR}/job_history.csv"
    today = datetime.now().strftime("%Y-%m-%d")

    if df_existing.empty:
        new_count    = len(df_new)
        closed_count = 0
    else:
        existing_urls = set(df_existing["url"])
        new_urls      = set(df_new["url"]) - existing_urls
        closed_urls   = existing_urls - set(df_new["url"])
        new_count     = len(new_urls)
        closed_count  = len(closed_urls)

    source_counts = df_new["source"].value_counts().to_dict()
    all_skills    = []
    for skills in df_new["skills"].dropna():
        if skills:
            all_skills.extend([s.strip() for s in str(skills).split(",")])
    top_skills = dict(Counter(all_skills).most_common(5))

    history_row = {
        "date":           today,
        "total_jobs":     len(df_new),
        "new_jobs":       new_count,
        "closed_jobs":    closed_count,
        "wanted_count":   source_counts.get("원티드", 0),
        "saramin_count":  source_counts.get("사람인", 0),
        "jobkorea_count": source_counts.get("잡코리아", 0),
        "remember_count": source_counts.get("리멤버", 0),
        "insurance_jobs": len(df_new[df_new["industry"].str.contains("금융·보험", na=False)]),
        "top_skills":     str(top_skills),
    }

    if os.path.exists(history_path):
        history_df = pd.read_csv(history_path, encoding="utf-8")
        history_df = history_df[history_df["date"] != today]
        history_df = pd.concat([history_df, pd.DataFrame([history_row])], ignore_index=True)
    else:
        history_df = pd.DataFrame([history_row])

    history_df.to_csv(history_path, index=False, encoding="utf-8")
    print(f"공고 변화 로그 저장 → {history_path}")
    print(f"  신규 공고: {new_count}개 | 마감 공고: {closed_count}개")

def save_new_jobs(df_new, df_existing):
    """신규 공고만 별도 CSV로 저장"""
    if df_existing.empty:
        new_df = df_new
    else:
        existing_urls = set(df_existing["url"])
        new_df = df_new[~df_new["url"].isin(existing_urls)]

    new_df = clean_columns(new_df)
    new_df.to_csv(f"{DATA_DIR}/new_jobs.csv", index=False, encoding="utf-8")
    print(f"신규 공고: {len(new_df)}개 → data/new_jobs.csv")
    return new_df

def save_active_jobs(df):
    """마감 공고 제거한 현재 지원 가능한 공고 저장"""
    today = datetime.now().strftime("%Y.%m.%d")

    def is_active(deadline):
        if not deadline or str(deadline) in ["상시채용", "nan", ""]:
            return True
        try:
            date_part = str(deadline)[:10].replace("-", ".")
            return date_part >= today
        except:
            return True

    active_df = df[df["deadline"].apply(is_active)]
    expired = len(df) - len(active_df)

    active_df = clean_columns(active_df)
    active_df.to_csv(f"{DATA_DIR}/active_jobs.csv", index=False, encoding="utf-8")
    print(f"마감 공고 제거: {expired}개 → active_jobs.csv {len(active_df)}개")
    return active_df

def merge_all():
    print("=== CSV 합치기 시작 ===\n")

    all_jobs_path = f"{DATA_DIR}/all_jobs.csv"
    if os.path.exists(all_jobs_path):
        df_existing = pd.read_csv(all_jobs_path, encoding="utf-8")
        print(f"기존 all_jobs.csv: {len(df_existing)}개\n")
    else:
        df_existing = pd.DataFrame()
        print("기존 all_jobs.csv 없음 (첫 실행)\n")

    dfs   = []
    stats = {}
    for source_name, path in CSV_FILES.items():
        df = load_csv(path, source_name)
        if df.empty:
            stats[source_name] = 0
            continue
        df = normalize_columns(df, source_name)
        stats[source_name] = len(df)
        dfs.append(df)

    if not dfs:
        print("\n[오류] 로드된 CSV 파일이 없어요!")
        return

    df_all = pd.concat(dfs, ignore_index=True)
    print(f"\n합치기 전: {len(df_all)}개")

    df_all = df_all.drop_duplicates(subset=["url"], keep="first")
    df_all = df_all.drop_duplicates(subset=["company", "title"], keep="first")
    print(f"중복 제거 후: {len(df_all)}개")

    df_all = df_all.fillna("")

    print("\n산업군 분류 중...")
    df_all["industry"] = df_all.apply(classify_industry, axis=1)
    print("산업군 분류 완료!")
    print(df_all["industry"].value_counts().to_string())

    print("\n스킬 재추출 중...")
    df_all["skills"] = df_all.apply(extract_skills_from_description, axis=1)
    print("완료!")

    before = len(df_all)
    df_all = df_all[(df_all["skills"] != "") | (df_all["source"] == "사람인")]
    print(f"스킬 없는 공고 제외: {before - len(df_all)}개 제거 → {len(df_all)}개")

    print("\n경력 추출 중...")
    df_all["experience"] = df_all.apply(extract_experience_from_description, axis=1)
    print("완료!")

    print("\n경력 정규화 중...")
    df_all["experience"] = df_all["experience"].apply(normalize_experience)
    print("완료!")

    df_all["employment_type"] = df_all.apply(infer_employment_type, axis=1)

    os.makedirs(DATA_DIR, exist_ok=True)
    df_all["experience"] = pd.to_numeric(df_all["experience"], errors="coerce").fillna("").apply(lambda x: str(int(x)) if x != "" else "")
    df_all = clean_columns(df_all)
    df_all.to_csv(all_jobs_path, index=False, encoding="utf-8")
    print(f"\nall_jobs.csv 저장 완료 → {len(df_all)}개")

    save_crawling_log(stats)
    save_job_history(df_all, df_existing)
    save_new_jobs(df_all, df_existing)
    save_active_jobs(df_all)

    print("\n=== 최종 요약 ===")
    print(f"총 공고 수: {len(df_all)}개")
    print("\n사이트별:")
    for source, count in df_all["source"].value_counts().items():
        print(f"  {source}: {count}개")
    print("\n산업군별:")
    for industry, count in df_all["industry"].value_counts().items():
        print(f"  {industry}: {count}개")
    print("\n스킬별 (상위 10):")
    all_skills = []
    for skills in df_all["skills"].dropna():
        if skills:
            all_skills.extend([s.strip() for s in str(skills).split(",")])
    all_skills = [s for s in all_skills if s != "미확인"]
    for skill, count in Counter(all_skills).most_common(10):
        print(f"  {skill}: {count}개")

    return df_all

# ── 실행 ──────────────────────────────────────────
if __name__ == "__main__":
    merge_all()