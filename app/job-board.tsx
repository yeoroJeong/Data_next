'use client';

import { useMemo, useState } from 'react';
import { ArrowUpRight, Building2, CheckCircle2, ChevronDown, Database, RefreshCw, Search } from 'lucide-react';

export type Job = {
  id: string; company: string; title: string; kind: string; place: string;
  deadline: string | null; deadlineLabel: string; track: string; note: string;
  check: string; url: string; source: string; initial: string;
  color: 'blue' | 'orange' | 'green'; verifiedAt: string;
};
export type Feed = { schemaVersion: number; updatedAt: string; jobs: Job[] };
export type Company = { name: string; group: string; category: string; career_home: string };
export type CurrentUser = { displayName: string };

const fallback: Feed = {
  schemaVersion: 1,
  updatedAt: '2026-09-08T14:00:00+09:00',
  jobs: [{
    id: 'hanwha-life-2026-ai-data', company: '한화생명',
    title: '2026 신입공채 · AI/데이터', kind: '신입 · 정규직',
    place: '서울 영등포구', deadline: '2026-09-18T15:00:00+09:00',
    deadlineLabel: '09.18 15:00', track: 'AI / 데이터',
    note: 'AI 모델 개발·데이터 엔지니어링 분야의 신입 공채입니다.',
    check: '2027년 1월 입사 가능자. 재학생은 2027년 2월 졸업 가능 여부를 확인하세요.',
    url: 'https://www.hanwhain.com/web/apply/notification/list.do',
    source: '한화 공식 채용', initial: 'HW', color: 'orange',
    verifiedAt: '2026-09-08T14:00:00+09:00',
  }],
};

function formatChecked(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '확인 시각 미상';
  return new Intl.DateTimeFormat('ko-KR', {
    timeZone: 'Asia/Seoul', year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', hour12: false,
  }).format(date);
}

export default function JobBoard({
  initialFeed = fallback,
  initialCompanies = [],
  currentUser = null,
  completedJobIds = [],
  signInPath = '/signin-with-chatgpt?return_to=%2F',
  signOutPath = '/signout-with-chatgpt?return_to=%2F',
}: {
  initialFeed?: Feed;
  initialCompanies?: Company[];
  currentUser?: CurrentUser | null;
  completedJobIds?: string[];
  signInPath?: string;
  signOutPath?: string;
}) {
  const [companyQuery, setCompanyQuery] = useState('');
  const [completedJobs, setCompletedJobs] = useState(() => new Set(completedJobIds));
  const [savingJobs, setSavingJobs] = useState(() => new Set<string>());
  const [saveError, setSaveError] = useState('');
  const feed = initialFeed;
  const companies = initialCompanies;
  const live = false;

  const jobs = useMemo(() => [...feed.jobs].sort(
    (a, b) => (a.deadline ? new Date(a.deadline).getTime() : Infinity) - (b.deadline ? new Date(b.deadline).getTime() : Infinity),
  ), [feed.jobs]);
  const jobGroups = useMemo(() => {
    const grouped = new Map<string, Job[]>();
    for (const job of jobs) grouped.set(job.company, [...(grouped.get(job.company) ?? []), job]);
    return [...grouped.entries()].map(([company, companyJobs]) => ({
      company,
      jobs: companyJobs,
      first: companyJobs[0],
    }));
  }, [jobs]);
  const visibleCompanies = useMemo(() => {
    const query = companyQuery.trim().toLowerCase();
    return companies.filter((company) => !query || `${company.name} ${company.group} ${company.category}`.toLowerCase().includes(query));
  }, [companies, companyQuery]);
  const checked = formatChecked(feed.updatedAt);
  const completedCount = completedJobs.size;

  async function toggleCompleted(jobId: string, completed: boolean) {
    const previous = new Set(completedJobs);
    const next = new Set(previous);
    if (completed) next.add(jobId); else next.delete(jobId);
    setCompletedJobs(next);
    setSavingJobs((value) => new Set(value).add(jobId));
    setSaveError('');

    try {
      const response = await fetch('/api/applications', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ jobId, completed }),
      });
      if (!response.ok) throw new Error('save failed');
    } catch {
      setCompletedJobs(previous);
      setSaveError('지원 상태를 저장하지 못했습니다. 잠시 후 다시 시도해 주세요.');
    } finally {
      setSavingJobs((value) => {
        const remaining = new Set(value);
        remaining.delete(jobId);
        return remaining;
      });
    }
  }

  return <>
    <header className="topbar">
      <a className="brand" href="#"><Database size={24}/>DATA <span>NEXT</span></a>
      <span className="edition">SSAFY DATA CLASS　 /　 CAREER COLLECTION</span>
      {currentUser ? <div className="account-area"><span className="account-name">{currentUser.displayName}<small>지원 완료 {completedCount}/{jobs.length}</small></span><a className="account-action" href={signOutPath} target="_top">로그아웃</a></div>
        : <a className="login-button" href={signInPath} target="_top">ChatGPT로 로그인</a>}
    </header>
    <main>
      <section className="intro">
        <div><div className="eyebrow">●　싸피 데이터반을 위한 채용 노트</div>
          <h1>우리의 다음 커리어,<br/><span>데이터에서 시작.</span></h1>
          <p>데이터와 조금이라도 맞닿은 대기업 공고를 넓게 모읍니다.<br className="mobile"/> 분석·AI·SW·클라우드·디지털·리서치까지 먼저 보여드립니다.</p>
        </div>
        <div className="date-panel"><span>LAST CHECKED</span><strong>{checked.slice(0, 10)}</strong><p>{checked.slice(11)} · 한국 시간</p></div>
      </section>
      <div className="scope">{live ? <RefreshCw size={18}/> : <CheckCircle2 size={18}/>}<p>
        <b>{live ? '원격 데이터 동기화' : '저장된 최신 데이터'}</b>
        {companies.length || '80+'}개 대기업·주요 테크 기업의 신입·인턴·주니어 공고를 폭넓게 확인합니다. 지원자격이 불명확한 공고도 관련성이 있으면 표시합니다.
      </p></div>
      <div className="content"><section>
        <div className="section-heading"><h2>지원 검토할 기업 <span>{jobGroups.length.toString().padStart(2, '0')}</span></h2><span>총 {jobs.length}개 직무 · 마감일 빠른 순</span></div>
        {saveError && <div className="save-error" role="alert">{saveError}</div>}
        {jobs.length === 0 ? <div className="empty-job">현재 조건이 확인된 모집 공고가 없습니다. 다음 수집에서 다시 확인합니다.</div> : jobGroups.map((group) => <details className="company-jobs" key={group.company}>
          <summary>
            <span className={`monogram ${group.first.color}`}>{group.first.initial}</span>
            <span className="company group-company">{group.company}<small>{group.jobs.length}개 직무{currentUser ? ` · 지원 완료 ${group.jobs.filter((job) => completedJobs.has(job.id)).length}개` : ''} · 눌러서 상세 공고 보기</small></span>
            <span className="group-summary-meta"><span className="deadline">{group.first.deadlineLabel}{group.first.deadline ? ' 마감' : ''}</span><ChevronDown className="group-chevron" size={20}/></span>
          </summary>
          <div className="company-job-list">{group.jobs.map((job) => <article className="job-role" key={job.id}>
            <div className="role-heading"><div className="job-title"><h3>{job.title}</h3><span className="tag">{job.track}</span></div><div className="role-actions"><span className="role-deadline">{job.deadlineLabel}{job.deadline ? ' 마감' : ''}</span>{currentUser ? <label className={`apply-checkbox ${completedJobs.has(job.id) ? 'checked' : ''}`}><input type="checkbox" checked={completedJobs.has(job.id)} disabled={savingJobs.has(job.id)} onChange={(event) => toggleCompleted(job.id, event.target.checked)}/><span>{savingJobs.has(job.id) ? '저장 중' : '지원 완료'}</span></label> : <a className="apply-login" href={signInPath} target="_top">로그인 후 체크</a>}</div></div>
            <div className="role-meta">{job.kind} · {job.place}</div>
            <p>{job.note}</p><div className="job-bottom"><span>{job.check}</span><a href={job.url} target="_blank" rel="noopener noreferrer">공고 원문 <ArrowUpRight size={17}/></a></div>
            <div className="source">출처: {job.source} · {formatChecked(job.verifiedAt)} 확인</div>
          </article>)}</div>
        </details>)}
      </section><aside>
        <div className="aside-card"><span className="eyebrow">APPLICATION NOTE</span><h2>수업에서 만든 경험을,<br/>지원서의 근거로.</h2><ol>
          <li><b>분석 프로젝트</b><p>문제 정의 → SQL 추출 → 분석 → 제안의 흐름을 한 장으로 정리하세요.</p></li>
          <li><b>데이터 파이프라인</b><p>수집·정제·적재 구조와 오류 처리, 개선 전후 수치를 보여주세요.</p></li>
          <li><b>AI 프로젝트</b><p>기준 모델, 평가 지표, 본인 기여와 실패 실험까지 연결하세요.</p></li>
        </ol><div className="aside-note">지원 준비 제안이며 기업의 필수 요건은 아닙니다.</div></div>
        <div className="schedule"><span>자동 수집 원칙</span><h3>관련되면 먼저,<br/>조건은 카드에 표시.</h3><p>데이터·AI·SW·클라우드·디지털·리서치 연관 공고를 우선 노출하고 지원 조건을 함께 안내합니다.</p></div>
      </aside></div>
      <section className="company-directory">
        <div className="directory-heading"><div><span className="eyebrow">OFFICIAL CAREER LINKS</span><h2>놓치지 않게 직접 보는 기업 <b>{companies.length || '80+'}</b></h2><p>자동 수집에 잡히지 않은 공고도 각 회사의 공식 채용 페이지에서 바로 확인할 수 있습니다.</p></div>
          <label className="company-search"><Search size={17}/><input value={companyQuery} onChange={(event) => setCompanyQuery(event.target.value)} placeholder="기업·그룹·분야 검색" aria-label="기업 검색"/></label>
        </div>
        <div className="company-grid">{visibleCompanies.map((company) => <a className="company-link" href={company.career_home} target="_blank" rel="noopener noreferrer" key={company.name}>
          <Building2 size={17}/><span><b>{company.name}</b><small>{company.group} · {company.category}</small></span><ArrowUpRight size={16}/>
        </a>)}</div>
        {companies.length > 0 && visibleCompanies.length === 0 && <div className="directory-empty">검색 결과가 없습니다.</div>}
      </section>
      <footer><span className="brand">DATA NEXT</span><p>자동화가 매일 오전 9시 17분과 오후 6시 17분(한국 시간)에 공고 원문 재확인을 시도합니다.<br/>접근 실패·조기 마감·변경이 있을 수 있으므로 지원 전 원문을 확인하세요.</p><a href="#">맨 위로 ↑</a></footer>
    </main>
  </>;
}
