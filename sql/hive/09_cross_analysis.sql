-- Render through query_metrics.py. Denominators precede threshold and Top N.
WITH grouped AS (
 SELECT ${hivevar:group_select},
 COUNT(*) impressions,SUM(click_count) clicks,COUNT(DISTINCT user_id) reached_users,
 COUNT(DISTINCT CASE WHEN click_count=1 THEN user_id END) clicked_users,
 COUNT(DISTINCT adgroup_id) ad_units
 FROM ${hivevar:ns}_dwd.exposure
 WHERE batch_id='${hivevar:batch}' AND dt BETWEEN '${hivevar:start_date}' AND '${hivevar:end_date}'
 ${hivevar:extra_filters}
 GROUP BY ${hivevar:group_by}
), scored AS (
 SELECT *,CAST(clicks AS DOUBLE)/nullif(impressions,0) ctr,
 CAST(clicked_users AS DOUBLE)/nullif(reached_users,0) user_click_ratio,
 CAST(impressions AS DOUBLE)/nullif(reached_users,0) impressions_per_user,
 CAST(impressions AS DOUBLE)/nullif(SUM(impressions) OVER(),0) impression_share,
 CAST(clicks AS DOUBLE)/nullif(SUM(clicks) OVER(),0) click_share
 FROM grouped
)
SELECT ${hivevar:group_columns},impressions,clicks,ctr,reached_users,clicked_users,
 user_click_ratio,ad_units,impressions_per_user,impression_share,click_share
FROM scored WHERE impressions>=${hivevar:minimum}
ORDER BY ${hivevar:sort_columns} LIMIT ${hivevar:limit};
