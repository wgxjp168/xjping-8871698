-- L6 Format Output Service - Initial Schema

CREATE TABLE IF NOT EXISTS l6_format_jobs (
    id              BIGSERIAL PRIMARY KEY,
    format_job_no   VARCHAR(64)  NOT NULL UNIQUE,
    generator_job_no VARCHAR(64) NOT NULL,
    l5_report_no    VARCHAR(64)  NOT NULL,
    user_id         BIGINT       NOT NULL,
    title           VARCHAR(255) NOT NULL,
    client_type     VARCHAR(32)  NOT NULL,
    status          VARCHAR(32)  NOT NULL DEFAULT 'PENDING',
    error_message   TEXT,
    html_url        VARCHAR(512),
    html_size       BIGINT,
    pdf_url         VARCHAR(512),
    pdf_size        BIGINT,
    excel_url       VARCHAR(512),
    excel_size      BIGINT,
    expires_at      TIMESTAMPTZ,
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_l6_format_jobs_l5_report_no  ON l6_format_jobs(l5_report_no);
CREATE INDEX idx_l6_format_jobs_user_id        ON l6_format_jobs(user_id);
CREATE INDEX idx_l6_format_jobs_status         ON l6_format_jobs(status);

CREATE TABLE IF NOT EXISTS l6_format_access_log (
    id              BIGSERIAL PRIMARY KEY,
    format_job_id   BIGINT       NOT NULL REFERENCES l6_format_jobs(id),
    user_id         BIGINT       NOT NULL,
    format          VARCHAR(16)  NOT NULL,  -- HTML | PDF | EXCEL | JSON
    ip_address      VARCHAR(64),
    user_agent      TEXT,
    accessed_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_l6_format_access_log_job_id ON l6_format_access_log(format_job_id);

-- Trigger
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_l6_format_jobs_updated_at
    BEFORE UPDATE ON l6_format_jobs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
