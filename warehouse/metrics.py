"""One metric implementation shared by ETL snapshots, API and validation."""
import sqlite3

GROUPS = {
    'date': 'date', 'hour': 'hour_key', 'resource': 'pid', 'campaign': 'campaign_id',
    'advertiser': 'customer_id', 'category': 'cate_id', 'brand': 'brand', 'ad': 'adgroup_id',
    'gender': "CASE WHEN profile_matched=0 THEN '未匹配画像' WHEN gender_code IS NULL THEN '属性缺失' ELSE '编码 '||gender_code END",
    'age': "CASE WHEN profile_matched=0 THEN '未匹配画像' WHEN age_level IS NULL THEN '属性缺失' ELSE '编码 '||age_level END",
    'shopping': "CASE WHEN profile_matched=0 THEN '未匹配画像' WHEN shopping_level IS NULL THEN '属性缺失' ELSE '编码 '||shopping_level END",
    'pvalue': "CASE WHEN profile_matched=0 THEN '未匹配画像' WHEN pvalue_level IS NULL THEN '属性缺失' ELSE '编码 '||pvalue_level END",
    'city': "CASE WHEN profile_matched=0 THEN '未匹配画像' WHEN city_level IS NULL THEN '属性缺失' ELSE '编码 '||city_level END",
}
AGG = '''COUNT(*) impressions, COALESCE(SUM(click_count),0) clicks,
 COUNT(DISTINCT user_id) reached_users,
 COUNT(DISTINCT CASE WHEN click_count=1 THEN user_id END) clicked_users,
 COUNT(DISTINCT adgroup_id) exposed_ads,
 COALESCE(SUM(profile_matched),0) matched_profile_rows,
 COUNT(DISTINCT CASE WHEN profile_matched=1 THEN user_id END) matched_profile_users,
 COALESCE(SUM(ad_matched),0) matched_ad_rows,
 COALESCE(SUM(CASE WHEN profile_matched=1 AND pvalue_level IS NULL THEN 1 ELSE 0 END),0) missing_pvalue_rows,
 COALESCE(SUM(CASE WHEN profile_matched=1 AND city_level IS NULL THEN 1 ELSE 0 END),0) missing_city_rows'''


def ratio(a, b):
    return a / b if b else None


def derive(row, total=None):
    d = dict(row)
    d.update(ctr=ratio(d['clicks'], d['impressions']),
             user_click_rate=ratio(d['clicked_users'], d['reached_users']),
             avg_impressions_per_user=ratio(d['impressions'], d['reached_users']),
             profile_row_coverage=ratio(d['matched_profile_rows'], d['impressions']),
             profile_user_coverage=ratio(d['matched_profile_users'], d['reached_users']),
             ad_row_coverage=ratio(d['matched_ad_rows'], d['impressions']),
             pvalue_missing_rate=ratio(d['missing_pvalue_rows'], d['matched_profile_rows']),
             city_missing_rate=ratio(d['missing_city_rows'], d['matched_profile_rows']))
    if total is not None:
        d['impression_share'] = ratio(d['impressions'], total['impressions'])
        d['click_share'] = ratio(d['clicks'], total['clicks'])
    return d


def scope(filters=None, quality=False):
    filters = filters or {}
    where, args = [], []
    for key, col in [('start', 'date'), ('end', 'date'), ('pid', 'pid'),
                     ('campaign', 'campaign_id'), ('category', 'cate_id')]:
        value = filters.get(key)
        if value not in (None, ''):
            op = '>=' if key == 'start' else '<=' if key == 'end' else '='
            where.append(f'{col}{op}?')
            args.append(value)
    if not quality:
        for key, col in [('gender', 'gender_code'), ('age', 'age_level'), ('shopping', 'shopping_level')]:
            value = filters.get(key)
            if value not in (None, ''):
                if value == '__unmatched__':
                    where.append('profile_matched=0')
                elif value == '__missing__':
                    where.append(f'profile_matched=1 AND {col} IS NULL')
                else:
                    where.append(f'profile_matched=1 AND {col}=?')
                    args.append(value)
    return 'SELECT * FROM v_exposure_detail' + (' WHERE ' + ' AND '.join(where) if where else ''), args


def overview(db, filters=None, quality=False):
    sql, args = scope(filters, quality)
    return derive(db.execute(f'WITH s AS ({sql}) SELECT {AGG} FROM s', args).fetchone())


def grouped(db, group, filters=None, *, second=None, limit=None, order='clicks', min_impressions=0):
    # Expressions are selected from this fixed dictionary; values are bound.
    if group not in GROUPS or (second and second not in GROUPS):
        raise ValueError('Unsupported grouping')
    if order not in ('clicks', 'ctr', 'key'):
        raise ValueError('Unsupported ordering')
    sql, args = scope(filters)
    expr = f"COALESCE(CAST({GROUPS[group]} AS TEXT),'未知') AS group_key"
    expr += f", COALESCE(CAST({GROUPS[second]} AS TEXT),'未知') AS second_key" if second else ''
    cols = 'group_key,second_key' if second else 'group_key'
    sort = 'group_key,second_key' if second else 'group_key'
    if order == 'key':
        # ISO date sorts lexically; hour is displayed chronologically as integer.
        sort = 'CAST(group_key AS INTEGER)' if group == 'hour' and not second else sort
    else:
        sort = ('1.0*clicks/NULLIF(impressions,0) DESC,' if order == 'ctr' else 'clicks DESC,') + 'impressions DESC,' + cols
    query = f'WITH s AS ({sql}), g AS (SELECT {expr},{AGG} FROM s GROUP BY {cols}) SELECT * FROM g WHERE impressions>=? ORDER BY {sort}'
    args.append(int(min_impressions))
    if limit is not None:
        query += ' LIMIT ?'
        args.append(int(limit))
    total = overview(db, filters)
    return [derive(row, total) for row in db.execute(query, args)]


def bundle(db, filters=None, group='campaign', order='clicks', minimum=1000):
    # Materialize this request's non-profile scope once, in temporary storage.
    # The server opens the main file mode=ro: only temporary query data is written.
    before = db.execute('PRAGMA query_only').fetchone()[0]
    db.execute('PRAGMA query_only=OFF')
    sql, args = scope(filters, quality=True)
    sql = sql.replace('FROM v_exposure_detail', 'FROM main.v_exposure_detail')
    db.execute('CREATE TEMP TABLE ads_query_scope AS '+sql, args)
    db.execute('CREATE TEMP VIEW v_exposure_detail AS SELECT * FROM ads_query_scope')
    try:
        return _bundle(db, filters, group, order, minimum)
    finally:
        db.execute('DROP VIEW temp.v_exposure_detail')
        db.execute('DROP TABLE temp.ads_query_scope')
        db.execute('PRAGMA query_only='+str(before))


def audience_series(db, group, filters=None):
    # Charts need counts and CTR only; avoid unnecessary DISTINCT aggregations.
    if group not in ('gender', 'shopping', 'pvalue'):
        raise ValueError('Unsupported audience chart')
    sql, args = scope(filters)
    expr = GROUPS[group]
    rows = db.execute(f'''WITH s AS ({sql}) SELECT {expr} group_key,
        COUNT(*) impressions, SUM(click_count) clicks FROM s
        GROUP BY group_key ORDER BY group_key''', args)
    return [dict(row, ctr=ratio(row['clicks'], row['impressions'])) for row in rows]


def _bundle(db, filters=None, group='campaign', order='clicks', minimum=1000):
    filters = filters or {}
    return {'filters': filters, 'overview': overview(db, filters),
            'quality': overview(db, filters, quality=True),
            'quality_scope_note': '画像筛选前；保留日期、资源位、计划及类目筛选',
            'daily': grouped(db, 'date', filters, order='key'),
            'hourly': grouped(db, 'hour', filters, order='key'),
            'resources': grouped(db, 'resource', filters, order='key'),
            'audience': grouped(db, 'age', filters, order='key'),
            'audiences': {key: audience_series(db, key, filters)
                          for key in ['gender', 'shopping', 'pvalue']},
            'ranking': grouped(db, group, filters, limit=20, order=order,
                               min_impressions=minimum if order == 'ctr' else 0),
            'cross': grouped(db, 'resource', filters, second='age', order='key'),
            'ranking_group': group, 'ranking_order': order,
            'ranking_min_impressions': minimum if order == 'ctr' else 0,
            'ranking_shares_before_top_n': True}


def connect(path):
    from pathlib import Path
    db = sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA query_only=ON')
    return db
