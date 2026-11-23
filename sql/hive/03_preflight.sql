-- A duplicate dimension key must stop the batch, never multiply exposures.
SELECT assert_true(COUNT(*)=0) FROM (
 SELECT trim(adgroup_id) AS k,COUNT(*) AS n FROM ${hivevar:ns}_ods.ad_feature
 WHERE batch_id='${hivevar:batch}' GROUP BY trim(adgroup_id)
) keys WHERE n>1 OR k IS NULL OR k='';
SELECT assert_true(COUNT(*)=0) FROM (
 SELECT trim(userid) AS k,COUNT(*) AS n FROM ${hivevar:ns}_ods.user_profile
 WHERE batch_id='${hivevar:batch}' GROUP BY trim(userid)
) keys WHERE n>1 OR k IS NULL OR k='';
-- Empty or partially missing source tables are not a successful full batch.
SELECT assert_true(COUNT(*)>0) FROM ${hivevar:ns}_ods.raw_sample WHERE batch_id='${hivevar:batch}';
SELECT assert_true(COUNT(*)>0) FROM ${hivevar:ns}_ods.ad_feature WHERE batch_id='${hivevar:batch}';
SELECT assert_true(COUNT(*)>0) FROM ${hivevar:ns}_ods.user_profile WHERE batch_id='${hivevar:batch}';
