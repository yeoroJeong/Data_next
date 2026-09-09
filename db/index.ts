import { env } from 'cloudflare:workers';

export function getDb(): D1Database {
  if (!env.DB) throw new Error('Cloudflare D1 binding `DB` is unavailable.');
  return env.DB;
}

export async function getCompletedJobIds(userId: string): Promise<string[]> {
  const result = await getDb()
    .prepare('SELECT job_id FROM job_applications WHERE user_id = ? ORDER BY completed_at DESC')
    .bind(userId)
    .all<{ job_id: string }>();
  return result.results.map((row) => row.job_id);
}

export async function setJobCompleted(userId: string, jobId: string, completed: boolean): Promise<void> {
  if (completed) {
    await getDb()
      .prepare(`INSERT INTO job_applications (user_id, job_id, completed_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(user_id, job_id) DO UPDATE SET completed_at = CURRENT_TIMESTAMP`)
      .bind(userId, jobId)
      .run();
    return;
  }

  await getDb()
    .prepare('DELETE FROM job_applications WHERE user_id = ? AND job_id = ?')
    .bind(userId, jobId)
    .run();
}
