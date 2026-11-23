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
SELECT assert_true(COUNT(*)=0) FROM (SELECT dt FROM ${hivevar:ns}_dws.daily_stats WHERE batch_id='${hivevar:batch}' GROUP BY dt HAVING COUNT(*)<>1) duplicate_rows;
SELECT assert_true(COUNT(*)=0) FROM expected_daily e FULL OUTER JOIN
 (SELECT * FROM ${hivevar:ns}_dws.daily_stats WHERE batch_id='${hivevar:batch}') a ON e.dt=a.dt
WHERE e.dt IS NULL OR a.dt IS NULL OR NOT (e.impressions<=>a.impressions) OR NOT (e.clicks<=>a.clicks) OR NOT (e.reached_users<=>a.reached_users) OR NOT (e.clicked_users<=>a.clicked_users) OR NOT (e.ad_units<=>a.ad_units) OR NOT (e.unmatched_profiles<=>a.unmatched_profiles) OR NOT (e.unmatched_ads<=>a.unmatched_ads);
SELECT assert_true(COUNT(*)=0) FROM (SELECT dt FROM ${hivevar:ns}_ads.daily_overview WHERE batch_id='${hivevar:batch}' GROUP BY dt HAVING COUNT(*)<>1) duplicate_rows;
SELECT assert_true(COUNT(*)=0) FROM expected_overview e FULL OUTER JOIN
 (SELECT * FROM ${hivevar:ns}_ads.daily_overview WHERE batch_id='${hivevar:batch}') a ON e.dt=a.dt
WHERE e.dt IS NULL OR a.dt IS NULL OR NOT (e.impressions<=>a.impressions) OR NOT (e.clicks<=>a.clicks) OR NOT (e.ctr<=>a.ctr) OR NOT (e.reached_users<=>a.reached_users) OR NOT (e.clicked_users<=>a.clicked_users) OR NOT (e.user_click_ratio<=>a.user_click_ratio) OR NOT (e.ad_units<=>a.ad_units) OR NOT (e.impressions_per_user<=>a.impressions_per_user) OR NOT (e.unmatched_profiles<=>a.unmatched_profiles) OR NOT (e.unmatched_ads<=>a.unmatched_ads);
SELECT assert_true(COUNT(*)=0) FROM (SELECT dt,axis,axis_value FROM ${hivevar:ns}_dws.axis_stats WHERE batch_id='${hivevar:batch}' GROUP BY dt,axis,axis_value HAVING COUNT(*)<>1) duplicate_rows;
SELECT assert_true(COUNT(*)=0) FROM expected_axis e FULL OUTER JOIN
 (SELECT * FROM ${hivevar:ns}_dws.axis_stats WHERE batch_id='${hivevar:batch}') a ON e.dt=a.dt AND e.axis=a.axis AND e.axis_value=a.axis_value
WHERE e.dt IS NULL OR a.dt IS NULL OR NOT (e.impressions<=>a.impressions) OR NOT (e.clicks<=>a.clicks) OR NOT (e.reached_users<=>a.reached_users) OR NOT (e.clicked_users<=>a.clicked_users) OR NOT (e.ad_units<=>a.ad_units);
SELECT assert_true(COUNT(*)=0) FROM (SELECT dt,axis,axis_value FROM ${hivevar:ns}_ads.daily_axis WHERE batch_id='${hivevar:batch}' GROUP BY dt,axis,axis_value HAVING COUNT(*)<>1) duplicate_rows;
SELECT assert_true(COUNT(*)=0) FROM expected_ads_axis e FULL OUTER JOIN
 (SELECT * FROM ${hivevar:ns}_ads.daily_axis WHERE batch_id='${hivevar:batch}') a ON e.dt=a.dt AND e.axis=a.axis AND e.axis_value=a.axis_value
WHERE e.dt IS NULL OR a.dt IS NULL OR NOT (e.impressions<=>a.impressions) OR NOT (e.clicks<=>a.clicks) OR NOT (e.ctr<=>a.ctr) OR NOT (e.reached_users<=>a.reached_users) OR NOT (e.clicked_users<=>a.clicked_users) OR NOT (e.user_click_ratio<=>a.user_click_ratio) OR NOT (e.ad_units<=>a.ad_units) OR NOT (e.impressions_per_user<=>a.impressions_per_user) OR NOT (e.impression_share<=>a.impression_share) OR NOT (e.click_share<=>a.click_share);
SELECT assert_true(COUNT(*)=0) FROM (SELECT dt FROM ${hivevar:ns}_dws.daily_quality WHERE batch_id='${hivevar:batch}' GROUP BY dt HAVING COUNT(*)<>1) duplicate_rows;
SELECT assert_true(COUNT(*)=0) FROM expected_daily e FULL OUTER JOIN
 (SELECT * FROM ${hivevar:ns}_dws.daily_quality WHERE batch_id='${hivevar:batch}') a ON e.dt=a.dt
WHERE e.dt IS NULL OR a.dt IS NULL OR NOT (e.impressions<=>a.impressions) OR NOT (e.matched_profile_impressions<=>a.matched_profile_impressions) OR NOT (e.reached_users<=>a.reached_users) OR NOT (e.matched_profile_users<=>a.matched_profile_users) OR NOT (e.matched_ad_impressions<=>a.matched_ad_impressions) OR NOT (e.gender_missing<=>a.gender_missing) OR NOT (e.age_missing<=>a.age_missing) OR NOT (e.shopping_missing<=>a.shopping_missing) OR NOT (e.pvalue_missing<=>a.pvalue_missing) OR NOT (e.occupation_missing<=>a.occupation_missing) OR NOT (e.city_missing<=>a.city_missing);
SELECT assert_true(COUNT(*)=0) FROM (SELECT dt FROM ${hivevar:ns}_ads.daily_quality WHERE batch_id='${hivevar:batch}' GROUP BY dt HAVING COUNT(*)<>1) duplicate_rows;
SELECT assert_true(COUNT(*)=0) FROM expected_quality e FULL OUTER JOIN
 (SELECT * FROM ${hivevar:ns}_ads.daily_quality WHERE batch_id='${hivevar:batch}') a ON e.dt=a.dt
WHERE e.dt IS NULL OR a.dt IS NULL OR NOT (e.impressions<=>a.impressions) OR NOT (e.matched_profile_impressions<=>a.matched_profile_impressions) OR NOT (e.reached_users<=>a.reached_users) OR NOT (e.matched_profile_users<=>a.matched_profile_users) OR NOT (e.matched_ad_impressions<=>a.matched_ad_impressions) OR NOT (e.gender_missing<=>a.gender_missing) OR NOT (e.age_missing<=>a.age_missing) OR NOT (e.shopping_missing<=>a.shopping_missing) OR NOT (e.pvalue_missing<=>a.pvalue_missing) OR NOT (e.occupation_missing<=>a.occupation_missing) OR NOT (e.city_missing<=>a.city_missing) OR NOT (e.profile_row_coverage<=>a.profile_row_coverage) OR NOT (e.profile_user_coverage<=>a.profile_user_coverage) OR NOT (e.ad_row_coverage<=>a.ad_row_coverage) OR NOT (e.gender_missing_rate<=>a.gender_missing_rate) OR NOT (e.age_missing_rate<=>a.age_missing_rate) OR NOT (e.shopping_missing_rate<=>a.shopping_missing_rate) OR NOT (e.pvalue_missing_rate<=>a.pvalue_missing_rate) OR NOT (e.occupation_missing_rate<=>a.occupation_missing_rate) OR NOT (e.city_missing_rate<=>a.city_missing_rate);
SELECT 'ALL_LAYER_FIELDS_RECONCILED' AS validation_result;
