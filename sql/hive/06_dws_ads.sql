SET hive.exec.dynamic.partition=true;
SET hive.exec.dynamic.partition.mode=nonstrict;
INSERT OVERWRITE TABLE ${hivevar:ns}_dws.daily_stats PARTITION(batch_id='${hivevar:batch}',dt)
SELECT COUNT(*),SUM(click_count),COUNT(DISTINCT user_id),
 COUNT(DISTINCT CASE WHEN click_count=1 THEN user_id ELSE NULL END),
 COUNT(DISTINCT adgroup_id),SUM(CASE WHEN NOT profile_matched THEN 1 ELSE 0 END),
 SUM(CASE WHEN NOT ad_matched THEN 1 ELSE 0 END),dt
FROM ${hivevar:ns}_dwd.exposure WHERE batch_id='${hivevar:batch}' GROUP BY dt;
INSERT OVERWRITE TABLE ${hivevar:ns}_dws.axis_stats PARTITION(batch_id='${hivevar:batch}',dt)
SELECT k.axis,k.axis_value,COUNT(*),SUM(click_count),COUNT(DISTINCT user_id),
 COUNT(DISTINCT CASE WHEN click_count=1 THEN user_id ELSE NULL END),COUNT(DISTINCT adgroup_id),dt
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
 named_struct('axis','shopping','axis_value',CASE WHEN NOT profile_matched THEN '__unmatched_profile__' ELSE coalesce(shopping_level,'__missing_attribute__') END),
 named_struct('axis','pvalue','axis_value',CASE WHEN NOT profile_matched THEN '__unmatched_profile__' ELSE coalesce(pvalue_level,'__missing_attribute__') END),
 named_struct('axis','age','axis_value',CASE WHEN NOT profile_matched THEN '__unmatched_profile__' ELSE coalesce(age_level,'__missing_attribute__') END),
 named_struct('axis','occupation','axis_value',CASE WHEN NOT profile_matched THEN '__unmatched_profile__' ELSE coalesce(occupation,'__missing_attribute__') END),
 named_struct('axis','city','axis_value',CASE WHEN NOT profile_matched THEN '__unmatched_profile__' ELSE coalesce(city_level,'__missing_attribute__') END)
)) exploded AS k
WHERE batch_id='${hivevar:batch}' GROUP BY dt,k.axis,k.axis_value;
INSERT OVERWRITE TABLE ${hivevar:ns}_ads.daily_overview PARTITION(batch_id='${hivevar:batch}',dt)
SELECT impressions,clicks,CAST(clicks AS DOUBLE)/nullif(impressions,0),reached_users,clicked_users,
 CAST(clicked_users AS DOUBLE)/nullif(reached_users,0),ad_units,
 CAST(impressions AS DOUBLE)/nullif(reached_users,0),unmatched_profiles,unmatched_ads,dt
FROM ${hivevar:ns}_dws.daily_stats WHERE batch_id='${hivevar:batch}';
-- Shares use all rows in each day/axis, BEFORE any top-N filter.
INSERT OVERWRITE TABLE ${hivevar:ns}_ads.daily_axis PARTITION(batch_id='${hivevar:batch}',dt)
SELECT axis,axis_value,impressions,clicks,CAST(clicks AS DOUBLE)/nullif(impressions,0),
 reached_users,clicked_users,CAST(clicked_users AS DOUBLE)/nullif(reached_users,0),ad_units,
 CAST(impressions AS DOUBLE)/nullif(reached_users,0),
 CAST(impressions AS DOUBLE)/nullif(SUM(impressions) OVER(PARTITION BY dt,axis),0),
 CAST(clicks AS DOUBLE)/nullif(SUM(clicks) OVER(PARTITION BY dt,axis),0),dt
FROM ${hivevar:ns}_dws.axis_stats WHERE batch_id='${hivevar:batch}';

-- Q01/Q02/Q03 use separate exposure and exact-user denominators. Q04 excludes unmatched profiles.
INSERT OVERWRITE TABLE ${hivevar:ns}_dws.daily_quality PARTITION(batch_id='${hivevar:batch}',dt)
SELECT COUNT(*),
 SUM(CASE WHEN profile_matched THEN 1 ELSE 0 END),
 COUNT(DISTINCT user_id),
 COUNT(DISTINCT CASE WHEN profile_matched THEN user_id END),
 SUM(CASE WHEN ad_matched THEN 1 ELSE 0 END),
 SUM(CASE WHEN profile_matched AND gender_code IS NULL THEN 1 ELSE 0 END),
 SUM(CASE WHEN profile_matched AND age_level IS NULL THEN 1 ELSE 0 END),
 SUM(CASE WHEN profile_matched AND shopping_level IS NULL THEN 1 ELSE 0 END),
 SUM(CASE WHEN profile_matched AND pvalue_level IS NULL THEN 1 ELSE 0 END),
 SUM(CASE WHEN profile_matched AND occupation IS NULL THEN 1 ELSE 0 END),
 SUM(CASE WHEN profile_matched AND city_level IS NULL THEN 1 ELSE 0 END),dt
FROM ${hivevar:ns}_dwd.exposure WHERE batch_id='${hivevar:batch}' GROUP BY dt;
INSERT OVERWRITE TABLE ${hivevar:ns}_ads.daily_quality PARTITION(batch_id='${hivevar:batch}',dt)
SELECT impressions, matched_profile_impressions, reached_users, matched_profile_users, matched_ad_impressions, gender_missing, age_missing, shopping_missing, pvalue_missing, occupation_missing, city_missing,
 CAST(matched_profile_impressions AS DOUBLE)/nullif(impressions,0),
 CAST(matched_profile_users AS DOUBLE)/nullif(reached_users,0),
 CAST(matched_ad_impressions AS DOUBLE)/nullif(impressions,0),
 CAST(gender_missing AS DOUBLE)/nullif(matched_profile_impressions,0),
 CAST(age_missing AS DOUBLE)/nullif(matched_profile_impressions,0),
 CAST(shopping_missing AS DOUBLE)/nullif(matched_profile_impressions,0),
 CAST(pvalue_missing AS DOUBLE)/nullif(matched_profile_impressions,0),
 CAST(occupation_missing AS DOUBLE)/nullif(matched_profile_impressions,0),
 CAST(city_missing AS DOUBLE)/nullif(matched_profile_impressions,0),dt
FROM ${hivevar:ns}_dws.daily_quality WHERE batch_id='${hivevar:batch}';
