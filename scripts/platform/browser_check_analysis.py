#!/usr/bin/env python3
"""Verify one synthetic exact-scope dashboard renders in a real browser."""
import argparse
import json
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dashboard',type=Path,required=True)
    args=parser.parse_args();report=json.loads(args.dashboard.read_text())
    if not report.get('technical_validation'):parser.error('此截图验证工具仅允许技术验证看板')
    private=json.loads(Path('/opt/taobao/data/reporting/credentials.json').read_text())
    profile=Path.home()/'snap/firefox/common/taobao-sql-v2';profile.mkdir(parents=True,exist_ok=True)
    options=Options();options.add_argument('-headless');options.page_load_strategy='eager'
    options.binary_location='/snap/firefox/current/usr/lib/firefox/firefox'
    options.set_preference('intl.accept_languages','zh-CN,zh,en-US,en')
    driver=webdriver.Firefox(options=options,service=Service('/snap/bin/geckodriver',
      service_args=['--profile-root',str(profile)],log_output=str(args.dashboard.parent/'browser-driver.log')))
    try:
        driver.set_page_load_timeout(60);driver.set_window_size(1800,1400)
        driver.get('http://127.0.0.1:8089/login/')
        wait=WebDriverWait(driver,90)
        wait.until(lambda d:d.find_element(By.CSS_SELECTOR,'input#username,input[name=username],input[type=text]')).send_keys('admin')
        driver.find_element(By.CSS_SELECTOR,'input[type=password]').send_keys(private['superset_admin'])
        driver.find_element(By.CSS_SELECTOR,'input[type=submit],button[type=submit],button.ant-btn-primary').click()
        wait.until(lambda d:'/login' not in d.current_url)
        driver.get(report['url'])
        wait.until(lambda d:len(d.find_elements(By.CSS_SELECTOR,'canvas'))>=1 and len(d.find_elements(By.CSS_SELECTOR,'table'))>=3)
        errors=[e.text for e in driver.find_elements(By.CSS_SELECTOR,'.ant-alert-error') if e.is_displayed()]
        if errors:raise RuntimeError(str(errors))
        wait.until(lambda d:'技术验证' in d.execute_script('return document.body.textContent'))
        body=driver.execute_script('return document.body.textContent')
        if '技术验证' not in body:raise RuntimeError('页面缺少技术验证标记')
        screenshot=args.dashboard.parent/'dashboard.png'
        driver.get_full_page_screenshot_as_file(str(screenshot))
        report.update(browser_verified=True,browser_errors=errors,screenshot=str(screenshot),
          browser_scope='login and render three tables and one bar chart; synthetic exact-scope only')
        args.dashboard.write_text(json.dumps(report,ensure_ascii=False,indent=2))
        (args.dashboard.parent/'browser-visible-text.txt').write_text(body)
        print(json.dumps({'browser_verified':True,'screenshot':str(screenshot)}))
    except BaseException:
        driver.save_screenshot(str(args.dashboard.parent/'browser-failure.png'));raise
    finally:driver.quit()
if __name__=='__main__':main()
