#!/usr/bin/env python3
"""Validate the native dashboard in headless Firefox; screenshots contain only technical data."""
import json
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

ROOT=Path(__file__).resolve().parents[2]
secret=json.loads(Path('/opt/taobao/data/reporting/credentials.json').read_text())
report_file=ROOT/'output/platform_checks/next-stage/superset-dashboard.json'
report=json.loads(report_file.read_text())
output=ROOT/'output/screenshots';output.mkdir(exist_ok=True)
profile_root=Path('/home/student/snap/firefox/common/taobao-ad-browser-validation');profile_root.mkdir(mode=0o700,exist_ok=True)
options=Options();options.page_load_strategy='eager';options.add_argument('-headless');options.binary_location='/snap/firefox/current/usr/lib/firefox/firefox'
options.set_preference('intl.accept_languages','zh-CN,zh,en-US,en')
service=Service(executable_path='/snap/bin/geckodriver',service_args=['--profile-root',str(profile_root)],log_output=str(output/'geckodriver.log'))
driver=webdriver.Firefox(options=options,service=service)
try:
    driver.set_page_load_timeout(60)
    driver.set_window_size(1600,1400)
    print('浏览器已启动，开始登录本机Superset',flush=True)
    driver.get('http://127.0.0.1:8089/login/')
    wait=WebDriverWait(driver,90)
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR,'input#username,input[name=username],input[autocomplete=username],input[type=text]'))).send_keys('admin')
    driver.find_element(By.CSS_SELECTOR,'input[type=password]').send_keys(secret['superset_admin'])
    driver.find_element(By.CSS_SELECTOR,'input[type=submit],button[type=submit],button.ant-btn-primary').click()
    wait.until(lambda d:'/login' not in d.current_url)
    print('登录通过，加载技术看板',flush=True)
    driver.get(report['dashboard_url'])
    wait.until(lambda d:'投放概览' in d.find_element(By.TAG_NAME,'body').text)
    wait.until(lambda d:len(d.find_elements(By.CSS_SELECTOR,'canvas'))>=1 and len(d.find_elements(By.CSS_SELECTOR,'table'))>=3)
    text=driver.find_element(By.TAG_NAME,'body').text
    errors=[e.text for e in driver.find_elements(By.CSS_SELECTOR,'.ant-alert-error') if e.is_displayed()]
    if errors:raise RuntimeError('看板显示错误：'+str(errors))
    if '画像未匹配' not in text or '属性缺失' not in text:raise RuntimeError('页面未显示两个独立未知人群类别')
    screenshot=output/'superset-technical-dashboard.png'
    driver.get_full_page_screenshot_as_file(str(screenshot))
    result={'technical_validation':True,'page_title':driver.title,'url':driver.current_url,
      'canvas_count':len(driver.find_elements(By.CSS_SELECTOR,'canvas')),'table_count':len(driver.find_elements(By.CSS_SELECTOR,'table')),
      'separate_unknown_groups_visible':True,'screenshot':str(screenshot),'errors':errors,
      'scope':'login, load native dashboard, render four charts, separate unknown groups; not all future interactions'}
    (output/'superset-browser-check.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    report['browser_visual_acceptance']='render_checks_passed_pending_screenshot_review'
    report_file.write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps(result,ensure_ascii=False,indent=2))
except Exception:
    driver.save_screenshot(str(output/'superset-technical-failure.png'))
    raise
finally:driver.quit()
