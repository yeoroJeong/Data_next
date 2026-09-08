import companies from '../automation/companies.json';
import feed from '../jobs.json';
import JobBoard, { type Company, type Feed } from './job-board';

export default function Home() {
  return <JobBoard initialFeed={feed as Feed} initialCompanies={companies as Company[]} />;
}
