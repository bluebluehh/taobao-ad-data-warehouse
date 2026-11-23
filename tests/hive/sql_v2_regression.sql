SET hive.execution.engine=tez;
SET hive.tez.container.size=512;
SET hive.tez.java.opts=-Xmx384m;
SELECT assert_true(COUNT(*)=9 AND SUM(click_count)=4 AND COUNT(DISTINCT user_id)=4) FROM ${hivevar:ns}_dwd.exposure WHERE batch_id='${hivevar:batch}';
SELECT assert_true(COUNT(*)=8) FROM ${hivevar:ns}_dwd.rejected_exposure WHERE batch_id='${hivevar:batch}';
SELECT assert_true(COUNT(*)=2) FROM ${hivevar:ns}_dwd.rejected_exposure WHERE batch_id='${hivevar:batch}' AND reason='outside_business_period';
SELECT assert_true(COUNT(*)=4) FROM ${hivevar:ns}_dwd.exposure WHERE batch_id='${hivevar:batch}' AND user_id='1' AND occupation='0' AND city_level='1';
CREATE TEMPORARY TABLE r_full_overview STORED AS ORC AS
-- Recompute exact user counts from DWD for the WHOLE selected period.
-- Never sum daily reached_users/clicked_users/ad_units from ADS.
SELECT COUNT(*) impressions,COALESCE(SUM(click_count),0) clicks,
 CAST(SUM(click_count) AS DOUBLE)/nullif(COUNT(*),0) ctr,
 COUNT(DISTINCT user_id) reached_users,
 COUNT(DISTINCT CASE WHEN click_count=1 THEN user_id END) clicked_users,
 COUNT(DISTINCT adgroup_id) ad_units,
 CAST(COUNT(DISTINCT CASE WHEN click_count=1 THEN user_id END) AS DOUBLE)/nullif(COUNT(DISTINCT user_id),0) user_click_ratio,
 CAST(COUNT(*) AS DOUBLE)/nullif(COUNT(DISTINCT user_id),0) impressions_per_user
FROM ${hivevar:ns}_dwd.exposure
WHERE batch_id='${hivevar:batch}' AND dt BETWEEN '2017-05-06' AND '2017-05-13';
CREATE TEMPORARY TABLE r_full_quality STORED AS ORC AS
-- Q01-Q04 are computed BEFORE portrait filters; all counts are zero for an empty scope.
WITH counted AS (
 SELECT COUNT(*) AS impressions,
 COALESCE(SUM(CASE WHEN profile_matched THEN 1 ELSE 0 END),0) AS matched_profile_impressions,
 COUNT(DISTINCT user_id) AS reached_users,
 COUNT(DISTINCT CASE WHEN profile_matched THEN user_id END) AS matched_profile_users,
 COALESCE(SUM(CASE WHEN ad_matched THEN 1 ELSE 0 END),0) AS matched_ad_impressions,
 COALESCE(SUM(CASE WHEN profile_matched AND gender_code IS NULL THEN 1 ELSE 0 END),0) AS gender_missing,
 COALESCE(SUM(CASE WHEN profile_matched AND age_level IS NULL THEN 1 ELSE 0 END),0) AS age_missing,
 COALESCE(SUM(CASE WHEN profile_matched AND shopping_level IS NULL THEN 1 ELSE 0 END),0) AS shopping_missing,
 COALESCE(SUM(CASE WHEN profile_matched AND pvalue_level IS NULL THEN 1 ELSE 0 END),0) AS pvalue_missing,
 COALESCE(SUM(CASE WHEN profile_matched AND occupation IS NULL THEN 1 ELSE 0 END),0) AS occupation_missing,
 COALESCE(SUM(CASE WHEN profile_matched AND city_level IS NULL THEN 1 ELSE 0 END),0) AS city_missing
 FROM ${hivevar:ns}_dwd.exposure
 WHERE batch_id='${hivevar:batch}' AND dt BETWEEN '2017-05-06' AND '2017-05-13'
 
)
SELECT impressions,matched_profile_impressions,reached_users,matched_profile_users,matched_ad_impressions,gender_missing,age_missing,shopping_missing,pvalue_missing,occupation_missing,city_missing,
 CAST(matched_profile_impressions AS DOUBLE)/nullif(impressions,0) AS profile_row_coverage,
 CAST(matched_profile_users AS DOUBLE)/nullif(reached_users,0) AS profile_user_coverage,
 CAST(matched_ad_impressions AS DOUBLE)/nullif(impressions,0) AS ad_row_coverage,
 CAST(gender_missing AS DOUBLE)/nullif(matched_profile_impressions,0) AS gender_missing_rate,
 CAST(age_missing AS DOUBLE)/nullif(matched_profile_impressions,0) AS age_missing_rate,
 CAST(shopping_missing AS DOUBLE)/nullif(matched_profile_impressions,0) AS shopping_missing_rate,
 CAST(pvalue_missing AS DOUBLE)/nullif(matched_profile_impressions,0) AS pvalue_missing_rate,
 CAST(occupation_missing AS DOUBLE)/nullif(matched_profile_impressions,0) AS occupation_missing_rate,
 CAST(city_missing AS DOUBLE)/nullif(matched_profile_impressions,0) AS city_missing_rate FROM counted;
CREATE TEMPORARY TABLE r_full_groups STORED AS ORC AS
-- Render through query_metrics.py. Denominators precede threshold and Top N.
WITH grouped AS (
 SELECT CASE WHEN NOT profile_matched THEN '__unmatched_profile__' ELSE coalesce(occupation,'__missing_attribute__') END AS group_value_1,CASE WHEN NOT profile_matched THEN '__unmatched_profile__' ELSE coalesce(city_level,'__missing_attribute__') END AS group_value_2,
 COUNT(*) impressions,SUM(click_count) clicks,COUNT(DISTINCT user_id) reached_users,
 COUNT(DISTINCT CASE WHEN click_count=1 THEN user_id END) clicked_users,
 COUNT(DISTINCT adgroup_id) ad_units
 FROM ${hivevar:ns}_dwd.exposure
 WHERE batch_id='${hivevar:batch}' AND dt BETWEEN '2017-05-06' AND '2017-05-13'
 
 GROUP BY CASE WHEN NOT profile_matched THEN '__unmatched_profile__' ELSE coalesce(occupation,'__missing_attribute__') END,CASE WHEN NOT profile_matched THEN '__unmatched_profile__' ELSE coalesce(city_level,'__missing_attribute__') END
), scored AS (
 SELECT *,CAST(clicks AS DOUBLE)/nullif(impressions,0) ctr,
 CAST(clicked_users AS DOUBLE)/nullif(reached_users,0) user_click_ratio,
 CAST(impressions AS DOUBLE)/nullif(reached_users,0) impressions_per_user,
 CAST(impressions AS DOUBLE)/nullif(SUM(impressions) OVER(),0) impression_share,
 CAST(clicks AS DOUBLE)/nullif(SUM(clicks) OVER(),0) click_share
 FROM grouped
)
SELECT group_value_1,group_value_2,impressions,clicks,ctr,reached_users,clicked_users,
 user_click_ratio,ad_units,impressions_per_user,impression_share,click_share
FROM scored WHERE impressions>=0
ORDER BY clicks DESC,impressions DESC,group_value_1,group_value_2 LIMIT 1;
SELECT assert_true(COUNT(*)=1) FROM r_full_overview;
SELECT assert_true(coalesce((impressions=9 AND clicks=4 AND reached_users=4 AND clicked_users=3 AND ad_units=3 AND abs(ctr-4.0/9)<1e-10),false)) FROM r_full_overview;
SELECT assert_true(COUNT(*)=1) FROM r_full_quality;
SELECT assert_true(coalesce((impressions=9 AND matched_profile_impressions=7 AND matched_profile_users=2 AND abs(profile_row_coverage-7.0/9)<1e-10 AND profile_user_coverage=0.5 AND gender_missing=3 AND city_missing=3 AND abs(gender_missing_rate-3.0/7)<1e-10 AND occupation_missing_rate=0),false)) FROM r_full_quality;
SELECT assert_true(COUNT(*)=1) FROM r_full_groups;
SELECT assert_true(coalesce((group_value_1='1' AND group_value_2='__missing_attribute__' AND impressions=3 AND clicks=2 AND abs(impression_share-1.0/3)<1e-10 AND click_share=0.5),false)) FROM r_full_groups;
CREATE TEMPORARY TABLE r_empty_overview STORED AS ORC AS
-- Recompute exact user counts from DWD for the WHOLE selected period.
-- Never sum daily reached_users/clicked_users/ad_units from ADS.
SELECT COUNT(*) impressions,COALESCE(SUM(click_count),0) clicks,
 CAST(SUM(click_count) AS DOUBLE)/nullif(COUNT(*),0) ctr,
 COUNT(DISTINCT user_id) reached_users,
 COUNT(DISTINCT CASE WHEN click_count=1 THEN user_id END) clicked_users,
 COUNT(DISTINCT adgroup_id) ad_units,
 CAST(COUNT(DISTINCT CASE WHEN click_count=1 THEN user_id END) AS DOUBLE)/nullif(COUNT(DISTINCT user_id),0) user_click_ratio,
 CAST(COUNT(*) AS DOUBLE)/nullif(COUNT(DISTINCT user_id),0) impressions_per_user
FROM ${hivevar:ns}_dwd.exposure
WHERE batch_id='${hivevar:batch}' AND dt BETWEEN '2018-01-01' AND '2018-01-02';
CREATE TEMPORARY TABLE r_empty_quality STORED AS ORC AS
-- Q01-Q04 are computed BEFORE portrait filters; all counts are zero for an empty scope.
WITH counted AS (
 SELECT COUNT(*) AS impressions,
 COALESCE(SUM(CASE WHEN profile_matched THEN 1 ELSE 0 END),0) AS matched_profile_impressions,
 COUNT(DISTINCT user_id) AS reached_users,
 COUNT(DISTINCT CASE WHEN profile_matched THEN user_id END) AS matched_profile_users,
 COALESCE(SUM(CASE WHEN ad_matched THEN 1 ELSE 0 END),0) AS matched_ad_impressions,
 COALESCE(SUM(CASE WHEN profile_matched AND gender_code IS NULL THEN 1 ELSE 0 END),0) AS gender_missing,
 COALESCE(SUM(CASE WHEN profile_matched AND age_level IS NULL THEN 1 ELSE 0 END),0) AS age_missing,
 COALESCE(SUM(CASE WHEN profile_matched AND shopping_level IS NULL THEN 1 ELSE 0 END),0) AS shopping_missing,
 COALESCE(SUM(CASE WHEN profile_matched AND pvalue_level IS NULL THEN 1 ELSE 0 END),0) AS pvalue_missing,
 COALESCE(SUM(CASE WHEN profile_matched AND occupation IS NULL THEN 1 ELSE 0 END),0) AS occupation_missing,
 COALESCE(SUM(CASE WHEN profile_matched AND city_level IS NULL THEN 1 ELSE 0 END),0) AS city_missing
 FROM ${hivevar:ns}_dwd.exposure
 WHERE batch_id='${hivevar:batch}' AND dt BETWEEN '2018-01-01' AND '2018-01-02'
 
)
SELECT impressions,matched_profile_impressions,reached_users,matched_profile_users,matched_ad_impressions,gender_missing,age_missing,shopping_missing,pvalue_missing,occupation_missing,city_missing,
 CAST(matched_profile_impressions AS DOUBLE)/nullif(impressions,0) AS profile_row_coverage,
 CAST(matched_profile_users AS DOUBLE)/nullif(reached_users,0) AS profile_user_coverage,
 CAST(matched_ad_impressions AS DOUBLE)/nullif(impressions,0) AS ad_row_coverage,
 CAST(gender_missing AS DOUBLE)/nullif(matched_profile_impressions,0) AS gender_missing_rate,
 CAST(age_missing AS DOUBLE)/nullif(matched_profile_impressions,0) AS age_missing_rate,
 CAST(shopping_missing AS DOUBLE)/nullif(matched_profile_impressions,0) AS shopping_missing_rate,
 CAST(pvalue_missing AS DOUBLE)/nullif(matched_profile_impressions,0) AS pvalue_missing_rate,
 CAST(occupation_missing AS DOUBLE)/nullif(matched_profile_impressions,0) AS occupation_missing_rate,
 CAST(city_missing AS DOUBLE)/nullif(matched_profile_impressions,0) AS city_missing_rate FROM counted;
CREATE TEMPORARY TABLE r_empty_groups STORED AS ORC AS
-- Render through query_metrics.py. Denominators precede threshold and Top N.
WITH grouped AS (
 SELECT CASE WHEN NOT profile_matched THEN '__unmatched_profile__' ELSE coalesce(occupation,'__missing_attribute__') END AS group_value_1,CASE WHEN NOT profile_matched THEN '__unmatched_profile__' ELSE coalesce(city_level,'__missing_attribute__') END AS group_value_2,
 COUNT(*) impressions,SUM(click_count) clicks,COUNT(DISTINCT user_id) reached_users,
 COUNT(DISTINCT CASE WHEN click_count=1 THEN user_id END) clicked_users,
 COUNT(DISTINCT adgroup_id) ad_units
 FROM ${hivevar:ns}_dwd.exposure
 WHERE batch_id='${hivevar:batch}' AND dt BETWEEN '2018-01-01' AND '2018-01-02'
 
 GROUP BY CASE WHEN NOT profile_matched THEN '__unmatched_profile__' ELSE coalesce(occupation,'__missing_attribute__') END,CASE WHEN NOT profile_matched THEN '__unmatched_profile__' ELSE coalesce(city_level,'__missing_attribute__') END
), scored AS (
 SELECT *,CAST(clicks AS DOUBLE)/nullif(impressions,0) ctr,
 CAST(clicked_users AS DOUBLE)/nullif(reached_users,0) user_click_ratio,
 CAST(impressions AS DOUBLE)/nullif(reached_users,0) impressions_per_user,
 CAST(impressions AS DOUBLE)/nullif(SUM(impressions) OVER(),0) impression_share,
 CAST(clicks AS DOUBLE)/nullif(SUM(clicks) OVER(),0) click_share
 FROM grouped
)
SELECT group_value_1,group_value_2,impressions,clicks,ctr,reached_users,clicked_users,
 user_click_ratio,ad_units,impressions_per_user,impression_share,click_share
FROM scored WHERE impressions>=0
ORDER BY clicks DESC,impressions DESC,group_value_1,group_value_2 LIMIT 100;
SELECT assert_true(COUNT(*)=1) FROM r_empty_overview;
SELECT assert_true(coalesce((impressions=0 AND clicks=0 AND reached_users=0 AND clicked_users=0 AND ad_units=0 AND ctr IS NULL AND user_click_ratio IS NULL AND impressions_per_user IS NULL),false)) FROM r_empty_overview;
SELECT assert_true(COUNT(*)=1) FROM r_empty_quality;
SELECT assert_true(coalesce((impressions=0 AND matched_profile_impressions=0 AND matched_profile_users=0 AND profile_row_coverage IS NULL AND profile_user_coverage IS NULL AND gender_missing_rate IS NULL),false)) FROM r_empty_quality;
SELECT assert_true(COUNT(*)=0) FROM r_empty_groups;
CREATE TEMPORARY TABLE r_zero_overview STORED AS ORC AS
-- Recompute exact user counts from DWD for the WHOLE selected period.
-- Never sum daily reached_users/clicked_users/ad_units from ADS.
SELECT COUNT(*) impressions,COALESCE(SUM(click_count),0) clicks,
 CAST(SUM(click_count) AS DOUBLE)/nullif(COUNT(*),0) ctr,
 COUNT(DISTINCT user_id) reached_users,
 COUNT(DISTINCT CASE WHEN click_count=1 THEN user_id END) clicked_users,
 COUNT(DISTINCT adgroup_id) ad_units,
 CAST(COUNT(DISTINCT CASE WHEN click_count=1 THEN user_id END) AS DOUBLE)/nullif(COUNT(DISTINCT user_id),0) user_click_ratio,
 CAST(COUNT(*) AS DOUBLE)/nullif(COUNT(DISTINCT user_id),0) impressions_per_user
FROM ${hivevar:ns}_dwd.exposure
WHERE batch_id='${hivevar:batch}' AND dt BETWEEN '2017-05-08' AND '2017-05-08';
CREATE TEMPORARY TABLE r_zero_quality STORED AS ORC AS
-- Q01-Q04 are computed BEFORE portrait filters; all counts are zero for an empty scope.
WITH counted AS (
 SELECT COUNT(*) AS impressions,
 COALESCE(SUM(CASE WHEN profile_matched THEN 1 ELSE 0 END),0) AS matched_profile_impressions,
 COUNT(DISTINCT user_id) AS reached_users,
 COUNT(DISTINCT CASE WHEN profile_matched THEN user_id END) AS matched_profile_users,
 COALESCE(SUM(CASE WHEN ad_matched THEN 1 ELSE 0 END),0) AS matched_ad_impressions,
 COALESCE(SUM(CASE WHEN profile_matched AND gender_code IS NULL THEN 1 ELSE 0 END),0) AS gender_missing,
 COALESCE(SUM(CASE WHEN profile_matched AND age_level IS NULL THEN 1 ELSE 0 END),0) AS age_missing,
 COALESCE(SUM(CASE WHEN profile_matched AND shopping_level IS NULL THEN 1 ELSE 0 END),0) AS shopping_missing,
 COALESCE(SUM(CASE WHEN profile_matched AND pvalue_level IS NULL THEN 1 ELSE 0 END),0) AS pvalue_missing,
 COALESCE(SUM(CASE WHEN profile_matched AND occupation IS NULL THEN 1 ELSE 0 END),0) AS occupation_missing,
 COALESCE(SUM(CASE WHEN profile_matched AND city_level IS NULL THEN 1 ELSE 0 END),0) AS city_missing
 FROM ${hivevar:ns}_dwd.exposure
 WHERE batch_id='${hivevar:batch}' AND dt BETWEEN '2017-05-08' AND '2017-05-08'
 
)
SELECT impressions,matched_profile_impressions,reached_users,matched_profile_users,matched_ad_impressions,gender_missing,age_missing,shopping_missing,pvalue_missing,occupation_missing,city_missing,
 CAST(matched_profile_impressions AS DOUBLE)/nullif(impressions,0) AS profile_row_coverage,
 CAST(matched_profile_users AS DOUBLE)/nullif(reached_users,0) AS profile_user_coverage,
 CAST(matched_ad_impressions AS DOUBLE)/nullif(impressions,0) AS ad_row_coverage,
 CAST(gender_missing AS DOUBLE)/nullif(matched_profile_impressions,0) AS gender_missing_rate,
 CAST(age_missing AS DOUBLE)/nullif(matched_profile_impressions,0) AS age_missing_rate,
 CAST(shopping_missing AS DOUBLE)/nullif(matched_profile_impressions,0) AS shopping_missing_rate,
 CAST(pvalue_missing AS DOUBLE)/nullif(matched_profile_impressions,0) AS pvalue_missing_rate,
 CAST(occupation_missing AS DOUBLE)/nullif(matched_profile_impressions,0) AS occupation_missing_rate,
 CAST(city_missing AS DOUBLE)/nullif(matched_profile_impressions,0) AS city_missing_rate FROM counted;
CREATE TEMPORARY TABLE r_zero_groups STORED AS ORC AS
-- Render through query_metrics.py. Denominators precede threshold and Top N.
WITH grouped AS (
 SELECT CASE WHEN NOT profile_matched THEN '__unmatched_profile__' ELSE coalesce(occupation,'__missing_attribute__') END AS group_value_1,CASE WHEN NOT profile_matched THEN '__unmatched_profile__' ELSE coalesce(city_level,'__missing_attribute__') END AS group_value_2,
 COUNT(*) impressions,SUM(click_count) clicks,COUNT(DISTINCT user_id) reached_users,
 COUNT(DISTINCT CASE WHEN click_count=1 THEN user_id END) clicked_users,
 COUNT(DISTINCT adgroup_id) ad_units
 FROM ${hivevar:ns}_dwd.exposure
 WHERE batch_id='${hivevar:batch}' AND dt BETWEEN '2017-05-08' AND '2017-05-08'
 
 GROUP BY CASE WHEN NOT profile_matched THEN '__unmatched_profile__' ELSE coalesce(occupation,'__missing_attribute__') END,CASE WHEN NOT profile_matched THEN '__unmatched_profile__' ELSE coalesce(city_level,'__missing_attribute__') END
), scored AS (
 SELECT *,CAST(clicks AS DOUBLE)/nullif(impressions,0) ctr,
 CAST(clicked_users AS DOUBLE)/nullif(reached_users,0) user_click_ratio,
 CAST(impressions AS DOUBLE)/nullif(reached_users,0) impressions_per_user,
 CAST(impressions AS DOUBLE)/nullif(SUM(impressions) OVER(),0) impression_share,
 CAST(clicks AS DOUBLE)/nullif(SUM(clicks) OVER(),0) click_share
 FROM grouped
)
SELECT group_value_1,group_value_2,impressions,clicks,ctr,reached_users,clicked_users,
 user_click_ratio,ad_units,impressions_per_user,impression_share,click_share
FROM scored WHERE impressions>=0
ORDER BY clicks DESC,impressions DESC,group_value_1,group_value_2 LIMIT 100;
SELECT assert_true(COUNT(*)=1) FROM r_zero_overview;
SELECT assert_true(coalesce((impressions=2 AND clicks=0 AND ctr=0 AND clicked_users=0 AND user_click_ratio=0),false)) FROM r_zero_overview;
SELECT assert_true(COUNT(*)=1) FROM r_zero_quality;
SELECT assert_true(coalesce((profile_row_coverage=1 AND profile_user_coverage=1 AND gender_missing_rate=0.5),false)) FROM r_zero_quality;
SELECT assert_true(COUNT(*)=2 AND SUM(CASE WHEN click_share IS NULL THEN 1 ELSE 0 END)=2) FROM r_zero_groups;
CREATE TEMPORARY TABLE r_unmatched_overview STORED AS ORC AS
-- Recompute exact user counts from DWD for the WHOLE selected period.
-- Never sum daily reached_users/clicked_users/ad_units from ADS.
SELECT COUNT(*) impressions,COALESCE(SUM(click_count),0) clicks,
 CAST(SUM(click_count) AS DOUBLE)/nullif(COUNT(*),0) ctr,
 COUNT(DISTINCT user_id) reached_users,
 COUNT(DISTINCT CASE WHEN click_count=1 THEN user_id END) clicked_users,
 COUNT(DISTINCT adgroup_id) ad_units,
 CAST(COUNT(DISTINCT CASE WHEN click_count=1 THEN user_id END) AS DOUBLE)/nullif(COUNT(DISTINCT user_id),0) user_click_ratio,
 CAST(COUNT(*) AS DOUBLE)/nullif(COUNT(DISTINCT user_id),0) impressions_per_user
FROM ${hivevar:ns}_dwd.exposure
WHERE batch_id='${hivevar:batch}' AND dt BETWEEN '2017-05-09' AND '2017-05-09';
CREATE TEMPORARY TABLE r_unmatched_quality STORED AS ORC AS
-- Q01-Q04 are computed BEFORE portrait filters; all counts are zero for an empty scope.
WITH counted AS (
 SELECT COUNT(*) AS impressions,
 COALESCE(SUM(CASE WHEN profile_matched THEN 1 ELSE 0 END),0) AS matched_profile_impressions,
 COUNT(DISTINCT user_id) AS reached_users,
 COUNT(DISTINCT CASE WHEN profile_matched THEN user_id END) AS matched_profile_users,
 COALESCE(SUM(CASE WHEN ad_matched THEN 1 ELSE 0 END),0) AS matched_ad_impressions,
 COALESCE(SUM(CASE WHEN profile_matched AND gender_code IS NULL THEN 1 ELSE 0 END),0) AS gender_missing,
 COALESCE(SUM(CASE WHEN profile_matched AND age_level IS NULL THEN 1 ELSE 0 END),0) AS age_missing,
 COALESCE(SUM(CASE WHEN profile_matched AND shopping_level IS NULL THEN 1 ELSE 0 END),0) AS shopping_missing,
 COALESCE(SUM(CASE WHEN profile_matched AND pvalue_level IS NULL THEN 1 ELSE 0 END),0) AS pvalue_missing,
 COALESCE(SUM(CASE WHEN profile_matched AND occupation IS NULL THEN 1 ELSE 0 END),0) AS occupation_missing,
 COALESCE(SUM(CASE WHEN profile_matched AND city_level IS NULL THEN 1 ELSE 0 END),0) AS city_missing
 FROM ${hivevar:ns}_dwd.exposure
 WHERE batch_id='${hivevar:batch}' AND dt BETWEEN '2017-05-09' AND '2017-05-09'
 
)
SELECT impressions,matched_profile_impressions,reached_users,matched_profile_users,matched_ad_impressions,gender_missing,age_missing,shopping_missing,pvalue_missing,occupation_missing,city_missing,
 CAST(matched_profile_impressions AS DOUBLE)/nullif(impressions,0) AS profile_row_coverage,
 CAST(matched_profile_users AS DOUBLE)/nullif(reached_users,0) AS profile_user_coverage,
 CAST(matched_ad_impressions AS DOUBLE)/nullif(impressions,0) AS ad_row_coverage,
 CAST(gender_missing AS DOUBLE)/nullif(matched_profile_impressions,0) AS gender_missing_rate,
 CAST(age_missing AS DOUBLE)/nullif(matched_profile_impressions,0) AS age_missing_rate,
 CAST(shopping_missing AS DOUBLE)/nullif(matched_profile_impressions,0) AS shopping_missing_rate,
 CAST(pvalue_missing AS DOUBLE)/nullif(matched_profile_impressions,0) AS pvalue_missing_rate,
 CAST(occupation_missing AS DOUBLE)/nullif(matched_profile_impressions,0) AS occupation_missing_rate,
 CAST(city_missing AS DOUBLE)/nullif(matched_profile_impressions,0) AS city_missing_rate FROM counted;
CREATE TEMPORARY TABLE r_unmatched_groups STORED AS ORC AS
-- Render through query_metrics.py. Denominators precede threshold and Top N.
WITH grouped AS (
 SELECT CASE WHEN NOT profile_matched THEN '__unmatched_profile__' ELSE coalesce(occupation,'__missing_attribute__') END AS group_value_1,CASE WHEN NOT profile_matched THEN '__unmatched_profile__' ELSE coalesce(city_level,'__missing_attribute__') END AS group_value_2,
 COUNT(*) impressions,SUM(click_count) clicks,COUNT(DISTINCT user_id) reached_users,
 COUNT(DISTINCT CASE WHEN click_count=1 THEN user_id END) clicked_users,
 COUNT(DISTINCT adgroup_id) ad_units
 FROM ${hivevar:ns}_dwd.exposure
 WHERE batch_id='${hivevar:batch}' AND dt BETWEEN '2017-05-09' AND '2017-05-09'
 
 GROUP BY CASE WHEN NOT profile_matched THEN '__unmatched_profile__' ELSE coalesce(occupation,'__missing_attribute__') END,CASE WHEN NOT profile_matched THEN '__unmatched_profile__' ELSE coalesce(city_level,'__missing_attribute__') END
), scored AS (
 SELECT *,CAST(clicks AS DOUBLE)/nullif(impressions,0) ctr,
 CAST(clicked_users AS DOUBLE)/nullif(reached_users,0) user_click_ratio,
 CAST(impressions AS DOUBLE)/nullif(reached_users,0) impressions_per_user,
 CAST(impressions AS DOUBLE)/nullif(SUM(impressions) OVER(),0) impression_share,
 CAST(clicks AS DOUBLE)/nullif(SUM(clicks) OVER(),0) click_share
 FROM grouped
)
SELECT group_value_1,group_value_2,impressions,clicks,ctr,reached_users,clicked_users,
 user_click_ratio,ad_units,impressions_per_user,impression_share,click_share
FROM scored WHERE impressions>=0
ORDER BY clicks DESC,impressions DESC,group_value_1,group_value_2 LIMIT 100;
SELECT assert_true(COUNT(*)=1) FROM r_unmatched_quality;
SELECT assert_true(coalesce((profile_row_coverage=0 AND profile_user_coverage=0 AND ad_row_coverage=0 AND gender_missing=0 AND gender_missing_rate IS NULL AND city_missing_rate IS NULL),false)) FROM r_unmatched_quality;
SELECT assert_true(COUNT(*)=1) FROM r_unmatched_groups;
SELECT assert_true(coalesce((group_value_1='__unmatched_profile__' AND reached_users=1 AND click_share IS NULL),false)) FROM r_unmatched_groups;
CREATE TEMPORARY TABLE r_portrait_overview STORED AS ORC AS
-- Recompute exact user counts from DWD for the WHOLE selected period.
-- Never sum daily reached_users/clicked_users/ad_units from ADS.
SELECT COUNT(*) impressions,COALESCE(SUM(click_count),0) clicks,
 CAST(SUM(click_count) AS DOUBLE)/nullif(COUNT(*),0) ctr,
 COUNT(DISTINCT user_id) reached_users,
 COUNT(DISTINCT CASE WHEN click_count=1 THEN user_id END) clicked_users,
 COUNT(DISTINCT adgroup_id) ad_units,
 CAST(COUNT(DISTINCT CASE WHEN click_count=1 THEN user_id END) AS DOUBLE)/nullif(COUNT(DISTINCT user_id),0) user_click_ratio,
 CAST(COUNT(*) AS DOUBLE)/nullif(COUNT(DISTINCT user_id),0) impressions_per_user
FROM ${hivevar:ns}_dwd.exposure
WHERE batch_id='${hivevar:batch}' AND dt BETWEEN '2017-05-06' AND '2017-05-13' AND (CASE WHEN NOT profile_matched THEN '__unmatched_profile__' ELSE coalesce(gender_code,'__missing_attribute__') END)='1';
CREATE TEMPORARY TABLE r_portrait_quality STORED AS ORC AS
-- Q01-Q04 are computed BEFORE portrait filters; all counts are zero for an empty scope.
WITH counted AS (
 SELECT COUNT(*) AS impressions,
 COALESCE(SUM(CASE WHEN profile_matched THEN 1 ELSE 0 END),0) AS matched_profile_impressions,
 COUNT(DISTINCT user_id) AS reached_users,
 COUNT(DISTINCT CASE WHEN profile_matched THEN user_id END) AS matched_profile_users,
 COALESCE(SUM(CASE WHEN ad_matched THEN 1 ELSE 0 END),0) AS matched_ad_impressions,
 COALESCE(SUM(CASE WHEN profile_matched AND gender_code IS NULL THEN 1 ELSE 0 END),0) AS gender_missing,
 COALESCE(SUM(CASE WHEN profile_matched AND age_level IS NULL THEN 1 ELSE 0 END),0) AS age_missing,
 COALESCE(SUM(CASE WHEN profile_matched AND shopping_level IS NULL THEN 1 ELSE 0 END),0) AS shopping_missing,
 COALESCE(SUM(CASE WHEN profile_matched AND pvalue_level IS NULL THEN 1 ELSE 0 END),0) AS pvalue_missing,
 COALESCE(SUM(CASE WHEN profile_matched AND occupation IS NULL THEN 1 ELSE 0 END),0) AS occupation_missing,
 COALESCE(SUM(CASE WHEN profile_matched AND city_level IS NULL THEN 1 ELSE 0 END),0) AS city_missing
 FROM ${hivevar:ns}_dwd.exposure
 WHERE batch_id='${hivevar:batch}' AND dt BETWEEN '2017-05-06' AND '2017-05-13'
 
)
SELECT impressions,matched_profile_impressions,reached_users,matched_profile_users,matched_ad_impressions,gender_missing,age_missing,shopping_missing,pvalue_missing,occupation_missing,city_missing,
 CAST(matched_profile_impressions AS DOUBLE)/nullif(impressions,0) AS profile_row_coverage,
 CAST(matched_profile_users AS DOUBLE)/nullif(reached_users,0) AS profile_user_coverage,
 CAST(matched_ad_impressions AS DOUBLE)/nullif(impressions,0) AS ad_row_coverage,
 CAST(gender_missing AS DOUBLE)/nullif(matched_profile_impressions,0) AS gender_missing_rate,
 CAST(age_missing AS DOUBLE)/nullif(matched_profile_impressions,0) AS age_missing_rate,
 CAST(shopping_missing AS DOUBLE)/nullif(matched_profile_impressions,0) AS shopping_missing_rate,
 CAST(pvalue_missing AS DOUBLE)/nullif(matched_profile_impressions,0) AS pvalue_missing_rate,
 CAST(occupation_missing AS DOUBLE)/nullif(matched_profile_impressions,0) AS occupation_missing_rate,
 CAST(city_missing AS DOUBLE)/nullif(matched_profile_impressions,0) AS city_missing_rate FROM counted;
CREATE TEMPORARY TABLE r_portrait_groups STORED AS ORC AS
-- Render through query_metrics.py. Denominators precede threshold and Top N.
WITH grouped AS (
 SELECT CASE WHEN NOT profile_matched THEN '__unmatched_profile__' ELSE coalesce(occupation,'__missing_attribute__') END AS group_value_1,CASE WHEN NOT profile_matched THEN '__unmatched_profile__' ELSE coalesce(city_level,'__missing_attribute__') END AS group_value_2,
 COUNT(*) impressions,SUM(click_count) clicks,COUNT(DISTINCT user_id) reached_users,
 COUNT(DISTINCT CASE WHEN click_count=1 THEN user_id END) clicked_users,
 COUNT(DISTINCT adgroup_id) ad_units
 FROM ${hivevar:ns}_dwd.exposure
 WHERE batch_id='${hivevar:batch}' AND dt BETWEEN '2017-05-06' AND '2017-05-13'
  AND (CASE WHEN NOT profile_matched THEN '__unmatched_profile__' ELSE coalesce(gender_code,'__missing_attribute__') END)='1'
 GROUP BY CASE WHEN NOT profile_matched THEN '__unmatched_profile__' ELSE coalesce(occupation,'__missing_attribute__') END,CASE WHEN NOT profile_matched THEN '__unmatched_profile__' ELSE coalesce(city_level,'__missing_attribute__') END
), scored AS (
 SELECT *,CAST(clicks AS DOUBLE)/nullif(impressions,0) ctr,
 CAST(clicked_users AS DOUBLE)/nullif(reached_users,0) user_click_ratio,
 CAST(impressions AS DOUBLE)/nullif(reached_users,0) impressions_per_user,
 CAST(impressions AS DOUBLE)/nullif(SUM(impressions) OVER(),0) impression_share,
 CAST(clicks AS DOUBLE)/nullif(SUM(clicks) OVER(),0) click_share
 FROM grouped
)
SELECT group_value_1,group_value_2,impressions,clicks,ctr,reached_users,clicked_users,
 user_click_ratio,ad_units,impressions_per_user,impression_share,click_share
FROM scored WHERE impressions>=0
ORDER BY clicks DESC,impressions DESC,group_value_1,group_value_2 LIMIT 100;
SELECT assert_true(COUNT(*)=1) FROM r_portrait_overview;
SELECT assert_true(coalesce((impressions=4 AND clicks=1 AND reached_users=1),false)) FROM r_portrait_overview;
SELECT assert_true(COUNT(*)=1) FROM r_portrait_quality;
SELECT assert_true(coalesce((impressions=9 AND matched_profile_impressions=7 AND profile_user_coverage=0.5),false)) FROM r_portrait_quality;
CREATE TEMPORARY TABLE r_threshold_overview STORED AS ORC AS
-- Recompute exact user counts from DWD for the WHOLE selected period.
-- Never sum daily reached_users/clicked_users/ad_units from ADS.
SELECT COUNT(*) impressions,COALESCE(SUM(click_count),0) clicks,
 CAST(SUM(click_count) AS DOUBLE)/nullif(COUNT(*),0) ctr,
 COUNT(DISTINCT user_id) reached_users,
 COUNT(DISTINCT CASE WHEN click_count=1 THEN user_id END) clicked_users,
 COUNT(DISTINCT adgroup_id) ad_units,
 CAST(COUNT(DISTINCT CASE WHEN click_count=1 THEN user_id END) AS DOUBLE)/nullif(COUNT(DISTINCT user_id),0) user_click_ratio,
 CAST(COUNT(*) AS DOUBLE)/nullif(COUNT(DISTINCT user_id),0) impressions_per_user
FROM ${hivevar:ns}_dwd.exposure
WHERE batch_id='${hivevar:batch}' AND dt BETWEEN '2017-05-06' AND '2017-05-13';
CREATE TEMPORARY TABLE r_threshold_quality STORED AS ORC AS
-- Q01-Q04 are computed BEFORE portrait filters; all counts are zero for an empty scope.
WITH counted AS (
 SELECT COUNT(*) AS impressions,
 COALESCE(SUM(CASE WHEN profile_matched THEN 1 ELSE 0 END),0) AS matched_profile_impressions,
 COUNT(DISTINCT user_id) AS reached_users,
 COUNT(DISTINCT CASE WHEN profile_matched THEN user_id END) AS matched_profile_users,
 COALESCE(SUM(CASE WHEN ad_matched THEN 1 ELSE 0 END),0) AS matched_ad_impressions,
 COALESCE(SUM(CASE WHEN profile_matched AND gender_code IS NULL THEN 1 ELSE 0 END),0) AS gender_missing,
 COALESCE(SUM(CASE WHEN profile_matched AND age_level IS NULL THEN 1 ELSE 0 END),0) AS age_missing,
 COALESCE(SUM(CASE WHEN profile_matched AND shopping_level IS NULL THEN 1 ELSE 0 END),0) AS shopping_missing,
 COALESCE(SUM(CASE WHEN profile_matched AND pvalue_level IS NULL THEN 1 ELSE 0 END),0) AS pvalue_missing,
 COALESCE(SUM(CASE WHEN profile_matched AND occupation IS NULL THEN 1 ELSE 0 END),0) AS occupation_missing,
 COALESCE(SUM(CASE WHEN profile_matched AND city_level IS NULL THEN 1 ELSE 0 END),0) AS city_missing
 FROM ${hivevar:ns}_dwd.exposure
 WHERE batch_id='${hivevar:batch}' AND dt BETWEEN '2017-05-06' AND '2017-05-13'
 
)
SELECT impressions,matched_profile_impressions,reached_users,matched_profile_users,matched_ad_impressions,gender_missing,age_missing,shopping_missing,pvalue_missing,occupation_missing,city_missing,
 CAST(matched_profile_impressions AS DOUBLE)/nullif(impressions,0) AS profile_row_coverage,
 CAST(matched_profile_users AS DOUBLE)/nullif(reached_users,0) AS profile_user_coverage,
 CAST(matched_ad_impressions AS DOUBLE)/nullif(impressions,0) AS ad_row_coverage,
 CAST(gender_missing AS DOUBLE)/nullif(matched_profile_impressions,0) AS gender_missing_rate,
 CAST(age_missing AS DOUBLE)/nullif(matched_profile_impressions,0) AS age_missing_rate,
 CAST(shopping_missing AS DOUBLE)/nullif(matched_profile_impressions,0) AS shopping_missing_rate,
 CAST(pvalue_missing AS DOUBLE)/nullif(matched_profile_impressions,0) AS pvalue_missing_rate,
 CAST(occupation_missing AS DOUBLE)/nullif(matched_profile_impressions,0) AS occupation_missing_rate,
 CAST(city_missing AS DOUBLE)/nullif(matched_profile_impressions,0) AS city_missing_rate FROM counted;
CREATE TEMPORARY TABLE r_threshold_groups STORED AS ORC AS
-- Render through query_metrics.py. Denominators precede threshold and Top N.
WITH grouped AS (
 SELECT CASE WHEN NOT profile_matched THEN '__unmatched_profile__' ELSE coalesce(occupation,'__missing_attribute__') END AS group_value_1,CASE WHEN NOT profile_matched THEN '__unmatched_profile__' ELSE coalesce(city_level,'__missing_attribute__') END AS group_value_2,
 COUNT(*) impressions,SUM(click_count) clicks,COUNT(DISTINCT user_id) reached_users,
 COUNT(DISTINCT CASE WHEN click_count=1 THEN user_id END) clicked_users,
 COUNT(DISTINCT adgroup_id) ad_units
 FROM ${hivevar:ns}_dwd.exposure
 WHERE batch_id='${hivevar:batch}' AND dt BETWEEN '2017-05-06' AND '2017-05-13'
 
 GROUP BY CASE WHEN NOT profile_matched THEN '__unmatched_profile__' ELSE coalesce(occupation,'__missing_attribute__') END,CASE WHEN NOT profile_matched THEN '__unmatched_profile__' ELSE coalesce(city_level,'__missing_attribute__') END
), scored AS (
 SELECT *,CAST(clicks AS DOUBLE)/nullif(impressions,0) ctr,
 CAST(clicked_users AS DOUBLE)/nullif(reached_users,0) user_click_ratio,
 CAST(impressions AS DOUBLE)/nullif(reached_users,0) impressions_per_user,
 CAST(impressions AS DOUBLE)/nullif(SUM(impressions) OVER(),0) impression_share,
 CAST(clicks AS DOUBLE)/nullif(SUM(clicks) OVER(),0) click_share
 FROM grouped
)
SELECT group_value_1,group_value_2,impressions,clicks,ctr,reached_users,clicked_users,
 user_click_ratio,ad_units,impressions_per_user,impression_share,click_share
FROM scored WHERE impressions>=4
ORDER BY ctr DESC,impressions DESC,group_value_1,group_value_2 LIMIT 1;
SELECT assert_true(COUNT(*)=1) FROM r_threshold_groups;
SELECT assert_true(coalesce((group_value_1='0' AND impressions=4 AND ctr=0.25 AND abs(impression_share-4.0/9)<1e-10),false)) FROM r_threshold_groups;
CREATE TEMPORARY TABLE r_ctr_default_overview STORED AS ORC AS
-- Recompute exact user counts from DWD for the WHOLE selected period.
-- Never sum daily reached_users/clicked_users/ad_units from ADS.
SELECT COUNT(*) impressions,COALESCE(SUM(click_count),0) clicks,
 CAST(SUM(click_count) AS DOUBLE)/nullif(COUNT(*),0) ctr,
 COUNT(DISTINCT user_id) reached_users,
 COUNT(DISTINCT CASE WHEN click_count=1 THEN user_id END) clicked_users,
 COUNT(DISTINCT adgroup_id) ad_units,
 CAST(COUNT(DISTINCT CASE WHEN click_count=1 THEN user_id END) AS DOUBLE)/nullif(COUNT(DISTINCT user_id),0) user_click_ratio,
 CAST(COUNT(*) AS DOUBLE)/nullif(COUNT(DISTINCT user_id),0) impressions_per_user
FROM ${hivevar:ns}_dwd.exposure
WHERE batch_id='${hivevar:batch}' AND dt BETWEEN '2017-05-06' AND '2017-05-13';
CREATE TEMPORARY TABLE r_ctr_default_quality STORED AS ORC AS
-- Q01-Q04 are computed BEFORE portrait filters; all counts are zero for an empty scope.
WITH counted AS (
 SELECT COUNT(*) AS impressions,
 COALESCE(SUM(CASE WHEN profile_matched THEN 1 ELSE 0 END),0) AS matched_profile_impressions,
 COUNT(DISTINCT user_id) AS reached_users,
 COUNT(DISTINCT CASE WHEN profile_matched THEN user_id END) AS matched_profile_users,
 COALESCE(SUM(CASE WHEN ad_matched THEN 1 ELSE 0 END),0) AS matched_ad_impressions,
 COALESCE(SUM(CASE WHEN profile_matched AND gender_code IS NULL THEN 1 ELSE 0 END),0) AS gender_missing,
 COALESCE(SUM(CASE WHEN profile_matched AND age_level IS NULL THEN 1 ELSE 0 END),0) AS age_missing,
 COALESCE(SUM(CASE WHEN profile_matched AND shopping_level IS NULL THEN 1 ELSE 0 END),0) AS shopping_missing,
 COALESCE(SUM(CASE WHEN profile_matched AND pvalue_level IS NULL THEN 1 ELSE 0 END),0) AS pvalue_missing,
 COALESCE(SUM(CASE WHEN profile_matched AND occupation IS NULL THEN 1 ELSE 0 END),0) AS occupation_missing,
 COALESCE(SUM(CASE WHEN profile_matched AND city_level IS NULL THEN 1 ELSE 0 END),0) AS city_missing
 FROM ${hivevar:ns}_dwd.exposure
 WHERE batch_id='${hivevar:batch}' AND dt BETWEEN '2017-05-06' AND '2017-05-13'
 
)
SELECT impressions,matched_profile_impressions,reached_users,matched_profile_users,matched_ad_impressions,gender_missing,age_missing,shopping_missing,pvalue_missing,occupation_missing,city_missing,
 CAST(matched_profile_impressions AS DOUBLE)/nullif(impressions,0) AS profile_row_coverage,
 CAST(matched_profile_users AS DOUBLE)/nullif(reached_users,0) AS profile_user_coverage,
 CAST(matched_ad_impressions AS DOUBLE)/nullif(impressions,0) AS ad_row_coverage,
 CAST(gender_missing AS DOUBLE)/nullif(matched_profile_impressions,0) AS gender_missing_rate,
 CAST(age_missing AS DOUBLE)/nullif(matched_profile_impressions,0) AS age_missing_rate,
 CAST(shopping_missing AS DOUBLE)/nullif(matched_profile_impressions,0) AS shopping_missing_rate,
 CAST(pvalue_missing AS DOUBLE)/nullif(matched_profile_impressions,0) AS pvalue_missing_rate,
 CAST(occupation_missing AS DOUBLE)/nullif(matched_profile_impressions,0) AS occupation_missing_rate,
 CAST(city_missing AS DOUBLE)/nullif(matched_profile_impressions,0) AS city_missing_rate FROM counted;
CREATE TEMPORARY TABLE r_ctr_default_groups STORED AS ORC AS
-- Render through query_metrics.py. Denominators precede threshold and Top N.
WITH grouped AS (
 SELECT CASE WHEN NOT profile_matched THEN '__unmatched_profile__' ELSE coalesce(occupation,'__missing_attribute__') END AS group_value_1,CASE WHEN NOT profile_matched THEN '__unmatched_profile__' ELSE coalesce(city_level,'__missing_attribute__') END AS group_value_2,
 COUNT(*) impressions,SUM(click_count) clicks,COUNT(DISTINCT user_id) reached_users,
 COUNT(DISTINCT CASE WHEN click_count=1 THEN user_id END) clicked_users,
 COUNT(DISTINCT adgroup_id) ad_units
 FROM ${hivevar:ns}_dwd.exposure
 WHERE batch_id='${hivevar:batch}' AND dt BETWEEN '2017-05-06' AND '2017-05-13'
 
 GROUP BY CASE WHEN NOT profile_matched THEN '__unmatched_profile__' ELSE coalesce(occupation,'__missing_attribute__') END,CASE WHEN NOT profile_matched THEN '__unmatched_profile__' ELSE coalesce(city_level,'__missing_attribute__') END
), scored AS (
 SELECT *,CAST(clicks AS DOUBLE)/nullif(impressions,0) ctr,
 CAST(clicked_users AS DOUBLE)/nullif(reached_users,0) user_click_ratio,
 CAST(impressions AS DOUBLE)/nullif(reached_users,0) impressions_per_user,
 CAST(impressions AS DOUBLE)/nullif(SUM(impressions) OVER(),0) impression_share,
 CAST(clicks AS DOUBLE)/nullif(SUM(clicks) OVER(),0) click_share
 FROM grouped
)
SELECT group_value_1,group_value_2,impressions,clicks,ctr,reached_users,clicked_users,
 user_click_ratio,ad_units,impressions_per_user,impression_share,click_share
FROM scored WHERE impressions>=1000
ORDER BY ctr DESC,impressions DESC,group_value_1,group_value_2 LIMIT 100;
SELECT assert_true(COUNT(*)=0) FROM r_ctr_default_groups;
SELECT 'SQL_V2_POSITIVE_REGRESSIONS_PASS' AS result;
-- Re-derive expectations from DWD, then check missing/duplicate rows and ALL output fields.
CREATE TEMPORARY TABLE expected_daily STORED AS ORC AS SELECT dt,
 COUNT(*) impressions,
 SUM(click_count) clicks,
 COUNT(DISTINCT user_id) reached_users,
 COUNT(DISTINCT CASE WHEN click_count=1 THEN user_id END) clicked_users,
 COUNT(DISTINCT adgroup_id) ad_units,
 SUM(CASE WHEN NOT profile_matched THEN 1 ELSE 0 END) unmatched_profiles,
 SUM(CASE WHEN NOT ad_matched THEN 1 ELSE 0 END) unmatched_ads,
 SUM(CASE WHEN profile_matched THEN 1 ELSE 0 END) matched_profile_impressions,
 COUNT(DISTINCT CASE WHEN profile_matched THEN user_id END) matched_profile_users,
 SUM(CASE WHEN ad_matched THEN 1 ELSE 0 END) matched_ad_impressions,
 SUM(CASE WHEN profile_matched AND gender_code IS NULL THEN 1 ELSE 0 END) gender_missing,
 SUM(CASE WHEN profile_matched AND age_level IS NULL THEN 1 ELSE 0 END) age_missing,
 SUM(CASE WHEN profile_matched AND shopping_level IS NULL THEN 1 ELSE 0 END) shopping_missing,
 SUM(CASE WHEN profile_matched AND pvalue_level IS NULL THEN 1 ELSE 0 END) pvalue_missing,
 SUM(CASE WHEN profile_matched AND occupation IS NULL THEN 1 ELSE 0 END) occupation_missing,
 SUM(CASE WHEN profile_matched AND city_level IS NULL THEN 1 ELSE 0 END) city_missing
FROM ${hivevar:ns}_dwd.exposure WHERE batch_id='${hivevar:batch}' GROUP BY dt;
CREATE TEMPORARY TABLE expected_axis STORED AS ORC AS
SELECT dt,k.axis,k.axis_value,COUNT(*) impressions,SUM(click_count) clicks,
 COUNT(DISTINCT user_id) reached_users,COUNT(DISTINCT CASE WHEN click_count=1 THEN user_id END) clicked_users,
 COUNT(DISTINCT adgroup_id) ad_units
FROM ${hivevar:ns}_dwd.exposure
LATERAL VIEW explode(array(
 named_struct('axis','hour','axis_value',CAST(event_hour AS STRING)),
 named_struct('axis','pid','axis_value',pid),
 named_struct('axis','adgroup','axis_value',adgroup_id),
 named_struct('axis','campaign','axis_value',CASE WHEN NOT ad_matched THEN '__unmatched_ad__' ELSE coalesce(campaign_id,'__missing_attribute__') END),
 named_struct('axis','customer','axis_value',CASE WHEN NOT ad_matched THEN '__unmatched_ad__' ELSE coalesce(customer_id,'__missing_attribute__') END),
 named_struct('axis','category','axis_value',CASE WHEN NOT ad_matched THEN '__unmatched_ad__' ELSE coalesce(cate_id,'__missing_attribute__') END),
 named_struct('axis','brand','axis_value',CASE WHEN NOT ad_matched THEN '__unmatched_ad__' ELSE coalesce(brand,'__missing_attribute__') END),
 named_struct('axis','gender','axis_value',CASE WHEN NOT profile_matched THEN '__unmatched_profile__' ELSE coalesce(gender_code,'__missing_attribute__') END),
 named_struct('axis','age','axis_value',CASE WHEN NOT profile_matched THEN '__unmatched_profile__' ELSE coalesce(age_level,'__missing_attribute__') END),
 named_struct('axis','shopping','axis_value',CASE WHEN NOT profile_matched THEN '__unmatched_profile__' ELSE coalesce(shopping_level,'__missing_attribute__') END),
 named_struct('axis','pvalue','axis_value',CASE WHEN NOT profile_matched THEN '__unmatched_profile__' ELSE coalesce(pvalue_level,'__missing_attribute__') END),
 named_struct('axis','occupation','axis_value',CASE WHEN NOT profile_matched THEN '__unmatched_profile__' ELSE coalesce(occupation,'__missing_attribute__') END),
 named_struct('axis','city','axis_value',CASE WHEN NOT profile_matched THEN '__unmatched_profile__' ELSE coalesce(city_level,'__missing_attribute__') END)
)) expanded AS k WHERE batch_id='${hivevar:batch}' GROUP BY dt,k.axis,k.axis_value;
CREATE TEMPORARY TABLE expected_overview STORED AS ORC AS
SELECT dt,impressions,clicks,CAST(clicks AS DOUBLE)/nullif(impressions,0) ctr,
reached_users,clicked_users,CAST(clicked_users AS DOUBLE)/nullif(reached_users,0) user_click_ratio,
ad_units,CAST(impressions AS DOUBLE)/nullif(reached_users,0) impressions_per_user,unmatched_profiles,unmatched_ads FROM expected_daily;
CREATE TEMPORARY TABLE expected_ads_axis STORED AS ORC AS
SELECT dt,axis,axis_value,impressions,clicks,CAST(clicks AS DOUBLE)/nullif(impressions,0) ctr,
 reached_users,clicked_users,CAST(clicked_users AS DOUBLE)/nullif(reached_users,0) user_click_ratio,
 ad_units,CAST(impressions AS DOUBLE)/nullif(reached_users,0) impressions_per_user,
 CAST(impressions AS DOUBLE)/nullif(SUM(impressions) OVER(PARTITION BY dt,axis),0) impression_share,
 CAST(clicks AS DOUBLE)/nullif(SUM(clicks) OVER(PARTITION BY dt,axis),0) click_share FROM expected_axis;
CREATE TEMPORARY TABLE expected_quality STORED AS ORC AS SELECT dt,impressions,matched_profile_impressions,reached_users,matched_profile_users,matched_ad_impressions,gender_missing,age_missing,shopping_missing,pvalue_missing,occupation_missing,city_missing,
CAST(matched_profile_impressions AS DOUBLE)/nullif(impressions,0) AS profile_row_coverage,
CAST(matched_profile_users AS DOUBLE)/nullif(reached_users,0) AS profile_user_coverage,
CAST(matched_ad_impressions AS DOUBLE)/nullif(impressions,0) AS ad_row_coverage,
CAST(gender_missing AS DOUBLE)/nullif(matched_profile_impressions,0) AS gender_missing_rate,
CAST(age_missing AS DOUBLE)/nullif(matched_profile_impressions,0) AS age_missing_rate,
CAST(shopping_missing AS DOUBLE)/nullif(matched_profile_impressions,0) AS shopping_missing_rate,
CAST(pvalue_missing AS DOUBLE)/nullif(matched_profile_impressions,0) AS pvalue_missing_rate,
CAST(occupation_missing AS DOUBLE)/nullif(matched_profile_impressions,0) AS occupation_missing_rate,
CAST(city_missing AS DOUBLE)/nullif(matched_profile_impressions,0) AS city_missing_rate FROM expected_daily;
CREATE TEMPORARY TABLE faulty_missing_axis STORED AS ORC AS SELECT * FROM ${hivevar:ns}_ads.daily_axis WHERE batch_id='${hivevar:batch}' AND axis<>'city';
CREATE TEMPORARY TABLE faulty_null_metric STORED AS ORC AS SELECT axis,axis_value,impressions,clicks,CAST(NULL AS DOUBLE) AS ctr,reached_users,clicked_users,user_click_ratio,ad_units,impressions_per_user,impression_share,click_share,batch_id,dt FROM ${hivevar:ns}_ads.daily_axis WHERE batch_id='${hivevar:batch}';
CREATE TEMPORARY TABLE faulty_duplicates STORED AS ORC AS SELECT * FROM ${hivevar:ns}_ads.daily_axis WHERE batch_id='${hivevar:batch}' UNION ALL SELECT * FROM ${hivevar:ns}_ads.daily_axis WHERE batch_id='${hivevar:batch}' AND axis='city';
SELECT assert_true(COUNT(*)>0) FROM expected_ads_axis e FULL OUTER JOIN
 (SELECT * FROM faulty_missing_axis WHERE batch_id='${hivevar:batch}') a ON e.dt=a.dt AND e.axis=a.axis AND e.axis_value=a.axis_value
WHERE e.dt IS NULL OR a.dt IS NULL OR NOT (e.impressions<=>a.impressions) OR NOT (e.clicks<=>a.clicks) OR NOT (e.ctr<=>a.ctr) OR NOT (e.reached_users<=>a.reached_users) OR NOT (e.clicked_users<=>a.clicked_users) OR NOT (e.user_click_ratio<=>a.user_click_ratio) OR NOT (e.ad_units<=>a.ad_units) OR NOT (e.impressions_per_user<=>a.impressions_per_user) OR NOT (e.impression_share<=>a.impression_share) OR NOT (e.click_share<=>a.click_share);
SELECT assert_true(COUNT(*)>0) FROM expected_ads_axis e FULL OUTER JOIN
 (SELECT * FROM faulty_null_metric WHERE batch_id='${hivevar:batch}') a ON e.dt=a.dt AND e.axis=a.axis AND e.axis_value=a.axis_value
WHERE e.dt IS NULL OR a.dt IS NULL OR NOT (e.impressions<=>a.impressions) OR NOT (e.clicks<=>a.clicks) OR NOT (e.ctr<=>a.ctr) OR NOT (e.reached_users<=>a.reached_users) OR NOT (e.clicked_users<=>a.clicked_users) OR NOT (e.user_click_ratio<=>a.user_click_ratio) OR NOT (e.ad_units<=>a.ad_units) OR NOT (e.impressions_per_user<=>a.impressions_per_user) OR NOT (e.impression_share<=>a.impression_share) OR NOT (e.click_share<=>a.click_share);
SELECT assert_true(COUNT(*)>0) FROM (SELECT dt,axis,axis_value FROM faulty_duplicates WHERE batch_id='${hivevar:batch}' GROUP BY dt,axis,axis_value HAVING COUNT(*)<>1) duplicate_rows;
SELECT 'SQL_V2_DEFECT_DETECTION_PASS' AS result;
SELECT assert_true(COUNT(*)=0) FROM expected_ads_axis e FULL OUTER JOIN
 (SELECT * FROM faulty_missing_axis WHERE batch_id='${hivevar:batch}') a ON e.dt=a.dt AND e.axis=a.axis AND e.axis_value=a.axis_value
WHERE e.dt IS NULL OR a.dt IS NULL OR NOT (e.impressions<=>a.impressions) OR NOT (e.clicks<=>a.clicks) OR NOT (e.ctr<=>a.ctr) OR NOT (e.reached_users<=>a.reached_users) OR NOT (e.clicked_users<=>a.clicked_users) OR NOT (e.user_click_ratio<=>a.user_click_ratio) OR NOT (e.ad_units<=>a.ad_units) OR NOT (e.impressions_per_user<=>a.impressions_per_user) OR NOT (e.impression_share<=>a.impression_share) OR NOT (e.click_share<=>a.click_share);