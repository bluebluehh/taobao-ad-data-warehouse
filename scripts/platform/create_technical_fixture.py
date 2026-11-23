#!/usr/bin/env python3
"""Create an explicitly marked synthetic fixture for platform tests, never business analysis."""
import argparse
from pathlib import Path

FILES={
'raw_sample.csv':'''user,time_stamp,adgroup_id,pid,nonclk,clk
1,1494000000,10,slot_a,1,0
1,1494000000,10,slot_a,1,0
2,1494003600,20,slot_b,0,1
3,1494086400,99,slot_a,0,1
1,1494086400,10,slot_b,0,1
4,1494086400,20,slot_b,0,0
''',
'ad_feature.csv':'''adgroup_id,cate_id,campaign_id,customer,brand,price
10,100,1000,10000,100000,9.9
20,200,2000,20000,,20
''',
'user_profile.csv':'''userid,cms_segid,cms_group_id,final_gender_code,age_level,pvalue_level,shopping_level,occupation,new_user_class_level
1,1,1,1,3,2,2,0,1
2,2,2,,4,,3,1,
'''}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    for name,data in FILES.items():(args.out/name).write_text(data)
    (args.out/'TECHNICAL_FIXTURE_ONLY').write_text('人工技术测试专用。禁止作为课程真实业务数据或导入taobao正式命名空间。\n')
    print('已创建人工技术测试输入，必须使用validation_*命名空间；禁止当作真实广告数据。')

if __name__=='__main__':main()
