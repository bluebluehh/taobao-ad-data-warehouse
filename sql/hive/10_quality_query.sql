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
 WHERE batch_id='${hivevar:batch}' AND dt BETWEEN '${hivevar:start_date}' AND '${hivevar:end_date}'
 ${hivevar:extra_filters}
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
