-- Row conservation and source-line uniqueness are mandatory before aggregation.
SELECT assert_true(s.n=v.n+r.n) FROM
 (SELECT COUNT(*) n FROM ${hivevar:ns}_ods.raw_sample WHERE batch_id='${hivevar:batch}') s
 CROSS JOIN (SELECT COUNT(*) n FROM ${hivevar:ns}_dwd.exposure WHERE batch_id='${hivevar:batch}') v
 CROSS JOIN (SELECT COUNT(*) n FROM ${hivevar:ns}_dwd.rejected_exposure WHERE batch_id='${hivevar:batch}') r;
SELECT assert_true(COUNT(*)=0) FROM (
 SELECT source_file,source_line FROM ${hivevar:ns}_dwd.exposure WHERE batch_id='${hivevar:batch}'
 GROUP BY source_file,source_line HAVING COUNT(*)<>1
) duplicated_fact;
SELECT assert_true(COUNT(*)=0) FROM ${hivevar:ns}_dwd.exposure
WHERE batch_id='${hivevar:batch}' AND (click_count NOT IN (0,1) OR event_hour NOT BETWEEN 0 AND 23 OR dt IS NULL);
SELECT dt, COUNT(*) impressions,SUM(click_count) clicks,
 SUM(CASE WHEN NOT profile_matched THEN 1 ELSE 0 END) unmatched_profiles,
 SUM(CASE WHEN profile_matched AND gender_code IS NULL THEN 1 ELSE 0 END) matched_missing_gender
FROM ${hivevar:ns}_dwd.exposure WHERE batch_id='${hivevar:batch}' GROUP BY dt ORDER BY dt;
SELECT assert_true(coalesce(s.clicks,0)=coalesce(d.clicks,0)) FROM (
 SELECT SUM(CAST(trim(o.clk) AS BIGINT)) clicks
 FROM ${hivevar:ns}_ods.raw_sample o LEFT JOIN ${hivevar:ns}_dwd.rejected_exposure r
 ON o.batch_id=r.batch_id AND o.source_file=r.source_file AND o.source_line=r.source_line
 WHERE o.batch_id='${hivevar:batch}' AND r.source_line IS NULL
) s CROSS JOIN (
 SELECT SUM(click_count) clicks FROM ${hivevar:ns}_dwd.exposure WHERE batch_id='${hivevar:batch}'
) d;

-- Both sides must remain disjoint, traceable and within the manifest's business period.
SELECT assert_true(COUNT(*)=0) FROM ${hivevar:ns}_dwd.exposure
WHERE batch_id='${hivevar:batch}' AND
 (source_file IS NULL OR source_line IS NULL OR source_line<2
  OR dt NOT BETWEEN '${hivevar:start_date}' AND '${hivevar:end_date}'
  OR profile_matched IS NULL OR ad_matched IS NULL);
SELECT assert_true(COUNT(*)=0) FROM (
 SELECT source_file,source_line FROM ${hivevar:ns}_dwd.rejected_exposure
 WHERE batch_id='${hivevar:batch}' GROUP BY source_file,source_line HAVING COUNT(*)<>1
) duplicate_rejects;
SELECT assert_true(COUNT(*)=0) FROM ${hivevar:ns}_dwd.exposure e
 JOIN ${hivevar:ns}_dwd.rejected_exposure r
 ON e.batch_id=r.batch_id AND e.source_file=r.source_file AND e.source_line=r.source_line
 WHERE e.batch_id='${hivevar:batch}';
SELECT assert_true(COUNT(*)=0) FROM ${hivevar:ns}_dwd.rejected_exposure
WHERE batch_id='${hivevar:batch}' AND (reason IS NULL OR source_file IS NULL OR source_line IS NULL);
