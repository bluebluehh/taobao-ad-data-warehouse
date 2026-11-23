#!/usr/bin/env python3
"""Generate the 17-row synthetic SQL v2 edge-case fixture, never production data."""
import argparse
from pathlib import Path
FILES = {
'ad_feature.csv': '''adgroup_id,cate_id,campaign_id,customer,brand,price
10,100,1000,10000,100000,9.9
20,200,2000,20000,,20
''',
'raw_sample.csv': '''user,time_stamp,adgroup_id,pid,nonclk,clk
1,1494000000,10,slot_a,1,0
1,1494000000,10,slot_a,1,0
2,1494003600,20,slot_b,0,1
3,1494086400,99,slot_a,0,1
1,1494086400,10,slot_b,0,1
4,1494086400,20,slot_b,0,0
1,1493999999,10,slot_a,1,0
1,1494691200,10,slot_a,1,0
2,1494691199,20,slot_c,0,1
1,bad_time,10,slot_a,1,0
,1494003600,10,slot_a,1,0
1,1494003600,,slot_a,1,0
1,1494003600,10,,1,0
1,1494003600,10,slot_a,2,-1
1,1494176400,10,slot_a,1,0
2,1494180000,10,slot_b,1,0
5,1494262800,99,slot_a,1,0
''',
'user_profile.csv': '''userid,cms_segid,cms_group_id,final_gender_code,age_level,pvalue_level,shopping_level,occupation,new_user_class_level 
1,1,1,1,3,2,2,0,1
2,2,2,,4,,3,1,
'''
}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=False)
    for name,text in FILES.items():(args.out/name).write_text(text)
    (args.out/'TECHNICAL_FIXTURE_ONLY').write_text('人工技术测试17条：有效9、拒绝8、点击4。禁止当作真实业务数据。\n')
    print('人工测试输入已生成；仅允许validation_*命名空间。')
if __name__=='__main__':main()
