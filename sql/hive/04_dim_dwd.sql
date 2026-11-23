SET hive.local.time.zone=Asia/Shanghai;
SET hive.exec.dynamic.partition=true;
SET hive.exec.dynamic.partition.mode=nonstrict;
SET hive.auto.convert.join=false;
INSERT OVERWRITE TABLE ${hivevar:ns}_dim.ad PARTITION(batch_id='${hivevar:batch}')
SELECT trim(adgroup_id), nullif(trim(cate_id),''), nullif(trim(campaign_id),''),
 nullif(trim(customer),''), nullif(trim(brand),''), CAST(nullif(trim(price),'') AS DECIMAL(18,4)), source_file, source_line
FROM ${hivevar:ns}_ods.ad_feature WHERE batch_id='${hivevar:batch}';
INSERT OVERWRITE TABLE ${hivevar:ns}_dim.user_profile PARTITION(batch_id='${hivevar:batch}')
SELECT trim(userid), nullif(trim(final_gender_code),''), nullif(trim(age_level),''),
 nullif(trim(shopping_level),''), nullif(trim(pvalue_level),''), nullif(trim(cms_segid),''),
 nullif(trim(cms_group_id),''), nullif(trim(occupation),''), nullif(trim(new_user_class_level),''), source_file, source_line
FROM ${hivevar:ns}_ods.user_profile WHERE batch_id='${hivevar:batch}';
-- This temporary table classifies once and preserves every source row, including duplicates.
CREATE TEMPORARY TABLE classified STORED AS ORC AS
SELECT *, CASE
 WHEN user_id IS NULL OR trim(user_id)='' THEN 'missing_user_id'
 WHEN adgroup_id IS NULL OR trim(adgroup_id)='' THEN 'missing_adgroup_id'
 WHEN pid IS NULL OR trim(pid)='' THEN 'missing_pid'
 WHEN time_stamp IS NULL OR NOT trim(time_stamp) RLIKE '^[0-9]{10}$'
   OR from_unixtime(CAST(trim(time_stamp) AS BIGINT),'yyyy-MM-dd') IS NULL THEN 'invalid_timestamp'
 WHEN from_unixtime(CAST(trim(time_stamp) AS BIGINT),'yyyy-MM-dd')
   NOT BETWEEN '${hivevar:start_date}' AND '${hivevar:end_date}' THEN 'outside_business_period'
 WHEN clk IS NULL OR nonclk IS NULL OR trim(clk) NOT IN ('0','1') OR trim(nonclk) NOT IN ('0','1')
   OR CAST(trim(clk) AS INT)+CAST(trim(nonclk) AS INT)<>1 THEN 'invalid_click_flags'
 ELSE NULL END AS reject_reason
FROM ${hivevar:ns}_ods.raw_sample WHERE batch_id='${hivevar:batch}';
INSERT OVERWRITE TABLE ${hivevar:ns}_dwd.rejected_exposure PARTITION(batch_id='${hivevar:batch}')
SELECT source_file, source_line, user_id, time_stamp, adgroup_id, pid, nonclk, clk, reject_reason
FROM classified WHERE reject_reason IS NOT NULL;
INSERT OVERWRITE TABLE ${hivevar:ns}_dwd.exposure PARTITION(batch_id='${hivevar:batch}',dt)
SELECT r.source_file, r.source_line, trim(r.user_id), trim(r.adgroup_id), trim(r.pid),
 CAST(trim(r.time_stamp) AS BIGINT),
 CAST(from_unixtime(CAST(trim(r.time_stamp) AS BIGINT),'HH') AS INT), CAST(trim(r.clk) AS INT),
 u.user_id IS NOT NULL, a.adgroup_id IS NOT NULL,
 u.gender_code, u.age_level, u.shopping_level, u.pvalue_level,
 a.cate_id, a.campaign_id, a.customer_id, a.brand, u.occupation, u.city_level,
 from_unixtime(CAST(trim(r.time_stamp) AS BIGINT),'yyyy-MM-dd')
FROM classified r
LEFT JOIN ${hivevar:ns}_dim.user_profile u ON trim(r.user_id)=u.user_id AND u.batch_id='${hivevar:batch}'
LEFT JOIN ${hivevar:ns}_dim.ad a ON trim(r.adgroup_id)=a.adgroup_id AND a.batch_id='${hivevar:batch}'
WHERE r.reject_reason IS NULL;
INSERT OVERWRITE TABLE ${hivevar:ns}_dim.calendar PARTITION(batch_id='${hivevar:batch}')
SELECT DISTINCT dt,CAST(regexp_replace(dt,'-','') AS INT),year(CAST(dt AS DATE)),
 month(CAST(dt AS DATE)),day(CAST(dt AS DATE)),pmod(datediff(CAST(dt AS DATE),CAST('1970-01-05' AS DATE)),7)+1
FROM ${hivevar:ns}_dwd.exposure WHERE batch_id='${hivevar:batch}';
INSERT OVERWRITE TABLE ${hivevar:ns}_dim.hour
SELECT hour_key,concat(lpad(CAST(hour_key AS STRING),2,'0'),':00')
FROM (SELECT stack(24,0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23) AS hour_key) hours;
INSERT OVERWRITE TABLE ${hivevar:ns}_dim.resource PARTITION(batch_id='${hivevar:batch}')
SELECT DISTINCT pid FROM ${hivevar:ns}_dwd.exposure WHERE batch_id='${hivevar:batch}';
