import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
import os
import sys
import json

URL = "https://sell.pia.jp/inbound/selectTicket.php?eventCd=2601912&rlsCd=003&langCd=eng"
TARGET_DATES = ["May 20", "May 22", "5/20", "5/22"]
LOG_FILE = "check_log.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://sell.pia.jp"
}

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
        res = requests.get(URL, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, "html.parser")
        text = soup.get_text()

        if "Kokugikan" not in text:
            result = "頁面載入異常"
            print(f"[{now}] {result}")
            log.append({"time": now, "result": result})
            save_log(log)
            return

        goes_on_sale = "Goes on sale" in text
        sold_out = any(word in text for word in ["SOLD OUT", "売り切れ", "完売"])

        if goes_on_sale or sold_out:
            result = "無票"
            print(f"[{now}] {result}")
            log.append({"time": now, "result": result})
            save_log(log)
            return

        has_seats = soup.find("input", {"type": "radio"}) or soup.find("select")
        if not has_seats:
            result = "無票"
            print(f"[{now}] {result}")
            log.append({"time": now, "result": result})
            save_log(log)
            return

        found_dates = [d for d in TARGET_DATES if d in text]
        if not found_dates:
            result = "有票但非目標場次"
            print(f"[{now}] {result}")
            log.append({"time": now, "result": result})
            save_log(log)
            return

        matched = ""
        if any("20" in d for d in found_dates):
            matched += "5月20日 "
        if any("22" in d for d in found_dates):
            matched += "5月22日"
        result = f"有票！{matched.strip()}"
        log.append({"time": now, "result": result})
        save_log(log)
        send_alert(matched.strip())

    except Exception as e:
        result = f"錯誤：{e}"
        print(f"[{now}] {result}")
        log.append({"time": now, "result": result})
        save_log(log)
        sys.exit(1)

def send_alert(dates):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
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

    # 發完清空 log
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
