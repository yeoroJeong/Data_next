import localFeed from '../jobs.json';
import type { Feed } from '../app/job-board';

const REMOTE_FEED_URL = 'https://raw.githubusercontent.com/yeoroJeong/Data_next/main/jobs.json';

export async function getCurrentFeed(): Promise<Feed> {
  try {
    const response = await fetch(REMOTE_FEED_URL, { cache: 'no-store', signal: AbortSignal.timeout(8000) });
    if (!response.ok) throw new Error(`feed request failed: ${response.status}`);
    const candidate = await response.json() as Partial<Feed>;
    if (!candidate || typeof candidate.updatedAt !== 'string' || !Array.isArray(candidate.jobs) || !candidate.jobs.every(job =>
      typeof job.id === 'string' && typeof job.company === 'string' && typeof job.title === 'string' &&
      typeof job.url === 'string' && /^https?:\/\//.test(job.url) && typeof job.deadlineLabel === 'string'
    )) {
      throw new Error('invalid feed');
    }
    return { ...candidate, delivery: 'remote' } as Feed;
  } catch {
    return { ...localFeed, delivery: 'fallback' } as Feed;
  }
}
