SET hive.execution.engine=tez;
SET hive.tez.container.size=512;
SET hive.tez.java.opts=-Xmx384m;
-- Only for the documented synthetic fixture in validation_pipeline. Never business results.
SELECT assert_true(COUNT(*)=5 AND SUM(click_count)=3 AND COUNT(DISTINCT user_id)=3)
FROM validation_pipeline_dwd.exposure WHERE batch_id='tech_20261122_v1';
SELECT assert_true(COUNT(*)=2) FROM validation_pipeline_dwd.exposure
WHERE batch_id='tech_20261122_v1' AND user_id='1' AND event_ts=1494000000;
SELECT assert_true(COUNT(*)=1) FROM validation_pipeline_dwd.exposure
WHERE batch_id='tech_20261122_v1' AND NOT profile_matched AND NOT ad_matched AND user_id='3';
SELECT assert_true(COUNT(*)=1) FROM validation_pipeline_dwd.exposure
WHERE batch_id='tech_20261122_v1' AND profile_matched AND gender_code IS NULL AND user_id='2';
SELECT assert_true(COUNT(*)=1 AND MIN(reason)='invalid_click_flags')
FROM validation_pipeline_dwd.rejected_exposure WHERE batch_id='tech_20261122_v1';
SELECT assert_true(COUNT(*)=2 AND SUM(impressions)=5 AND SUM(clicks)=3 AND SUM(reached_users)=4)
FROM validation_pipeline_ads.daily_overview WHERE batch_id='tech_20261122_v1';
SELECT assert_true(COUNT(*)=1 AND MIN(impressions)=2 AND MIN(clicks)=0)
FROM validation_pipeline_ads.daily_axis WHERE batch_id='tech_20261122_v1' AND dt='2017-05-06' AND axis='gender' AND axis_value='1';
-- User 1 has two non-clicks on May 6.
SELECT assert_true(COUNT(*)=24 AND COUNT(DISTINCT hour_key)=24 AND MIN(hour_key)=0 AND MAX(hour_key)=23)
FROM validation_pipeline_dim.hour;
SELECT assert_true(COUNT(*)=2 AND MIN(weekday_monday_1)=6 AND MAX(weekday_monday_1)=7)
FROM validation_pipeline_dim.calendar WHERE batch_id='tech_20261122_v1';
SELECT assert_true(COUNT(*)=2) FROM validation_pipeline_dim.resource WHERE batch_id='tech_20261122_v1';
SELECT assert_true(COUNT(*)=0) FROM (
 SELECT dt,axis FROM validation_pipeline_ads.daily_axis WHERE batch_id='tech_20261122_v1'
 GROUP BY dt,axis HAVING abs(SUM(impression_share)-1.0)>0.00000001 OR abs(SUM(click_share)-1.0)>0.00000001
) invalid_contributions;
SELECT 'TECHNICAL_FIXTURE_ASSERTIONS_PASS' AS validation_result;
