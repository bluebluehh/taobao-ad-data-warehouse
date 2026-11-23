-- Expected CSV headers come from the previous prototype. Verify against real files before loading.
-- All business fields remain STRING in ODS; line numbers are attached by the staging loader.
CREATE DATABASE IF NOT EXISTS ${hivevar:ns}_ods LOCATION '/warehouse/${hivevar:ns}/ods';
CREATE DATABASE IF NOT EXISTS ${hivevar:ns}_dim LOCATION '/warehouse/${hivevar:ns}/dim';
CREATE DATABASE IF NOT EXISTS ${hivevar:ns}_dwd LOCATION '/warehouse/${hivevar:ns}/dwd';
CREATE DATABASE IF NOT EXISTS ${hivevar:ns}_dws LOCATION '/warehouse/${hivevar:ns}/dws';
CREATE DATABASE IF NOT EXISTS ${hivevar:ns}_ads LOCATION '/warehouse/${hivevar:ns}/ads';
CREATE EXTERNAL TABLE IF NOT EXISTS ${hivevar:ns}_ods.raw_sample (
 source_file STRING, source_line BIGINT,
 user_id STRING, time_stamp STRING, adgroup_id STRING, pid STRING, nonclk STRING, clk STRING
) PARTITIONED BY (batch_id STRING)
ROW FORMAT DELIMITED FIELDS TERMINATED BY '\t'
STORED AS TEXTFILE LOCATION '/warehouse/${hivevar:ns}/ods/raw_sample'
TBLPROPERTIES ('external.table.purge'='false');
CREATE EXTERNAL TABLE IF NOT EXISTS ${hivevar:ns}_ods.ad_feature (
 source_file STRING, source_line BIGINT,
 adgroup_id STRING, cate_id STRING, campaign_id STRING, customer STRING, brand STRING, price STRING
) PARTITIONED BY (batch_id STRING)
ROW FORMAT DELIMITED FIELDS TERMINATED BY '\t'
STORED AS TEXTFILE LOCATION '/warehouse/${hivevar:ns}/ods/ad_feature'
TBLPROPERTIES ('external.table.purge'='false');
CREATE EXTERNAL TABLE IF NOT EXISTS ${hivevar:ns}_ods.user_profile (
 source_file STRING, source_line BIGINT,
 userid STRING, cms_segid STRING, cms_group_id STRING, final_gender_code STRING,
 age_level STRING, pvalue_level STRING, shopping_level STRING, occupation STRING, new_user_class_level STRING
) PARTITIONED BY (batch_id STRING)
ROW FORMAT DELIMITED FIELDS TERMINATED BY '\t'
STORED AS TEXTFILE LOCATION '/warehouse/${hivevar:ns}/ods/user_profile'
TBLPROPERTIES ('external.table.purge'='false');
SHOW TABLES IN ${hivevar:ns}_ods;
DESCRIBE ${hivevar:ns}_ods.raw_sample;
