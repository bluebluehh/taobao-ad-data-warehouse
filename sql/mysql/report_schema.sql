-- Apply only in the intended report database. No DROP, TRUNCATE or source data deletion.
CREATE TABLE IF NOT EXISTS daily_overview (
 impressions BIGINT NOT NULL, clicks BIGINT NOT NULL, ctr DOUBLE NULL,
 reached_users BIGINT NOT NULL, clicked_users BIGINT NOT NULL,
 user_click_ratio DOUBLE NULL, ad_units BIGINT NOT NULL, impressions_per_user DOUBLE NULL,
 unmatched_profiles BIGINT NOT NULL, unmatched_ads BIGINT NOT NULL,
 batch_id VARCHAR(64) NOT NULL, dt DATE NOT NULL,
 PRIMARY KEY(batch_id,dt)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
CREATE TABLE IF NOT EXISTS daily_axis (
 axis VARCHAR(32) NOT NULL, axis_value VARCHAR(255) NOT NULL,
 impressions BIGINT NOT NULL, clicks BIGINT NOT NULL, ctr DOUBLE NULL,
 reached_users BIGINT NOT NULL, clicked_users BIGINT NOT NULL, user_click_ratio DOUBLE NULL,
 ad_units BIGINT NOT NULL, impressions_per_user DOUBLE NULL,
 impression_share DOUBLE NULL, click_share DOUBLE NULL,
 batch_id VARCHAR(64) NOT NULL, dt DATE NOT NULL,
 PRIMARY KEY(batch_id,dt,axis,axis_value)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
-- Readers use this marker to ignore incomplete or failed publications.
CREATE TABLE IF NOT EXISTS published_batches (
 batch_id VARCHAR(64) PRIMARY KEY,
 source_namespace VARCHAR(64) NOT NULL,
 published_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
CREATE OR REPLACE VIEW published_daily_overview AS
 SELECT d.* FROM daily_overview d JOIN published_batches p ON d.batch_id=p.batch_id;
CREATE OR REPLACE VIEW published_daily_axis AS
 SELECT d.* FROM daily_axis d JOIN published_batches p ON d.batch_id=p.batch_id;
CREATE OR REPLACE VIEW published_daily_axis_labeled AS
SELECT d.*,
 CASE
  WHEN axis_value='__unmatched_profile__' THEN '画像未匹配'
  WHEN axis_value='__unmatched_ad__' THEN '广告信息未匹配'
  WHEN axis_value='__missing_attribute__' THEN '属性缺失'
  WHEN axis='gender' AND axis_value='1' THEN '男'
  WHEN axis='gender' AND axis_value='2' THEN '女'
  WHEN axis='shopping' AND axis_value='1' THEN '浅层用户'
  WHEN axis='shopping' AND axis_value='2' THEN '中度用户'
  WHEN axis='shopping' AND axis_value='3' THEN '深度用户'
  WHEN axis='pvalue' AND axis_value='1' THEN '低档'
  WHEN axis='pvalue' AND axis_value='2' THEN '中档'
  WHEN axis='pvalue' AND axis_value='3' THEN '高档'
  WHEN axis='hour' THEN CONCAT(LPAD(axis_value,2,'0'),':00')
  ELSE axis_value END AS group_label
FROM published_daily_axis d;

-- SQL revision 2 quality results; user counts are daily and must not be summed across dates.
CREATE TABLE IF NOT EXISTS daily_quality (
 impressions BIGINT NOT NULL,
 matched_profile_impressions BIGINT NOT NULL,
 reached_users BIGINT NOT NULL,
 matched_profile_users BIGINT NOT NULL,
 matched_ad_impressions BIGINT NOT NULL,
 gender_missing BIGINT NOT NULL,
 age_missing BIGINT NOT NULL,
 shopping_missing BIGINT NOT NULL,
 pvalue_missing BIGINT NOT NULL,
 occupation_missing BIGINT NOT NULL,
 city_missing BIGINT NOT NULL,
 profile_row_coverage DOUBLE NULL,
 profile_user_coverage DOUBLE NULL,
 ad_row_coverage DOUBLE NULL,
 gender_missing_rate DOUBLE NULL,
 age_missing_rate DOUBLE NULL,
 shopping_missing_rate DOUBLE NULL,
 pvalue_missing_rate DOUBLE NULL,
 occupation_missing_rate DOUBLE NULL,
 city_missing_rate DOUBLE NULL,
 batch_id VARCHAR(64) NOT NULL, dt DATE NOT NULL, PRIMARY KEY(batch_id,dt)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
CREATE OR REPLACE VIEW published_daily_quality AS
 SELECT d.* FROM daily_quality d JOIN published_batches p ON d.batch_id=p.batch_id;
CREATE TABLE IF NOT EXISTS analysis_scopes (
 request_id VARCHAR(64) PRIMARY KEY, batch_id VARCHAR(64) NOT NULL,
 source_namespace VARCHAR(64) NOT NULL, start_date DATE NOT NULL, end_date DATE NOT NULL,
 request_json JSON NOT NULL, published_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
CREATE TABLE IF NOT EXISTS analysis_overview (
 request_id VARCHAR(64) NOT NULL,
 impressions BIGINT NOT NULL,
 clicks BIGINT NOT NULL,
 ctr DOUBLE NULL,
 reached_users BIGINT NOT NULL,
 clicked_users BIGINT NOT NULL,
 user_click_ratio DOUBLE NULL,
 ad_units BIGINT NOT NULL,
 impressions_per_user DOUBLE NULL,
 PRIMARY KEY(request_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
CREATE OR REPLACE VIEW published_analysis_overview AS
 SELECT r.* FROM analysis_overview r JOIN analysis_scopes s ON r.request_id=s.request_id;
CREATE TABLE IF NOT EXISTS analysis_quality (
 request_id VARCHAR(64) NOT NULL,
 impressions BIGINT NOT NULL,
 matched_profile_impressions BIGINT NOT NULL,
 reached_users BIGINT NOT NULL,
 matched_profile_users BIGINT NOT NULL,
 matched_ad_impressions BIGINT NOT NULL,
 gender_missing BIGINT NOT NULL,
 age_missing BIGINT NOT NULL,
 shopping_missing BIGINT NOT NULL,
 pvalue_missing BIGINT NOT NULL,
 occupation_missing BIGINT NOT NULL,
 city_missing BIGINT NOT NULL,
 profile_row_coverage DOUBLE NULL,
 profile_user_coverage DOUBLE NULL,
 ad_row_coverage DOUBLE NULL,
 gender_missing_rate DOUBLE NULL,
 age_missing_rate DOUBLE NULL,
 shopping_missing_rate DOUBLE NULL,
 pvalue_missing_rate DOUBLE NULL,
 occupation_missing_rate DOUBLE NULL,
 city_missing_rate DOUBLE NULL,
 PRIMARY KEY(request_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
CREATE OR REPLACE VIEW published_analysis_quality AS
 SELECT r.* FROM analysis_quality r JOIN analysis_scopes s ON r.request_id=s.request_id;
CREATE TABLE IF NOT EXISTS analysis_groups (
 request_id VARCHAR(64) NOT NULL,
 group_key VARCHAR(64) NOT NULL, group_label VARCHAR(1024) NOT NULL, group_values JSON NOT NULL,
 impressions BIGINT NOT NULL,
 clicks BIGINT NOT NULL,
 ctr DOUBLE NULL,
 reached_users BIGINT NOT NULL,
 clicked_users BIGINT NOT NULL,
 user_click_ratio DOUBLE NULL,
 ad_units BIGINT NOT NULL,
 impressions_per_user DOUBLE NULL,
 impression_share DOUBLE NULL,
 click_share DOUBLE NULL,
 PRIMARY KEY(request_id,group_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
CREATE OR REPLACE VIEW published_analysis_groups AS
 SELECT r.* FROM analysis_groups r JOIN analysis_scopes s ON r.request_id=s.request_id;
