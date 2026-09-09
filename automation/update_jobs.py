from __future__ import annotations

import base64
from concurrent.futures import ThreadPoolExecutor
import hashlib
import html
import json
import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlparse

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
    "신입", "인턴", "경력무관", "경력 무관", "주니어", "junior talent",
    "entry level", "entry-level", "new grad", "graduate", "intern",
    "assistant", "어시스턴트", "체험형", "채용연계", "전환형",
]
EXCLUDE_TERMS = [
    "데이터센터 시설", "데이터 센터 시설", "시설관리", "시공관리", "안전관리",
    "단순 라벨링", "데이터 라벨러", "cx 기획", "마케팅 기획", "senior",
    "시니어", "팀장", "파트장", "lead data", "principal", "임원",
]
CLOSED_TERMS = ["접수마감", "채용마감", "모집마감", "지원마감", "closed", "마감된 공고"]
RECRUIT_TERMS = ["채용", "모집", "공고", "recruit", "career", "job", "신입", "인턴", "지원자격"]
NON_POSTING_TITLES = [
    "더보기", "메인", "jobs", "careers", "career doosan", "apply", "채용 프로세스",
    "채용 공정성안내", "자주 하는 질문", "1:1 문의하기", "채용서류반환신청",
    "회원가입", "이용약관", "개인정보처리방침", "이메일무단수집거부", "채용 문의처",
    "인재 db에 등록", "지원안내", "직무소개", "회사생활", "지난 공개 채용 다시보기",
    "신입채용 바로가기", "합류 여정", "채용 공고", "공고", "matchjob",
]
CORE_DATA_TERMS = [
    "데이터 분석", "데이터분석", "데이터 엔지니어", "데이터엔지니어",
    "데이터 사이언", "data analyst", "data engineer", "data scientist",
    "machine learning", "ml engineer", "ai engineer", "머신러닝", "인공지능",
    "생성형 ai", "llm", "소프트웨어", "software", "sw개발", "sw 개발",
    "백엔드", "backend", "클라우드", "cloud", "devops", "mlops", "sql", "python",
    "business intelligence", "bi 분석", "마케팅 분석", "crm 분석",
]
COMPUTER_SCIENCE_TERMS = [
    "sw", "개발자", "개발", "engineer", "engineering", "frontend", "front-end",
    "프론트엔드", "서버", "server", "api", "보안", "security", "사이버",
    "인프라", "infrastructure", "sre", "qa", "quality assurance", "테스트 자동화",
    "로봇", "robot", "자율주행", "computer vision", "컴퓨터 비전",
    "알고리즘", "분산 시스템", "네트워크", "network", "운영체제",
    "시스템 분석", "기술 지원", "technical", "디지털 트랜스포메이션",
]
RELATED_TERMS = DATA_TERMS + COMPUTER_SCIENCE_TERMS
BATCH_RECRUIT_TERMS = ["신입사원 채용", "신입사원채용", "신입 공채", "신입공채", "신입 공개채용"]
TECH_BATCH_PREFIXES = ["삼성", "롯데이노베이트", "현대오토에버", "SK AX", "LG CNS", "POSCO DX", "KT DS", "NAVER", "카카오"]
TECH_ROLE_TITLE_TERMS = CORE_DATA_TERMS + [
    "sw", "개발자", "engineer", "engineering", "프론트엔드", "frontend",
    "서버", "server", "보안", "security", "사이버", "침해사고", "인프라",
    "sre", "로봇", "robot", "자율주행", "computer vision", "컴퓨터 비전",
]
NON_TECH_DOMAIN_TITLES = ["식품", "마케팅", "인플루언서", "로컬임팩트", "제휴", "cm_어시스턴트"]
STRONG_CONTEXT_TERMS = [term for term in RELATED_TERMS if term not in {
    "ai", "api", "qa", "platform", "플랫폼", "technical", "개발", "기술 지원",
}]


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


def candidate(company: dict, url: str, title: str, snippet: str, source: str) -> dict | None:
    url = normalized_url(urljoin(company["career_home"], url))
    if not url or not official(url, company["domains"]):
        return None
    return {
        "company": company["name"], "url": url, "title": clean_text(title),
        "snippet": clean_text(snippet), "discoveredBy": source,
    }


def direct_results(company: dict) -> list[dict]:
    """Discover postings exposed in official HTML and JobPosting JSON-LD."""
    results = []
    discovery_urls = list(dict.fromkeys([company["career_home"], *company.get("discovery_urls", [])]))
    visited_pages = set()
    for discovery_url in discovery_urls:
        if discovery_url in visited_pages or len(visited_pages) >= 5:
            continue
        visited_pages.add(discovery_url)
        response = requests.get(discovery_url, headers=HEADERS, timeout=25)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        for anchor in soup.select("a[href]"):
            target_url = normalized_url(urljoin(discovery_url, anchor.get("href", "")))
            context = clean_text(anchor.parent.get_text(" ", strip=True))[:1000]
            title_node = anchor.select_one(".tit, .title, .job-title, [class*='job-title']")
            title = clean_text(title_node.get_text(" ", strip=True) if title_node else anchor.get_text(" ", strip=True))
            url = anchor.get("href", "")
            target_path = urlparse(target_url).path.lower().rstrip("/")
            listing_label = contains_any(title, ["전체 채용공고", "채용공고", "채용정보", "채용 보기", "jobs", "job openings"])
            listing_path = target_path.endswith(("/jobs", "/recruit", "/careers", "/apply", "/notification")) or any(
                token in target_path for token in ["applylist", "recruit/list", "rcrt/list"]
            )
            detail_path = any(token in target_path for token in ["jobs-view", "/view", "/detail"])
            if official(target_url, company["domains"]) and not detail_path and (listing_label or listing_path):
                if target_url not in visited_pages and target_url not in discovery_urls and len(discovery_urls) < 5:
                    discovery_urls.append(target_url)
            if not contains_any(f"{title} {context} {url}", RECRUIT_TERMS + DATA_TERMS):
                continue
            item = candidate(company, urljoin(discovery_url, url), title or context[:120], context, "official_page")
            if item:
                results.append(item)

        for script in soup.select('script[type="application/ld+json"]'):
            try:
                payload = json.loads(script.string or "null")
            except json.JSONDecodeError:
                continue
            stack = payload if isinstance(payload, list) else [payload]
            while stack:
                node = stack.pop()
                if isinstance(node, list):
                    stack.extend(node)
                elif isinstance(node, dict):
                    if node.get("@type") == "JobPosting":
                        item = candidate(
                            company, node.get("url", discovery_url),
                            node.get("title", ""), node.get("description", ""), "json_ld",
                        )
                        if item:
                            results.append(item)
                    stack.extend(value for value in node.values() if isinstance(value, (dict, list)))
    return results


def sitemap_results(company: dict) -> list[dict]:
    """Use official sitemaps for job detail pages that are absent from navigation."""
    results = []
    tokens = ("recruit", "career", "job", "apply", "notification", "posting", "rcrt")
    for domain in company["domains"]:
        for scheme in ("https",):
            try:
                response = requests.get(f"{scheme}://{domain}/sitemap.xml", headers=HEADERS, timeout=15)
                response.raise_for_status()
                root = ET.fromstring(response.content)
            except (requests.RequestException, ET.ParseError):
                continue
            urls = [element.text.strip() for element in root.iter() if element.tag.endswith("loc") and element.text]
            for url in urls[:2000]:
                if any(token in urlparse(url).path.lower() for token in tokens):
                    item = candidate(company, url, url.rstrip("/").split("/")[-1], "", "sitemap")
                    if item:
                        results.append(item)
                        if len(results) >= 40:
                            return results
    return results


def naver_api_results(company: dict) -> list[dict]:
    results = []
    for first_index in range(0, 200, 10):
        response = requests.get(
            "https://recruit.navercorp.com/rcrt/loadJobList.do",
            params={"firstIndex": first_index}, headers=HEADERS, timeout=25,
        )
        response.raise_for_status()
        rows = response.json().get("list", [])
        if not rows:
            break
        for row in rows:
            company_label = clean_text(row.get("sysCompanyCdNm", ""))
            if company["name"] == "NAVER Cloud" and "CLOUD" not in company_label.upper():
                continue
            if company["name"] == "NAVER" and "CLOUD" in company_label.upper():
                continue
            title = clean_text(row.get("annoSubject", ""))
            detail = " ".join(clean_text(str(row.get(key, ""))) for key in (
                "classCdNm", "subJobCdNm", "empTypeCdNm", "staYmdTime", "endYmdTime",
            ))
            item = candidate(
                company,
                f"https://recruit.navercorp.com/rcrt/view.do?annoId={row.get('annoId')}",
                title, f"{company_label} {detail}", "official_api",
            )
            if item:
                results.append(item)
        if len(rows) < 10:
            break
    return results


def kakao_api_results(company: dict) -> list[dict]:
    results = []
    endpoint = "https://careers.kakao.com/public/api/job-list"
    for part in ("TECHNOLOGY", "BUSINESS_SERVICES", "STAFF"):
        for page in range(1, 11):
            response = requests.get(endpoint, params={"part": part, "page": page}, headers=HEADERS, timeout=25)
            response.raise_for_status()
            payload = response.json()
            for row in payload.get("jobList", []):
                fields = [
                    row.get("introduction", ""), row.get("workContentDesc", ""),
                    row.get("qualification", ""), row.get("krewComment", ""),
                    row.get("employeeTypeName", ""), row.get("locationName", ""),
                    " ".join(skill.get("skillSetName", "") for skill in (row.get("skillSetList") or [])),
                ]
                item = candidate(
                    company, f"https://careers.kakao.com/jobs/{row.get('realId')}",
                    row.get("jobOfferTitle", ""), " ".join(fields), "official_api",
                )
                if item:
                    results.append(item)
            if page >= int(payload.get("totalPage", 1)):
                break
    return results


SAMSUNG_SUBSIDIARY_CODES = {
    "삼성전자": ["C10CAA", "C10CAH"],
    "삼성디스플레이": ["C90"], "삼성SDI": ["C31"],
    "삼성전기": ["C40"], "삼성SDS": ["C60"],
    "삼성생명": ["E11"], "삼성화재": ["E21"],
    "삼성카드": ["E31"], "삼성증권": ["E40"],
    "삼성물산": ["B12"],
}


def samsung_results(company: dict) -> list[dict]:
    results = []
    for code in SAMSUNG_SUBSIDIARY_CODES.get(company["name"], []):
        page_url = f"https://www.samsungcareers.com/subsid/detail/{code}"
        response = requests.get(page_url, headers=HEADERS, timeout=25)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        for link in soup.select('a[name="btnRecruit"][data-value]'):
            title_node = link.select_one(".title")
            company_node = link.select_one(".company")
            if not title_node:
                continue
            container = link.find_parent("li") or link.parent.parent
            snippet = clean_text(container.get_text(" ", strip=True))
            display_name = clean_text(company_node.get_text(" ", strip=True)) if company_node else company["name"]
            results.append({
                "company": display_name,
                "url": f"{page_url}?recruitId={link.get('data-value')}",
                "title": clean_text(title_node.get_text(" ", strip=True)),
                "snippet": snippet,
                "discoveredBy": "official_api",
            })
    return results


def bing_results(company: dict) -> list[dict]:
    results = []
    for domain in company["domains"]:
        queries = [f'site:{domain} "{company["name"]}" (데이터 OR AI OR SW OR 클라우드) (신입 OR 인턴 OR 주니어)']
        for query in queries:
            response = requests.get("https://www.bing.com/search", params={"q": query, "format": "rss"}, headers=HEADERS, timeout=25)
            response.raise_for_status()
            root = ET.fromstring(response.content)
            for row in root.findall(".//item")[:30]:
                link = row.findtext("link", "")
                link = normalized_url(link)
                if not link or not official(link, company["domains"]):
                    continue
                results.append({
                    "company": company["name"],
                    "url": link,
                    "title": clean_text(row.findtext("title", "")),
                    "snippet": clean_text(row.findtext("description", "")),
                    "discoveredBy": "bing",
                })
    return results


def discover(company: dict) -> tuple[list[dict], list[str]]:
    results, errors = [], []
    finders = [("official_page", direct_results), ("sitemap", sitemap_results), ("bing", bing_results)]
    if company["name"] in {"NAVER", "NAVER Cloud"}:
        finders.insert(0, ("official_api", naver_api_results))
    if company["name"] == "카카오":
        finders.insert(0, ("official_api", kakao_api_results))
    if company["name"] in SAMSUNG_SUBSIDIARY_CODES:
        finders.insert(0, ("official_api", samsung_results))
    for name, finder in finders:
        try:
            results.extend(finder(company))
        except (requests.RequestException, ET.ParseError, ValueError) as exc:
            errors.append(f"{name}:{type(exc).__name__}")
    unique = {}
    for item in results:
        unique[item["url"]] = item
    return list(unique.values()), errors


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
    for term in terms:
        needle = term.lower()
        if re.fullmatch(r"[a-z0-9+#.]{1,3}", needle):
            if re.search(rf"(?<![a-z0-9]){re.escape(needle)}(?![a-z0-9])", lower):
                return True
        elif needle in lower:
            return True
    return False


def technical_relevance(title: str, context: str) -> bool:
    if contains_any(title, NON_TECH_DOMAIN_TITLES):
        return False
    if contains_any(title, TECH_ROLE_TITLE_TERMS):
        return True
    hits = sum(1 for term in STRONG_CONTEXT_TERMS if contains_any(context, [term]))
    return hits >= 2


def deadline_from(text: str) -> datetime | None:
    # Some career sites show the application range beside the title without a
    # separate "deadline" label, so always inspect the top of the posting too.
    contexts = [text[:5000]]
    for match in re.finditer(r"마감|접수기간|지원기간|지원 마감|deadline|until|접수", text, re.I):
        contexts.append(text[max(0, match.start() - 45):match.end() + 90])
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
    if any(term in lower for term in ["보안", "security", "사이버", "네트워크", "network"]):
        return "보안 / 인프라"
    if any(term in lower for term in ["qa", "quality assurance", "테스트"]):
        return "QA / 테스트"
    if any(term in lower for term in ["개발", "engineer", "server", "frontend", "프론트엔드"]):
        return "컴퓨터공학 / 개발"
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
    preview = " ".join([title, candidate["snippet"]])
    path = urlparse(candidate["url"]).path.lower()
    if len(title) < 4 or title.lower().strip() in NON_POSTING_TITLES:
        return None, "not_job_posting"
    if re.search(r"\.(?:hc|kc)(?:\?|$)|[?=&]", title.lower()):
        return None, "not_job_posting"
    if re.fullmatch(r"[a-z0-9_-]+", title.lower()) and " " not in title:
        return None, "not_job_posting"
    if candidate.get("discoveredBy") == "sitemap" and (
        any(token in path for token in ["/blog", "/news", "/story", "/people", "/culture"])
        or not any(token in path for token in ["/job", "/recruit", "/apply", "/notification", "/rcrt"])
    ):
        return None, "not_job_posting"
    if candidate.get("discoveredBy") != "official_api" and not contains_any(preview, RECRUIT_TERMS) and not any(token in path for token in ["recruit", "career", "job", "apply", "notification", "rcrt"]):
        return None, "not_job_posting"
    combined = " ".join([candidate["company"], title, candidate["snippet"], page_text])
    batch_recruit = contains_any(title, BATCH_RECRUIT_TERMS) and any(
        title.lower().startswith(prefix.lower()) or (
            not candidate["company"].startswith("롯데")
            and candidate["company"].lower().startswith(prefix.lower())
        )
        for prefix in TECH_BATCH_PREFIXES
    )
    if candidate.get("discoveredBy") == "official_api" and not technical_relevance(title, candidate["snippet"]) and not batch_recruit:
        return None, "not_data_track"
    if candidate.get("discoveredBy") in {"official_page", "bing"}:
        title_related = contains_any(title, RELATED_TERMS)
        broad_entry_posting = contains_any(title, ENTRY_TERMS) and contains_any(preview, RELATED_TERMS)
        if not title_related and not broad_entry_posting and not batch_recruit:
            return None, "not_data_track"
    if not contains_any(combined, RELATED_TERMS) and not batch_recruit:
        return None, "not_data_track"
    title_lower = title.lower()
    if contains_any(title_lower, ["경력", "senior", "lead", "principal"]) and not contains_any(title_lower, ENTRY_TERMS):
        return None, "career_only"
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
    track = "통합 공채 · 직무 확인" if batch_recruit else track_for(combined)
    eligibility_text = page_text if candidate.get("discoveredBy") == "sitemap" else preview
    entry_confirmed = contains_any(eligibility_text, ENTRY_TERMS)
    if not entry_confirmed:
        return None, "eligibility_unconfirmed"
    kind = "인턴" if contains_any(eligibility_text, ["인턴", "intern"]) else ("신입 · 어시스턴트" if contains_any(eligibility_text, ["어시스턴트", "assistant"]) else "신입 · 정규직")
    if kind == "인턴" and contains_any(combined, ["채용연계", "전환형"]):
        kind = "신입 · 채용연계형 인턴"
    elif kind == "인턴":
        kind = "신입 · 인턴"
    display_company = candidate["company"]
    named_company = re.match(r"^(?:\[)?(롯데[0-9A-Za-z가-힣&]+)", title) or re.match(r"^([0-9A-Za-z가-힣&]+)\s+20\d{2}년", title)
    if named_company:
        display_company = named_company.group(1)
    initial, color = company_style(display_company)
    job_id = hashlib.sha1((display_company + "|" + normalized_url(candidate["url"])).encode()).hexdigest()[:16]
    return {
        "id": job_id,
        "company": display_company,
        "title": title[:120],
        "kind": kind,
        "place": "원문 확인",
        "deadline": deadline.isoformat() if deadline else None,
        "deadlineLabel": deadline.strftime("%m.%d %H:%M") if deadline else "원문 확인",
        "track": track,
        "note": ("통합 신입 공채입니다. AI·SW·데이터 세부 직무 포함 여부를 원문에서 확인하세요." if batch_recruit else f"공식 채용 원문에서 {track} 연관성이 확인된 공고입니다."),
        "check": ("직무별 전공·스킬 조건을 원문에서 확인하세요." if batch_recruit else "신입·인턴 지원 조건을 확인했습니다. 상세 자격과 근무지는 원문에서 다시 확인하세요."),
        "url": normalized_url(candidate["url"]),
        "source": f"{display_company} 공식 채용",
        "initial": initial,
        "color": color,
        "verifiedAt": NOW.isoformat(timespec="minutes"),
    }, "verified"


def revalidate_existing(job: dict, review: list[dict], checked_at: str) -> dict | None:
    """Recheck a published posting rather than trusting only its old deadline."""
    url = job.get("url", "")
    page_text, fetch_error = fetch_page(url)
    if fetch_error:
        review.append({
            "company": job.get("company", ""), "url": url,
            "title": job.get("title", ""), "snippet": job.get("note", ""),
            "reason": f"existing_{fetch_error}", "checkedAt": checked_at,
        })
        return job
    title = clean_text(job.get("title", ""))
    title_at = page_text.lower().find(title.lower()) if title else -1
    if title_at < 0:
        review.append({
            "company": job.get("company", ""), "url": url,
            "title": title, "snippet": job.get("note", ""),
            "reason": "existing_posting_not_found", "checkedAt": checked_at,
        })
        return job

    posting_text = page_text[max(0, title_at - 500):title_at + len(title) + 2500]
    if contains_any(posting_text, CLOSED_TERMS):
        return None
    deadline = deadline_from(posting_text)
    if deadline and deadline < NOW:
        return None
    refreshed = dict(job)
    if deadline:
        refreshed["deadline"] = deadline.isoformat()
        refreshed["deadlineLabel"] = deadline.strftime("%m.%d %H:%M")
    elif job.get("deadline"):
        try:
            if datetime.fromisoformat(job["deadline"]) < NOW:
                return None
        except ValueError:
            pass
    refreshed["verifiedAt"] = NOW.isoformat(timespec="minutes")
    return refreshed


def main() -> None:
    companies = read_json(ROOT / "automation" / "companies.json", [])
    old_feed = read_json(ROOT / "jobs.json", {"schemaVersion": 1, "jobs": []})
    if os.getenv("FRESH_START") == "1":
        old_feed = {"schemaVersion": 1, "jobs": []}
    review = []
    state = {"lastRunAt": NOW.isoformat(timespec="seconds"), "companies": {}}
    verified = {}
    for job in old_feed.get("jobs", []):
        refreshed = revalidate_existing(job, review, state["lastRunAt"])
        if refreshed:
            verified[refreshed["id"]] = refreshed

    with ThreadPoolExecutor(max_workers=8) as executor:
        discovery_results = list(executor.map(discover, companies))

    for company, (candidates, discovery_errors) in zip(companies, discovery_results):
        company_state = {"discovered": 0, "verified": 0, "sources": {}, "errors": []}
        try:
            company_state["discovered"] = len(candidates)
            company_state["errors"] = discovery_errors
            for item in candidates:
                source = item.get("discoveredBy", "unknown")
                company_state["sources"][source] = company_state["sources"].get(source, 0) + 1
            seen_urls = set()
            for candidate in candidates:
                if candidate["url"] in seen_urls or candidate["url"].rstrip("/") == company["career_home"].rstrip("/"):
                    continue
                seen_urls.add(candidate["url"])
                if candidate.get("discoveredBy") in {"official_page", "bing"}:
                    title = candidate["title"]
                    preview = f"{title} {candidate['snippet']}"
                    batch_recruit = contains_any(title, BATCH_RECRUIT_TERMS) and any(
                        title.lower().startswith(prefix.lower()) or (
                            not candidate["company"].startswith("롯데")
                            and candidate["company"].lower().startswith(prefix.lower())
                        )
                        for prefix in TECH_BATCH_PREFIXES
                    )
                    if not contains_any(title, RELATED_TERMS) and not (
                        contains_any(title, ENTRY_TERMS) and contains_any(preview, RELATED_TERMS)
                    ) and not batch_recruit:
                        continue
                if candidate.get("discoveredBy") == "official_api":
                    page_text, fetch_error = candidate.get("snippet", ""), None
                else:
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
            company_state["errors"].append(f"company:{type(exc).__name__}")
        state["companies"][company["name"]] = company_state

    jobs = sorted(verified.values(), key=lambda item: item.get("deadline") or "9999")
    feed = {"schemaVersion": 1, "updatedAt": NOW.isoformat(timespec="seconds"), "jobs": jobs}
    (ROOT / "jobs.json").write_text(json.dumps(feed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (ROOT / "automation" / "state.json").write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (ROOT / "automation" / "review-queue.json").write_text(json.dumps(review[:100], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
