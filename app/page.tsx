import companies from '../automation/companies.json';
import JobBoard, { type Company, type Feed } from './job-board';
import { chatGPTSignInPath, chatGPTSignOutPath, getChatGPTUser } from './chatgpt-auth';
import { getCompletedJobIds } from '../db';
import { getCurrentFeed } from '../lib/feed';

export const dynamic = 'force-dynamic';

export default async function Home() {
  const user = await getChatGPTUser();
  const feed = await getCurrentFeed();
  const currentJobIds = new Set(feed.jobs.map((job) => job.id));
  const completedJobIds = user
    ? (await getCompletedJobIds(user.userId)).filter((jobId) => currentJobIds.has(jobId))
    : [];

  return <JobBoard
    initialFeed={feed as Feed}
    initialCompanies={companies as Company[]}
    currentUser={user ? { displayName: user.displayName } : null}
    completedJobIds={completedJobIds}
    signInPath={chatGPTSignInPath('/')}
    signOutPath={chatGPTSignOutPath('/')}
  />;
}
