-- Isolated synthetic negative test. EXPECTED result: assert_true failure; no business tables are modified.
SET hive.execution.engine=tez;
SET hive.tez.container.size=512;
SET hive.tez.java.opts=-Xmx384m;
CREATE TEMPORARY TABLE duplicate_ad_keys STORED AS ORC AS
SELECT adgroup_id,'negative_test' AS batch_id FROM (SELECT stack(2,'42','42') AS adgroup_id) seed;
-- A duplicate dimension key must stop the batch, never multiply exposures.
SELECT assert_true(COUNT(*)=0) FROM (
 SELECT trim(adgroup_id) AS k,COUNT(*) AS n FROM duplicate_ad_keys
 WHERE batch_id='negative_test' GROUP BY trim(adgroup_id)
) keys WHERE n>1 OR k IS NULL OR k='';
