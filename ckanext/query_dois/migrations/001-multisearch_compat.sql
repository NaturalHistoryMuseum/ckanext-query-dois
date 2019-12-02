ALTER TABLE query_doi ADD COLUMN query_version text;
ALTER TABLE query_doi ALTER COLUMN requested_version DROP NOT NULL;
