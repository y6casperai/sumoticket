import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
import os
import sys

URL = "https://sell.pia.jp/inbound/selectTicket.php?eventCd=2601912&rlsCd=003&langCd=eng"
TARGET_DATES = ["May 20", "May 22", "5/20", "5/22"]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://sell.pia.jp"
}

def check_tickets():
    try:
        res = requests.get(URL, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, "html.parser")
        text = soup.get_text()

        # 確認頁面有載入
        if "Kokugikan" not in text:
            print(f"[{datetime.now()}] 頁面載入異常")
            return

        # 判斷有無座位選項（有票時會出現 input 或 select 元素）
        has_seats = soup.find("input", {"type": "radio"}) or soup.find("select")

        if not has_seats:
            print(f"[{datetime.now()}] 無票，頁面無座位選項")
            return

        # 確認是否為目標日期
        found_dates = [d for d in TARGET_DATES if d in text]
        if not found_dates:
            print(f"[{datetime.now()}] 有票但非目標場次（5/20、5/22）")
            return

        # 有票且是目標日期，發送通知
        matched = "5月20日" if any("20" in d for d in found_dates) else ""
        matched += " 5月22日" if any("22" in d for d in found_dates) else ""
        send_email(matched.strip())

    except Exception as e:
        print(f"[{datetime.now()}] 錯誤：{e}")
        sys.exit(1)

def send_email(dates):
    gmail_user = os.environ["GMAIL_USER"]
    gmail_password = os.environ["GMAIL_PASSWORD"]
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    subject = f"🎫 有票了！{dates} 場次有票！"
    body = f"""有票了！請立刻前往購買！

場次：{dates}
網址：{URL}
檢查時間：{now}
"""

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = gmail_user
    msg["To"] = gmail_user

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail_user, gmail_password)
        server.send_message(msg)

    print(f"[{datetime.now()}] ✅ 通知已發送！{dates} 有票！")

if __name__ == "__main__":
    check_tickets()
