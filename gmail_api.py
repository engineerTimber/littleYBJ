import imaplib
import email
from email.header import decode_header
from dotenv import load_dotenv
import os
import socket

TA_COURSE_TABLE = {
     "林冠霆": "OOP",
     "黃世強": "OOP",
     "江仲恩": "OOP",
     "黃睿帆": "微積分",
     "姜鈞": "微積分",
     "陳以潔": "生涯規劃與導師時間",
     "吳雨勳": "生涯規劃與導師時間",
     "王先正": "國防",
     "嚴力行": "離散數學",
     "鄭璟翰": "離散數學",
     "蔡淳仁": "數位電路設計",
     "廖昶竣": "數位電路設計",
     "葉家蓁": "服務學習：自由軟體推廣",
     "ewant": "物理",
     "鄭智仁": "體育",
     "/": "未知QQ"
}

# 設定全域 timeout（防止卡住）
socket.setdefaulttimeout(10)

# 載入 .env 中的帳密
load_dotenv()
MY_GMAIL = os.getenv("MY_GMAIL")
MY_GMAIL_PASSWORD = os.getenv("MY_GMAIL_PASSWORD")

# 建立連線
def connect_to_gmail():
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(MY_GMAIL, MY_GMAIL_PASSWORD)
    mail.select("inbox")
    return mail

# 解碼函數，處理亂碼
def decode_mime_words(s):
    decoded = decode_header(s)
    return ''.join(
        str(part[0], part[1] or 'utf-8') if isinstance(part[0], bytes) else part[0]
        for part in decoded
    )

# 搜尋關鍵字（從最新的 num_emails 封信件中找）
def search_emails(keyword, num_emails=10):
    try:
        mail = connect_to_gmail()
        status, messages = mail.search(None, "ALL")
        email_ids = messages[0].split()
        latest_ids = email_ids[-num_emails:]

        matching_emails = []
        for eid in reversed(latest_ids):  # 從最新到舊
            try:
                status, data = mail.fetch(eid, "(RFC822)")
                if status != "OK":
                    print(f"⚠️ 無法讀取 email ID {eid}")
                    continue

                msg = email.message_from_bytes(data[0][1])
                subject = decode_mime_words(msg["Subject"])
                from_ = decode_mime_words(msg.get("From"))
                date = msg.get("Date")

                if keyword in subject or keyword in from_:
                    matching_emails.append({
                        "From": from_,
                        "Subject": subject,
                        "Date": date
                    })

            except Exception as e:
                print(f"❌ 處理信件 ID {eid} 時發生錯誤：{e}")
                continue

        mail.logout()
        return matching_emails

    except Exception as e:
        print(f"❌ Gmail 連線或搜尋失敗：{e}")
        return []

def search_course_emails(num_emails=10):
    try:
        keyword = "/"
        mail = connect_to_gmail()
        status, messages = mail.search(None, "ALL")
        email_ids = messages[0].split()
        latest_ids = email_ids[-num_emails:]

        matching_emails = []
        for eid in reversed(latest_ids):  # 從最新到舊
            try:
                status, data = mail.fetch(eid, "(RFC822)")
                if status != "OK":
                    print(f"⚠️ 無法讀取 email ID {eid}")
                    continue

                msg = email.message_from_bytes(data[0][1])
                subject = decode_mime_words(msg["Subject"])
                from_ = decode_mime_words(msg.get("From"))
                date = msg.get("Date")

                if keyword in subject or keyword in from_:
                    course_name = TA_COURSE_TABLE.get(from_, "未知QQ")
                    matching_emails.append({
                        "From": from_,
                        "Subject": subject,
                        "Date": date,
                        "Course": course_name
                    })

            except Exception as e:
                print(f"❌ 處理信件 ID {eid} 時發生錯誤：{e}")
                continue

        mail.logout()
        return matching_emails

    except Exception as e:
        print(f"❌ Gmail 連線或搜尋失敗：{e}")
        return []

# 測試用
if __name__ == "__main__":
    keyword = "/"
    print(f"搜尋包含關鍵字「{keyword}」的信件：")
    emails = search_emails(keyword, num_emails=20)

    for email in emails:
        print(f"From: {email['From']}\nSubject: {email['Subject']}\nDate: {email['Date']}\n")
