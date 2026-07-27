#!/bin/bash

# 이 스크립트가 위치한 폴더를 프로젝트 경로로 사용
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

PYTHON="$PROJECT_DIR/.venv/bin/python"
LOG="$PROJECT_DIR/logs/cron.log"

# 현재 사용자의 홈 디렉터리 기준
N8N_DIR="$HOME/.n8n-files"

mkdir -p "$PROJECT_DIR/logs"
mkdir -p "$N8N_DIR"

cd "$PROJECT_DIR" || exit 1

echo "===== $(date) 크롤링 시작 =====" >> "$LOG"

"$PYTHON" crawlers/wanted.py >> "$LOG" 2>&1
"$PYTHON" crawlers/saramin.py >> "$LOG" 2>&1
"$PYTHON" crawlers/jobkorea.py >> "$LOG" 2>&1
"$PYTHON" crawlers/remember.py >> "$LOG" 2>&1
"$PYTHON" crawlers/merge.py >> "$LOG" 2>&1

sleep 3

cp "$PROJECT_DIR/data/all_jobs.csv" "$N8N_DIR/all_jobs.csv"
echo "all_jobs cp exit: $?" >> "$LOG"

cp "$PROJECT_DIR/data/new_jobs.csv" "$N8N_DIR/new_jobs.csv"
echo "new_jobs cp exit: $?" >> "$LOG"

cp "$PROJECT_DIR/data/active_jobs.csv" "$N8N_DIR/active_jobs.csv"
echo "active_jobs cp exit: $?" >> "$LOG"

echo "$(date) 파일 복사 완료" >> "$LOG"