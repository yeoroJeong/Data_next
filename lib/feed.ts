import localFeed from '../jobs.json';
import type { Feed } from '../app/job-board';

const REMOTE_FEED_URL = 'https://raw.githubusercontent.com/yeoroJeong/Data_next/main/jobs.json';

export async function getCurrentFeed(): Promise<Feed> {
  try {
    const response = await fetch(REMOTE_FEED_URL, { cache: 'no-store' });
    if (!response.ok) throw new Error(`feed request failed: ${response.status}`);
    const candidate = await response.json() as Partial<Feed>;
    if (!candidate || typeof candidate.updatedAt !== 'string' || !Array.isArray(candidate.jobs)) {
      throw new Error('invalid feed');
    }
    return candidate as Feed;
  } catch {
    return localFeed as Feed;
  }
}
