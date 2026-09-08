from __future__ import annotations

import base64
import hashlib
import html
import json
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs, quote_plus, urlparse

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
SEOUL = timezone(timedelta(hours=9))
NOW = datetime.now(SEOUL)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; SSAFYDataJobs/1.0; public recruitment monitor)"
}
DATA_TERMS = [
    "데이터 분석", "데이터분석", "데이터 엔지니어", "데이터엔지니어",
    "데이터 사이언", "머신러닝", "machine learning", "data analyst",
    "data engineer", "data scientist", "ml engineer", "ai engineer",
    "인공지능", "ai/데이터", "ai · 데이터", "생성형 ai", "llm",
    "소프트웨어", "software", "sw개발", "sw 개발", "백엔드", "backend",
    "클라우드", "cloud", "플랫폼", "platform", "devops", "mlops",
    "데이터베이스", "database", "dba", "sql", "python", "통계",
    "business intelligence", "bi 분석", "디지털", "자동화", "rpa",
    "추천", "검색", "리서치", "research", "마케팅 분석", "crm",
]
ENTRY_TERMS = [
    "신입", "경력무", "인턴", "경력무", "경력무관", "경력 무관",
    "entry level", "entry-level", "new grad", "graduate", "intern",
]
EXCLUDE_TERMS = [
    "데이터센터 시설", "데이터 센터 시설", "시설관리", "시공관리", "안전관리",
    "단순 라벨링", "데이터 라벨러", "cx 기획", "마케팅 기획", "senior",
    "시니어", "팀장", "파트장", "lead data", "principal", "임원",
]
CLOSED_TERMS = ["접수마감", "채용마감", "모집마감", "지원마감", "closed", "마감된 공고"]


def read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def clean_text(raw: str) -> str:
    soup = BeautifulSoup(html.unescape(raw or ""), "html.parser")
    return re.sub(r"\s+", " ", soup.get_text(" ", strip=True)).strip()


def normalized_url(raw: str) -> str:
    parsed = urlparse(raw)
    if "bing.com" in parsed.netloc and parsed.path.startswith("/ck/a"):
        candidate = parse_qs(parsed.query).get("u", [raw])[0]
        if candidate.startswith("a1"):
            encoded = candidate[2:]
            try:
                candidate = base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)).decode("utf-8")
            except (ValueError, UnicodeDecodeError):
                candidate = encoded
        raw = candidate
        parsed = urlparse(raw)
    return parsed._replace(fragment="").geturl().rstrip("/")


def official(url: str, domains: list[str]) -> bool:
    host = urlparse(url).netloc.lower().split(":")[0]
    return any(host == domain or host.endswith("." + domain) for domain in domains)


def bing_results(company: dict) -> list[dict]:
    results = []
    for domain in company["domains"]:
        queries = [
            f'site:{domain} "{company["name"]}" (데이터 OR AI OR 소프트웨어 OR 디지털) 채용',
            f'site:{domain} "{company["name"]}" (신입 OR 인턴 OR 주니어) 채용',
        ]
        for query in queries:
            response = requests.get(
                "https://www.bing.com/search",
                params={"q": query}, headers=HEADERS, timeout=25,
            )
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            for row in soup.select("li.b_algo")[:20]:
                anchor = row.select_one("h2 a")
                if not anchor:
                    continue
                link = anchor.get("href", "")
                parsed = urlparse(link)
                if "duckduckgo.com" in parsed.netloc:
                    link = parse_qs(parsed.query).get("uddg", [link])[0]
                link = normalized_url(link)
                if not link or not official(link, company["domains"]):
                    continue
                snippet = row.select_one(".b_caption p")
                results.append({
                    "company": company["name"],
                    "url": link,
                    "title": clean_text(anchor.get_text(" ", strip=True)),
                    "snippet": clean_text(snippet.get_text(" ", strip=True) if snippet else ""),
                })
    return results


def fetch_page(url: str) -> tuple[str, str | None]:
    try:
        response = requests.get(url, headers=HEADERS, timeout=25, allow_redirects=True)
        response.raise_for_status()
        if "text/html" not in response.headers.get("content-type", ""):
            return "", "not_html"
        text = clean_text(response.text)
        return text[:100_000], None if len(text) >= 180 else "insufficient_text"
    except requests.RequestException as exc:
        return "", type(exc).__name__


def contains_any(text: str, terms: list[str]) -> bool:
    lower = text.lower()
    return any(term.lower() in lower for term in terms)


def deadline_from(text: str) -> datetime | None:
    contexts = []
    for match in re.finditer(r"마감|접수기간|지원기간|지원 마감|deadline|until|접수", text, re.I):
        contexts.append(text[max(0, match.start() - 45):match.end() + 90])
    contexts = contexts or [text[:1500]]
    dates = []
    patterns = [
        r"(20\d{2})[./-]\s*(\d{1,2})[./-]\s*(\d{1,2})(?:\D{0,12}(\d{1,2})[:시]\s*(\d{1,2})?)?",
        r"(20\d{2})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일(?:\D{0,12}(\d{1,2})\s*시\s*(\d{1,2})?)?",
    ]
    for context in contexts:
        for pattern in patterns:
            for match in re.finditer(pattern, context, re.I):
                year, month, day = map(int, match.group(1, 2, 3))
                hour = int(match.group(4) or 23)
                minute = int(match.group(5) or 59)
                try:
                    value = datetime(year, month, day, hour, minute, tzinfo=SEOUL)
                    if NOW - timedelta(days=2) <= value <= NOW + timedelta(days=370):
                        dates.append(value)
                except ValueError:
                    pass
    return max(dates) if dates else None


def senior_career_required(text: str) -> bool:
    lower = text.lower()
    if "경력무관" in lower or "경력 무관" in lower:
        return False
    matches = re.findall(r"경력\s*([1-9]\d*)\s*년\s*(?:이상|필수|~)", lower)
    return any(int(years) >= 4 for years in matches)


def track_for(text: str) -> str:
    lower = text.lower()
    if any(term in lower for term in ["data engineer", "데이터 엔지니어", "데이터엔지니어", "파이프라인", "data platform"]):
        return "데이터 엔지니어링"
    if any(term in lower for term in ["machine learning", "ml engineer", "ai engineer", "머신러닝", "인공지능"]):
        return "AI / ML"
    if any(term in lower for term in ["data scientist", "데이터 사이언"]):
        return "데이터 사이언스"
    if any(term in lower for term in ["소프트웨어", "software", "sw개발", "sw 개발", "백엔드", "backend"]):
        return "SW / 백엔드"
    if any(term in lower for term in ["클라우드", "cloud", "platform", "플랫폼", "devops"]):
        return "클라우드 / 플랫폼"
    if any(term in lower for term in ["마케팅", "crm", "리서치", "research"]):
        return "비즈니스 분석"
    return "데이터 / 디지털"


def company_style(name: str) -> tuple[str, str]:
    initial = re.sub(r"[^A-Za-z0-9]", "", name)[:2].upper()
    if not initial:
        initial = name[:2]
    colors = ["blue", "orange", "green"]
    color = colors[int(hashlib.sha1(name.encode()).hexdigest(), 16) % len(colors)]
    return initial, color


def classify(candidate: dict, page_text: str) -> tuple[dict | None, str]:
    title = candidate["title"].strip()
    combined = " ".join([candidate["company"], title, candidate["snippet"], page_text])
    if not contains_any(combined, DATA_TERMS):
        return None, "not_data_track"
    if contains_any(title + " " + candidate["snippet"], EXCLUDE_TERMS):
        return None, "excluded_role"
    if senior_career_required(combined):
        return None, "senior_career_required"
    if re.search(r"(?:석사|박사)\s*(?:이상|필수)", combined):
        return None, "advanced_degree_required"
    deadline = deadline_from(combined)
    if deadline and deadline < NOW:
        return None, "expired"
    if contains_any(page_text[:2500], CLOSED_TERMS):
        return None, "marked_closed"
    track = track_for(combined)
    entry_confirmed = contains_any(combined, ENTRY_TERMS)
    kind = "인턴" if contains_any(combined, ["인턴", "intern"]) else ("신입 · 정규직" if entry_confirmed else "지원자격 확인")
    if kind == "인턴" and contains_any(combined, ["채용연계", "전환형"]):
        kind = "신입 · 채용연계형 인턴"
    elif kind == "인턴":
        kind = "신입 · 인턴"
    initial, color = company_style(candidate["company"])
    job_id = hashlib.sha1((candidate["company"] + "|" + normalized_url(candidate["url"])).encode()).hexdigest()[:16]
    return {
        "id": job_id,
        "company": candidate["company"],
        "title": title[:120],
        "kind": kind,
        "place": "원문 확인",
        "deadline": deadline.isoformat() if deadline else None,
        "deadlineLabel": deadline.strftime("%m.%d %H:%M") if deadline else "원문 확인",
        "track": track,
        "note": f"공식 채용 원문에서 {track} 연관성이 확인된 공고입니다.",
        "check": ("신입·인턴 지원 조건을 확인했습니다. 상세 자격과 근무지는 원문에서 다시 확인하세요." if entry_confirmed else "데이터 트랙 연관성으로 먼저 포착했습니다. 신입 지원 가능 여부와 마감일을 원문에서 확인하세요."),
        "url": normalized_url(candidate["url"]),
        "source": f"{candidate['company']} 공식 채용",
        "initial": initial,
        "color": color,
        "verifiedAt": NOW.isoformat(timespec="minutes"),
    }, "verified"


def main() -> None:
    companies = read_json(ROOT / "automation" / "companies.json", [])
    old_feed = read_json(ROOT / "jobs.json", {"schemaVersion": 1, "jobs": []})
    retained = {}
    for job in old_feed.get("jobs", []):
        try:
            if not job.get("deadline") or datetime.fromisoformat(job["deadline"]) >= NOW:
                retained[job["id"]] = job
        except (KeyError, ValueError):
            pass

    verified = dict(retained)
    review = []
    state = {"lastRunAt": NOW.isoformat(timespec="seconds"), "companies": {}}

    for company in companies:
        company_state = {"discovered": 0, "verified": 0, "error": None}
        try:
            candidates = bing_results(company)
            company_state["discovered"] = len(candidates)
            seen_urls = set()
            for candidate in candidates:
                if candidate["url"] in seen_urls or candidate["url"].rstrip("/") == company["career_home"].rstrip("/"):
                    continue
                seen_urls.add(candidate["url"])
                page_text, fetch_error = fetch_page(candidate["url"])
                if fetch_error:
                    review.append({**candidate, "reason": fetch_error, "checkedAt": state["lastRunAt"]})
                    continue
                job, reason = classify(candidate, page_text)
                if job:
                    verified[job["id"]] = job
                    company_state["verified"] += 1
                elif reason not in {"not_data_track", "expired", "marked_closed", "excluded_role"}:
                    review.append({**candidate, "reason": reason, "checkedAt": state["lastRunAt"]})
        except (requests.RequestException, ET.ParseError) as exc:
            company_state["error"] = type(exc).__name__
        state["companies"][company["name"]] = company_state
        time.sleep(0.35)

    jobs = sorted(verified.values(), key=lambda item: item.get("deadline") or "9999")
    feed = {"schemaVersion": 1, "updatedAt": NOW.isoformat(timespec="seconds"), "jobs": jobs}
    (ROOT / "jobs.json").write_text(json.dumps(feed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (ROOT / "automation" / "state.json").write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (ROOT / "automation" / "review-queue.json").write_text(json.dumps(review[:100], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
