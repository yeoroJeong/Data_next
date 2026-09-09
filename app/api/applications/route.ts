import { getChatGPTUser } from '../../chatgpt-auth';
import { setJobCompleted } from '../../../db';
import { getCurrentFeed } from '../../../lib/feed';

export const dynamic = 'force-dynamic';

export async function POST(request: Request) {
  const user = await getChatGPTUser();
  if (!user) return Response.json({ error: '로그인이 필요합니다.' }, { status: 401 });

  const contentType = request.headers.get('content-type') ?? '';
  if (!contentType.includes('application/json')) {
    return Response.json({ error: '잘못된 요청입니다.' }, { status: 415 });
  }

  let body: { jobId?: unknown; completed?: unknown };
  try {
    body = await request.json();
  } catch {
    return Response.json({ error: '잘못된 요청입니다.' }, { status: 400 });
  }

  const feed = await getCurrentFeed();
  const validJobIds = new Set(feed.jobs.map((job) => job.id));
  if (typeof body.jobId !== 'string' || !validJobIds.has(body.jobId) || typeof body.completed !== 'boolean') {
    return Response.json({ error: '유효하지 않은 공고입니다.' }, { status: 400 });
  }

  await setJobCompleted(user.userId, body.jobId, body.completed);
  return Response.json({ jobId: body.jobId, completed: body.completed });
}
