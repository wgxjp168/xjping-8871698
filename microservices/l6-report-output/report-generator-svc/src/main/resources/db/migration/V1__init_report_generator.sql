-- L6 Report Generator Service - Initial Schema
-- =============================================

CREATE TABLE IF NOT EXISTS l6_report_jobs (
    id              BIGSERIAL PRIMARY KEY,
    job_no          VARCHAR(64)  NOT NULL UNIQUE,
    l5_report_no    VARCHAR(64)  NOT NULL,
    user_id         BIGINT       NOT NULL,
    report_type     VARCHAR(32)  NOT NULL,  -- B2B | B2C_DEFINED | B2C_UNDEFINED
    business_type   VARCHAR(32)  NOT NULL,  -- PRICE_ANALYSIS | SUPPLIER_EVAL | MARKET_TREND
    brand_id        BIGINT,
    category_id     BIGINT,
    parameters      JSONB,
    status          VARCHAR(32)  NOT NULL DEFAULT 'PENDING',
    retry_count     INT          NOT NULL DEFAULT 0,
    error_message   TEXT,
    result_json     JSONB,
    format_job_id   BIGINT,
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_l6_report_jobs_l5_report_no ON l6_report_jobs(l5_report_no);
CREATE INDEX idx_l6_report_jobs_user_id      ON l6_report_jobs(user_id);
CREATE INDEX idx_l6_report_jobs_status       ON l6_report_jobs(status);
CREATE INDEX idx_l6_report_jobs_created_at   ON l6_report_jobs(created_at);

CREATE TABLE IF NOT EXISTS l6_report_sections (
    id          BIGSERIAL PRIMARY KEY,
    job_id      BIGINT       NOT NULL REFERENCES l6_report_jobs(id) ON DELETE CASCADE,
    section_key VARCHAR(64)  NOT NULL,
    title       VARCHAR(255) NOT NULL,
    content     JSONB,
    charts      JSONB,
    order_index INT          NOT NULL DEFAULT 0,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_l6_report_sections_job_id ON l6_report_sections(job_id);

-- Trigger: auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_l6_report_jobs_updated_at
    BEFORE UPDATE ON l6_report_jobs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
