from zoneinfo import ZoneInfo
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
import os
import sys
import json
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

URL = "https://sell.pia.jp/inbound/selectTicket.php?eventCd=2601912&rlsCd=003&langCd=eng"
LOG_FILE = "check_log.json"

def get_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver

def load_log():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            return json.load(f)
    return []

def save_log(log):
    with open(LOG_FILE, "w") as f:
        json.dump(log, f)

def check_tickets():
    log = load_log()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    result = "無票"

    try:
        driver = get_driver()
        driver.get(URL)
        time.sleep(10)
        html = driver.page_source
        driver.quit()

        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text()

        # 確認頁面載入
        if "Kokugikan" not in text:
            result = "頁面載入異常"
            print(f"[{now}] {result}")
            log.append({"time": now, "result": result})
            save_log(log)
            return

        # 無票條件
        no_ticket_keywords = ["Goes on sale", "SOLD OUT", "売り切れ", "完売"]
        if any(kw in text for kw in no_ticket_keywords):
            result = "無票"
            print(f"[{now}] {result}")
            log.append({"time": now, "result": result})
            save_log(log)
            return

        # 找目標日期的 dropdown 選項
        target_found = {}
        select_elem = soup.find("select")
        if select_elem:
            for opt in select_elem.find_all("option"):
                opt_text = opt.get_text()
                if "May 20" in opt_text:
                    target_found["5月20日"] = opt.get("value", "")
                if "May 22" in opt_text:
                    target_found["5月22日"] = opt.get("value", "")

        if not target_found:
            result = "無票（找不到目標場次）"
            print(f"[{now}] {result}")
            log.append({"time": now, "result": result})
            save_log(log)
            return

        # 確認有 ○ 或 △（Available 或 Only few left）
        available_radios = soup.find_all("input", {"type": "radio"})
        has_available = any(not r.get("disabled") for r in available_radios)
        has_available_text = "Available" in text or "Only few left" in text

        if not has_available and not has_available_text:
            result = "無票（全部 Sold out）"
            print(f"[{now}] {result}")
            log.append({"time": now, "result": result})
            save_log(log)
            return

        # 有票！
        matched = " ".join(target_found.keys())
        result = f"有票！{matched}"
        print(f"[{now}] {result}")
        log.append({"time": now, "result": result})
        save_log(log)
        send_alert(matched)

    except Exception as e:
        result = f"錯誤：{e}"
        print(f"[{now}] {result}")
        log.append({"time": now, "result": result})
        save_log(log)
        sys.exit(1)

def send_alert(dates):
    now = datetime.now(ZoneInfo("Asia/Taipei")).strftime("%Y-%m-%d %H:%M")
    subject = f"🎫 有票了！{dates} 場次有票！"
    body = f"""有票了！請立刻前往購買！

場次：{dates}
網址：{URL}
檢查時間：{now}
"""
    send_email(subject, body)
    print(f"[{now}] ✅ 有票通知已發送！{dates}")

def send_daily_summary():
    log = load_log()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    total = len(log)
    found = [r for r in log if "有票" in r["result"]]
    no_ticket = [r for r in log if r["result"] == "無票"]
    errors = [r for r in log if "錯誤" in r["result"] or "異常" in r["result"]]
    detail = "\n".join([f"{r['time']} - {r['result']}" for r in log]) or "無紀錄"

    subject = f"📊 搶票監控每日報告 {datetime.now().strftime('%Y-%m-%d')}"
    body = f"""過去24小時監控摘要

總共檢查：{total} 次
無票：{len(no_ticket)} 次
有票：{len(found)} 次
異常：{len(errors)} 次

詳細紀錄：
{detail}

監控網址：{URL}
報告時間：{now}
"""
    send_email(subject, body)
    print(f"[{now}] 📊 每日報告已發送")
    save_log([])

def send_email(subject, body):
    gmail_user = os.environ["GMAIL_USER"]
    gmail_password = os.environ["GMAIL_PASSWORD"]

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = gmail_user
    msg["To"] = gmail_user

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail_user, gmail_password)
        server.send_message(msg)

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "check"
    if mode == "summary":
        send_daily_summary()
    else:
        check_tickets()
