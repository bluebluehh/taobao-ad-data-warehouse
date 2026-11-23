-- Every snapshot is isolated by batch_id; these are not real-time increments.
CREATE EXTERNAL TABLE IF NOT EXISTS ${hivevar:ns}_dim.ad (
 adgroup_id STRING, cate_id STRING, campaign_id STRING, customer_id STRING,
 brand STRING, price DECIMAL(18,4), source_file STRING, source_line BIGINT
) PARTITIONED BY(batch_id STRING) STORED AS ORC
LOCATION '/warehouse/${hivevar:ns}/dim/ad' TBLPROPERTIES('external.table.purge'='false');
CREATE EXTERNAL TABLE IF NOT EXISTS ${hivevar:ns}_dim.user_profile (
 user_id STRING, gender_code STRING, age_level STRING, shopping_level STRING,
 pvalue_level STRING, cms_segid STRING, cms_group_id STRING, occupation STRING,
 city_level STRING, source_file STRING, source_line BIGINT
) PARTITIONED BY(batch_id STRING) STORED AS ORC
LOCATION '/warehouse/${hivevar:ns}/dim/user_profile' TBLPROPERTIES('external.table.purge'='false');
CREATE EXTERNAL TABLE IF NOT EXISTS ${hivevar:ns}_dwd.exposure (
 source_file STRING, source_line BIGINT, user_id STRING, adgroup_id STRING,
 pid STRING, event_ts BIGINT, event_hour INT, click_count INT,
 profile_matched BOOLEAN, ad_matched BOOLEAN,
 gender_code STRING, age_level STRING, shopping_level STRING, pvalue_level STRING,
 cate_id STRING, campaign_id STRING, customer_id STRING, brand STRING,
 occupation STRING, city_level STRING
) PARTITIONED BY(batch_id STRING, dt STRING) STORED AS ORC
LOCATION '/warehouse/${hivevar:ns}/dwd/exposure' TBLPROPERTIES('external.table.purge'='false');
CREATE EXTERNAL TABLE IF NOT EXISTS ${hivevar:ns}_dwd.rejected_exposure (
 source_file STRING, source_line BIGINT, user_id STRING, time_stamp STRING,
 adgroup_id STRING, pid STRING, nonclk STRING, clk STRING, reason STRING
) PARTITIONED BY(batch_id STRING) STORED AS ORC
LOCATION '/warehouse/${hivevar:ns}/dwd/rejected_exposure' TBLPROPERTIES('external.table.purge'='false');
CREATE EXTERNAL TABLE IF NOT EXISTS ${hivevar:ns}_dws.daily_stats (
 impressions BIGINT, clicks BIGINT, reached_users BIGINT, clicked_users BIGINT,
 ad_units BIGINT, unmatched_profiles BIGINT, unmatched_ads BIGINT
) PARTITIONED BY(batch_id STRING, dt STRING) STORED AS ORC
LOCATION '/warehouse/${hivevar:ns}/dws/daily_stats' TBLPROPERTIES('external.table.purge'='false');
CREATE EXTERNAL TABLE IF NOT EXISTS ${hivevar:ns}_dws.axis_stats (
 axis STRING, axis_value STRING, impressions BIGINT, clicks BIGINT,
 reached_users BIGINT, clicked_users BIGINT, ad_units BIGINT
) PARTITIONED BY(batch_id STRING, dt STRING) STORED AS ORC
LOCATION '/warehouse/${hivevar:ns}/dws/axis_stats' TBLPROPERTIES('external.table.purge'='false');
CREATE EXTERNAL TABLE IF NOT EXISTS ${hivevar:ns}_ads.daily_overview (
 impressions BIGINT, clicks BIGINT, ctr DOUBLE, reached_users BIGINT,
 clicked_users BIGINT, user_click_ratio DOUBLE, ad_units BIGINT,
 impressions_per_user DOUBLE, unmatched_profiles BIGINT, unmatched_ads BIGINT
) PARTITIONED BY(batch_id STRING, dt STRING) STORED AS ORC
LOCATION '/warehouse/${hivevar:ns}/ads/daily_overview' TBLPROPERTIES('external.table.purge'='false');
CREATE EXTERNAL TABLE IF NOT EXISTS ${hivevar:ns}_ads.daily_axis (
 axis STRING, axis_value STRING, impressions BIGINT, clicks BIGINT, ctr DOUBLE,
 reached_users BIGINT, clicked_users BIGINT, user_click_ratio DOUBLE,
 ad_units BIGINT, impressions_per_user DOUBLE,
 impression_share DOUBLE, click_share DOUBLE
) PARTITIONED BY(batch_id STRING, dt STRING) STORED AS ORC
LOCATION '/warehouse/${hivevar:ns}/ads/daily_axis' TBLPROPERTIES('external.table.purge'='false');
CREATE EXTERNAL TABLE IF NOT EXISTS ${hivevar:ns}_dim.calendar (
 dt STRING, date_key INT, year_num INT, month_num INT, day_num INT, weekday_monday_1 INT
) PARTITIONED BY(batch_id STRING) STORED AS ORC
LOCATION '/warehouse/${hivevar:ns}/dim/calendar' TBLPROPERTIES('external.table.purge'='false');
CREATE EXTERNAL TABLE IF NOT EXISTS ${hivevar:ns}_dim.hour (
 hour_key INT, hour_label STRING
) STORED AS ORC LOCATION '/warehouse/${hivevar:ns}/dim/hour'
TBLPROPERTIES('external.table.purge'='false');
CREATE EXTERNAL TABLE IF NOT EXISTS ${hivevar:ns}_dim.resource (
 pid STRING
) PARTITIONED BY(batch_id STRING) STORED AS ORC
LOCATION '/warehouse/${hivevar:ns}/dim/resource' TBLPROPERTIES('external.table.purge'='false');

CREATE EXTERNAL TABLE IF NOT EXISTS ${hivevar:ns}_dws.daily_quality (
 impressions BIGINT, matched_profile_impressions BIGINT, reached_users BIGINT,
 matched_profile_users BIGINT, matched_ad_impressions BIGINT,
 gender_missing BIGINT, age_missing BIGINT, shopping_missing BIGINT,
 pvalue_missing BIGINT, occupation_missing BIGINT, city_missing BIGINT
) PARTITIONED BY(batch_id STRING, dt STRING) STORED AS ORC
LOCATION '/warehouse/${hivevar:ns}/dws/daily_quality' TBLPROPERTIES('external.table.purge'='false');
CREATE EXTERNAL TABLE IF NOT EXISTS ${hivevar:ns}_ads.daily_quality (
 impressions BIGINT, matched_profile_impressions BIGINT, reached_users BIGINT,
 matched_profile_users BIGINT, matched_ad_impressions BIGINT,
 gender_missing BIGINT, age_missing BIGINT, shopping_missing BIGINT,
 pvalue_missing BIGINT, occupation_missing BIGINT, city_missing BIGINT,
 profile_row_coverage DOUBLE, profile_user_coverage DOUBLE, ad_row_coverage DOUBLE,
 gender_missing_rate DOUBLE, age_missing_rate DOUBLE, shopping_missing_rate DOUBLE,
 pvalue_missing_rate DOUBLE, occupation_missing_rate DOUBLE, city_missing_rate DOUBLE
) PARTITIONED BY(batch_id STRING, dt STRING) STORED AS ORC
LOCATION '/warehouse/${hivevar:ns}/ads/daily_quality' TBLPROPERTIES('external.table.purge'='false');
