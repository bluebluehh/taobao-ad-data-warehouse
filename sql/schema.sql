PRAGMA foreign_keys=ON;
CREATE TABLE source_inventory(name TEXT PRIMARY KEY, path TEXT NOT NULL, sha256 TEXT NOT NULL,
    rows INTEGER NOT NULL, bytes INTEGER NOT NULL, original_header TEXT NOT NULL);
CREATE TABLE run_info(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE ods_ad(source_line INTEGER PRIMARY KEY,adgroup_id TEXT,cate_id TEXT,
    campaign_id TEXT,customer TEXT,brand TEXT,price TEXT);
CREATE TABLE ods_user(source_line INTEGER PRIMARY KEY,userid TEXT,cms_segid TEXT,cms_group_id TEXT,
    final_gender_code TEXT,age_level TEXT,pvalue_level TEXT,shopping_level TEXT,
    occupation TEXT,new_user_class_level TEXT);
CREATE TABLE ods_exposure(source_line INTEGER PRIMARY KEY,user TEXT,time_stamp TEXT,
    adgroup_id TEXT,pid TEXT,nonclk TEXT,clk TEXT);
CREATE TABLE ods_reject(source TEXT,source_line INTEGER,reason TEXT,raw_text TEXT);
CREATE TABLE dim_user(user_sk INTEGER PRIMARY KEY,user_id TEXT NOT NULL UNIQUE,
    cms_segid TEXT,cms_group_id TEXT,gender_code TEXT,age_level TEXT,pvalue_level TEXT,
    shopping_level TEXT,occupation TEXT,city_level TEXT,profile_matched INTEGER NOT NULL CHECK(profile_matched IN(0,1)));
CREATE TABLE dim_ad(ad_sk INTEGER PRIMARY KEY,adgroup_id TEXT NOT NULL UNIQUE,
    cate_id TEXT,campaign_id TEXT,customer_id TEXT,brand TEXT,price REAL,
    ad_matched INTEGER NOT NULL CHECK(ad_matched IN(0,1)));
CREATE TABLE dim_date(date_key INTEGER PRIMARY KEY,date TEXT UNIQUE,year INTEGER,month INTEGER,
    day INTEGER,weekday INTEGER);
CREATE TABLE dim_hour(hour_key INTEGER PRIMARY KEY CHECK(hour_key BETWEEN 0 AND 23),label TEXT);
CREATE TABLE dim_resource(pid TEXT PRIMARY KEY);
CREATE TABLE dwd_exposure(source_line INTEGER PRIMARY KEY REFERENCES ods_exposure(source_line),
    user_sk INTEGER NOT NULL REFERENCES dim_user(user_sk),ad_sk INTEGER NOT NULL REFERENCES dim_ad(ad_sk),
    date_key INTEGER NOT NULL REFERENCES dim_date(date_key),hour_key INTEGER NOT NULL REFERENCES dim_hour(hour_key),
    pid TEXT NOT NULL REFERENCES dim_resource(pid),event_ts INTEGER NOT NULL,
    impression_count INTEGER NOT NULL DEFAULT 1 CHECK(impression_count=1),
    click_count INTEGER NOT NULL CHECK(click_count IN(0,1)));
CREATE VIEW v_exposure_detail AS
SELECT f.*,d.date,u.user_id,u.gender_code,u.age_level,u.pvalue_level,u.shopping_level,
    u.occupation,u.city_level,u.profile_matched,a.adgroup_id,a.cate_id,a.campaign_id,
    a.customer_id,a.brand,a.price,a.ad_matched
FROM dwd_exposure f JOIN dim_user u USING(user_sk) JOIN dim_ad a USING(ad_sk)
JOIN dim_date d USING(date_key);
