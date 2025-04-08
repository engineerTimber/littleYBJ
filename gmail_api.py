import os
import pickle
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

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

def get_gmail_service():
    creds = None
    token_path = "token.pickle"
    credentials_path = "oauth_credentials.json"

    if os.path.exists(token_path):
        with open(token_path, "rb") as token:
            creds = pickle.load(token)

    # 自動刷新憑證
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            with open(token_path, "wb") as token:
                pickle.dump(creds, token)
        except Exception as e:
            print("刷新 token 失敗，嘗試重新登入。錯誤：", e)
            creds = None

    if not creds or not creds.valid:
        if not os.path.exists(credentials_path):
            raise FileNotFoundError(f"找不到 {credentials_path}，請確保檔案存在")
        flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
        creds = flow.run_local_server(port=0)
        with open(token_path, "wb") as token:
            pickle.dump(creds, token)

    return build("gmail", "v1", credentials=creds)

def list_labels():
    service = get_gmail_service()
    results = service.users().labels().list(userId="me").execute()
    labels = results.get("labels", [])

    if not labels:
        print("No labels found.")
    else:
        print("Labels:")
        for label in labels:
            print(f"{label['name']} (ID: {label['id']})")

def check_email_for_keyword(keyword, count=15):
    service = get_gmail_service()
    results = service.users().messages().list(userId="me", maxResults=count).execute()
    messages = results.get("messages", [])

    email_info = []

    for msg in messages:
        msg_detail = service.users().messages().get(userId="me", id=msg["id"]).execute()
        headers = msg_detail.get("payload", {}).get("headers", [])

        from_header = next((header["value"] for header in headers if header["name"] == "From"), "")
        subject_header = next((header["value"] for header in headers if header["name"] == "Subject"), "")

        if keyword.lower() in from_header.lower() or keyword.lower() in subject_header.lower():
            find_ta = False
            if keyword == "/":
                for ta, course in TA_COURSE_TABLE.items():
                    if ta in from_header.lower() or ta in subject_header.lower():
                        find_ta = True
                        email_info.append({"Course": course, "From": from_header, "Subject": subject_header})
                        break
            else:
                email_info.append({"From": from_header, "Subject": subject_header})

    return email_info

def get_recent_emails(count=15):
    service = get_gmail_service()
    results = service.users().messages().list(userId="me", labelIds=["INBOX", "CATEGORY_UPDATES"], maxResults=count).execute()
    messages = results.get("messages", [])

    email_info = []

    for msg in messages:
        msg_detail = service.users().messages().get(userId="me", id=msg["id"]).execute()
        headers = msg_detail.get("payload", {}).get("headers", [])

        from_header = next((header["value"] for header in headers if header["name"] == "From"), "")
        subject_header = next((header["value"] for header in headers if header["name"] == "Subject"), "")

        email_info.append({"From": from_header, "Subject": subject_header})

    return email_info

if __name__ == "__main__":
    print("測試 Gmail API 連線...")

    keyword = "/"
    email_snippet = check_email_for_keyword(keyword, 30)
    if email_snippet:
        print(f"找到符合關鍵字「{keyword}」的信件：\n")
        for email in email_snippet:
            print(f"From: {email['From']}, Subject: {email['Subject']}")
    else:
        print("沒有符合的信件")

    print("\n最近的信件：")
    recent_emails = get_recent_emails(15)
    for email in recent_emails:
        print(f"From: {email['From']}, Subject: {email['Subject']}")
