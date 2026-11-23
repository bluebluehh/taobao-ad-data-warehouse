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
WHERE batch_id='${hivevar:batch}' AND dt BETWEEN '${hivevar:start_date}' AND '${hivevar:end_date}';
