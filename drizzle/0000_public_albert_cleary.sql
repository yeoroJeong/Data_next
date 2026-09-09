CREATE TABLE `job_applications` (
	`user_id` text NOT NULL,
	`job_id` text NOT NULL,
	`completed_at` text DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY(`user_id`, `job_id`)
);
