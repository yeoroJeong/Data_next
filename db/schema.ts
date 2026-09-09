import { sql } from 'drizzle-orm';
import { primaryKey, sqliteTable, text } from 'drizzle-orm/sqlite-core';

export const jobApplications = sqliteTable('job_applications', {
  userId: text('user_id').notNull(),
  jobId: text('job_id').notNull(),
  completedAt: text('completed_at').notNull().default(sql`CURRENT_TIMESTAMP`),
}, (table) => [primaryKey({ columns: [table.userId, table.jobId] })]);
