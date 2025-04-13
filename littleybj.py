import discord
from discord.ext import commands, tasks
from discord.ui import Button, View, Select, Modal, TextInput
import os
import time
import dotenv
import requests
import aiohttp
import asyncio
import datetime
import threading
from flask import Flask
from dataclasses import dataclass
from gmail_api import search_emails

app = Flask(__name__)

@app.route("/")
def index():
    return "LittleYBJ is running!"

def run_web():
    app.run(host='0.0.0.0', port=8080)

threading.Thread(target=run_web).start()

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
MAIL_CHANNEL_ID = 1351939144531574867
TIMER_CHANNEL_ID = 1353369453567676426
IDEA_CHANNEL_ID = 1353369426103242856
SYSTEM_CHANNEL_ID = 1359169959703351416

YBJ_ID = 877711777943650335  # 我的ID

# 載入.env檔案
dotenv.load_dotenv()
LILTLEYBJ_KEY = os.getenv("LILTLEYBJ_KEY")
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

# intents是要求機器人的權限
intents = discord.Intents.all()
bot = commands.Bot(command_prefix = "&", intents = intents)

# 設定 Notion 資料庫
db_url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
headers = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

@dataclass
class Timer:
    content: str
    hour: int
    minute: int

mail_timers = {
    "mail_timer1": Timer("mail_timer1", 8, 0), 
    "mail_timer2": Timer("mail_timer2", 20, 0)
}

personal_timers = {
    "timer1": Timer("personal_timer1", 9, 0),
    "timer2": Timer("personal_timer2", 13, 0)
}

async def set_timers():
    mail_timers["mail_timer1"].hour = get_data("Name", "mail_timer1", "hour", "number")
    mail_timers["mail_timer1"].minute = get_data("Name", "mail_timer1", "minute", "number")
    mail_timers["mail_timer2"].hour = get_data("Name", "mail_timer2", "hour", "number")
    mail_timers["mail_timer2"].minute = get_data("Name", "mail_timer2", "minute", "number")

    query_data = {
        "filter": {
            "and": [
                {
                    "property": "Name",
                    "title": {
                        "does_not_contain": "mail_timer"
                    }
                },
                {
                    "property": "category",
                    "select": {
                        "equals": "timer"
                    }
                }
            ]
        }
    }

    response = requests.post(db_url, headers=headers, json=query_data)
    if response.status_code == 200:
        data = response.json()
        personal_timers.clear()

        for item in data["results"]:
            name = item["properties"]["Name"]["title"][0]["text"]["content"]
            hour = item["properties"]["hour"]["number"]
            minute = item["properties"]["minute"]["number"]
            personal_timers[name] = Timer(name, hour, minute)
    else:
        print(f"❌ 無法從 Notion 獲取資料，錯誤碼：{response.status_code}")

async def update_db_timer(timer_name, hour, minute):
    page_id = get_data("Name", timer_name, "id", "id")  # 取得 Notion 頁面 ID
    
    if not isinstance(page_id, str):  # 確保 page_id 有效
        return f"❌ 無法找到定時器 `{timer_name}`，請檢查名稱！"

    url = f"https://api.notion.com/v1/pages/{page_id}"
    data = {
        "properties": {
            "hour": {"number": hour},
            "minute": {"number": minute}
        }
    }

    async with aiohttp.ClientSession() as session:
        async with session.patch(url, headers=headers, json=data) as response:
            if response.status == 200:
                return f"✅ `{timer_name}` 更新成功為 {hour}:{minute}！"
            else:
                return f"❌ `{timer_name}` 更新失敗，錯誤碼：{response.status}"

async def add_db_personal_timer(timer_name, hour, minute):
    url = "https://api.notion.com/v1/pages"
    data = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "Name": {"title": [{"text": {"content": timer_name}}]},
            "category": {"select": {"name": "timer"}},
            "hour": {"number": hour},
            "minute": {"number": minute}
        }
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=data) as response:
            if response.status == 200:
                return f"✅ `{timer_name}` 已成功新增至資料庫！"
            else:
                return f"❌ 新增失敗，錯誤碼：{response.status}，錯誤訊息：{await response.text()}"

async def delete_db_timer(timer_names):
    timers_to_delete = []
    for timer_name in timer_names:
        page_id = get_data("Name", timer_name, "id", "id")
        if isinstance(page_id, str):
            timers_to_delete.append(page_id)
    for page_id in timers_to_delete:
        delete_url = f"https://api.notion.com/v1/pages/{page_id}"
        delete_response = requests.patch(delete_url, headers=headers, json={"archived": True})

        if delete_response.status_code == 200:
            print(f"✅ 成功刪除計時器: {page_id}")
        else:
            print(f"❌ 刪除失敗: {delete_response.text}")

async def update_db_mail(mail_name, content):
    page_id = get_data("Name", mail_name, "id", "id")
    if not isinstance(page_id, str):
        return "❌ 無法找到郵件記錄，請檢查名稱！"
    url = f"https://api.notion.com/v1/pages/{page_id}"
    data = {
        "properties": {
            "content": {"rich_text": [{"text": {"content": content}}]}
        }
    }

    async with aiohttp.ClientSession() as session:
        async with session.patch(url, headers=headers, json=data) as response:
            if response.status == 200:
                return "✅ 郵件記錄更新成功！"
            else:
                return f"❌ 郵件記錄更新失敗，錯誤碼：{response.status}"

async def add_idea_to_db(content):
    title = content[:40]
    data = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "Name": {
                "title": [{
                    "text": {"content": title}
                }]
            },
            "category": {
                "select": {"name": "idea"}
            },
            "content": {
                "rich_text": [{
                    "text": {"content": content}
                }]
            }
        }
    }
    response = requests.post("https://api.notion.com/v1/pages", headers=headers, json=data)
    print("📥 Notion 回應狀態碼：", response.status_code)

async def init():
    await set_timers()
    response = requests.post(db_url, headers=headers)
    if response.status_code == 200:
        print("讀取資料庫成功")
    else:
        print("讀取失敗")

# 取得 Notion 資料庫中的資料
def get_data(property="Name", name="None", req="content", type="rich_text"):
    # 查詢條件：篩選出 "property" 為 "name" 的資料
    query_data = {
        "filter": {
            "property": property,
            "title": {
                "equals": name
            }
        }
    }

    response = requests.post(db_url, headers=headers, json=query_data)
    if response.status_code == 200:
        data = response.json()
        if data["results"]:
            if type == "rich_text":
                return data["results"][0]["properties"][req]["rich_text"][0]["text"]["content"]
            elif type == "number":
                return data["results"][0]["properties"][req]["number"]
            elif type == "id":
                return data["results"][0]["id"]
        else:
            return "查無資料"
    else:
        return "資造庫讀取失敗"
    
def get_all_ideas():
    query_data = {
        "filter": {
            "property": "category",
            "select": {
                "equals": "idea"
            }
        }
    }

    response = requests.post(db_url, headers=headers, json=query_data)
    if response.status_code == 200:
        data = response.json()
        ideas = []
        for item in data["results"]:
            title = item["properties"]["Name"]["title"][0]["text"]["content"]
            content = item["properties"]["content"]["rich_text"][0]["text"]["content"]
            ideas.append([title, content])
        return ideas
    else:
        print(f"❌ 無法從 Notion 獲取資料，錯誤碼：{response.status_code}")
        return []

class TimeInputModal(Modal, title="設定鬧鐘時間"):
    hour = TextInput(label="小時 (0-23)", placeholder="請輸入 0-23", required=True)
    minute = TextInput(label="分鐘 (0-59)", placeholder="請輸入 0-59", required=True)

    def __init__(self, timer_name):
        super().__init__()
        self.timer_name = timer_name  # 記住是哪個鬧鐘

    async def on_submit(self, interaction: discord.Interaction):
        try:
            hour = int(self.hour.value)
            minute = int(self.minute.value)
            if 0 <= hour < 24 and 0 <= minute < 60:
                await interaction.response.defer()  # 先回應，避免等待時間過長 
                await update_db_timer(self.timer_name, hour, minute)
                await set_timers()
                await interaction.followup.send(f"✅ `{self.timer_name}` 更新為 {hour:02d}:{minute:02d}！", ephemeral=True)
            else:
                await interaction.followup.send("❌ 時間輸入錯誤，請重新設定！", ephemeral=True)
        except ValueError:
            await interaction.followup.send("❌ 輸入格式錯誤，請輸入數字！", ephemeral=True)

class AddTimerModal(Modal, title="新增鬧鐘"):
    timer_name = TextInput(label="請輸入鬧鐘名稱", placeholder="例如：吃藥", required=True)
    hour = TextInput(label="小時 (0-23)", placeholder="請輸入 0-23", required=True)
    minute = TextInput(label="分鐘 (0-59)", placeholder="請輸入 0-59", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        new_timer_name = self.timer_name.value.strip()
        hour = int(self.hour.value)
        minute = int(self.minute.value)
        if new_timer_name:
            await interaction.response.defer()
            for timer in mail_timers.keys() | personal_timers.keys():
                if new_timer_name == timer:
                    await interaction.followup.send("❌ 鬧鐘名稱重複，請重新輸入！", ephemeral=True)
                    return

            await add_db_personal_timer(new_timer_name, hour, minute)
            await set_timers()

            await interaction.followup.send(f"✅ 新增 `{new_timer_name}` 成功！", ephemeral=True)
        else:
            await interaction.followup.send("❌ 鬧鐘名稱不能為空！", ephemeral=True)

# 🔵 讓使用者選擇 Timer 的選單
class TimerSelectView(View):
    def __init__(self):
        super().__init__()
        self.add_item(TimerSelect())

class TimerSelect(Select):
    def __init__(self):
        options = [discord.SelectOption(label=key, value=key) for key in list(mail_timers.keys()) + list(personal_timers.keys())]
        options.insert(0, discord.SelectOption(label="➕ 新增鬧鐘", value="add_new"))
        super().__init__(placeholder="選擇要修改的鬧鐘", options=options)

    async def callback(self, interaction: discord.Interaction):
        if interaction.data["values"][0] == "add_new":
            await interaction.response.send_modal(AddTimerModal())  # 顯示新增鬧鐘的輸入框
        else:
            await interaction.response.send_modal(TimeInputModal(self.values[0]))  # 顯示輸入框

class TimerDeleteView(View):
    def __init__(self):
        super().__init__()
        self.add_item(TimerDelete())

class TimerDelete(Select):
    def __init__(self):
        options = [discord.SelectOption(label=key, value=key) for key in list(mail_timers.keys()) + list(personal_timers.keys())]
        super().__init__(placeholder="選擇要刪除的鬧鐘", options=options, min_values=1, max_values=len(options))

    async def callback(self, interaction: discord.Interaction):
        for value in interaction.data["values"]:
            if value in mail_timers:
                await interaction.response.send_message("❌ 不能刪除預設的郵件鬧鐘！", ephemeral=True)
                return
        
        await interaction.response.defer()
        await delete_db_timer(interaction.data["values"])
        await interaction.followup.send(f"✅ `{value}` 已成功刪除！", ephemeral=True)
        await set_timers()

class IdeaDeleteView(View):
    def __init__(self):
        super().__init__()
        self.add_item(IdeaDelete())

class IdeaDelete(Select):
    def __init__(self):
        ideas = get_all_ideas()
        options = [discord.SelectOption(label=title, value=title) for title, _ in ideas]
        super().__init__(placeholder="選擇要刪除的靈感", options=options, min_values=1, max_values=len(options))

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        for value in interaction.data["values"]:
            page_id = get_data("Name", value, "id", "id")
            if isinstance(page_id, str):
                delete_url = f"https://api.notion.com/v1/pages/{page_id}"
                delete_response = requests.patch(delete_url, headers=headers, json={"archived": True})
                if delete_response.status_code == 200:
                    print(f"✅ 成功刪除靈感: {value}")
                else:
                    print(f"❌ 刪除失敗: {delete_response.text}")
        await interaction.followup.send("✅ 已成功刪除靈感！", ephemeral=True)

@bot.event
async def on_ready():
    print(f"目前登入身份 --> {bot.user}")
    channel = bot.get_channel(SYSTEM_CHANNEL_ID)
    await channel.send("LittleYBJ 已啟動！")
    time.sleep(10)  # 等待 10 秒，讓所有頻道和成員都載入完成
    if not check_timer_task.is_running():  # 確保 task 只會啟動一次
        check_timer_task.start()
        return

user_commands = ["help", "哈囉", "嗨", "信", "課程信件", "設定鬧鐘", "刪除鬧鐘", "鬧鐘", "靈感", "idea", "刪除靈感"]

@bot.event
async def on_message(message):
    if message.author == bot.user:  # 避免機器人回應自己
        return

    if message.channel.id == IDEA_CHANNEL_ID and message.content not in user_commands:  
        # 發訊息詢問是否加入 Notion
        prompt = await message.channel.send("你要不要新增到靈感？")
        await prompt.add_reaction("✅")
        await prompt.add_reaction("❌")

        def check(reaction, user):
            return (
                user == message.author and
                reaction.message.id == prompt.id and
                str(reaction.emoji) in ["✅", "❌"]
            )

        try:
            reaction, user = await bot.wait_for("reaction_add", timeout=30.0, check=check)
            if str(reaction.emoji) == "✅":
                ideas = get_all_ideas()
                for title, content in ideas:
                    if title == message.content:
                        await message.channel.send("❌ 此靈感已存在！")
                        await prompt.delete()
                        return
                await add_idea_to_db(message.content)
                await message.channel.send("✅ 已加入靈感")
                await prompt.delete()  # 刪除提示訊息
            else:
                await prompt.delete()

        except:
            await prompt.delete()
        return
    if "help" in message.content or "Help" in message.content:  # 偵測關鍵字「help」
        await message.channel.send("哈囉！我是 LittleYBJ，你的小幫手！以下是我能幫助你的指令：\n"
                                   "## <指令列表>\n"
                                   "1. **help** / **Help** - 顯示指令列表\n"
                                   "2. **哈囉** / **嗨** - 打招呼\n"
                                   "3. **信 <關鍵字>** - 查詢郵件 (預設會在 8:00 和 20:00 自動查詢最新信件，可從「**設定鬧鐘**」調整)\n"
                                   "4. **課程信件** - 查詢近期課程相關郵件\n"
                                   "5. **鬧鐘** - 顯示目前運行中的所有鬧鐘，我會在設定的時間提醒你！ (mail_timer不會提醒！但會在該時間查詢信件)\n"
                                   "6. **設定鬧鐘** - 設定、新增鬧鐘\n"
                                   "7. **刪除鬧鐘** - 刪除鬧鐘\n"
                                   "8. **靈感** / **idea** - 顯示靈感列表\n"
                                   "9. **刪除靈感** - 刪除指定靈感")
    elif "哈囉" in message.content or "嗨" in message.content:
        await message.channel.send("哈囉！我是 LittleYBJ，你的小幫手！有什麼可以幫助你的嗎？")
    elif "課程信件" in message.content:
        channel = bot.get_channel(MAIL_CHANNEL_ID)
        await check_course_email(channel)
    elif "信" in message.content:
        channel = bot.get_channel(MAIL_CHANNEL_ID)
        keywords = message.content.split()  # 取得使用者輸入的所有詞
        
        if len(keywords) > 1:
            await check_email(channel, *keywords[1:])  # 正確傳遞 channel 參數
        else:
            await check_email(channel)  # 只輸入「信」時，執行無關鍵字的查詢
    elif "設定鬧鐘" in message.content:
        channel = bot.get_channel(TIMER_CHANNEL_ID)
        await update_timer(channel)
    elif "刪除鬧鐘" in message.content:
        channel = bot.get_channel(TIMER_CHANNEL_ID)
        await delete_timer(channel)
    elif "鬧鐘" in message.content:
        channel = bot.get_channel(TIMER_CHANNEL_ID)
        response = "## <目前運行中的所有鬧鐘>\n"
        timers = {**mail_timers, **personal_timers}
        for timer in timers.keys():
            response += f"🕰️ **{timer}**  時間：{timers[timer].hour:02d}:{timers[timer].minute:02d}\n"
        await channel.send(response)
    elif "刪除靈感" in message.content:
        channel = bot.get_channel(IDEA_CHANNEL_ID)
        await delete_idea(channel)
    elif "靈感" in message.content or "idea" in message.content:
        channel = bot.get_channel(IDEA_CHANNEL_ID)
        ideas = get_all_ideas()
        if not ideas:
            response = "目前沒有收錄任何靈感！"
        else:    
            response = "## <靈感列表>\n"
        for title, content in ideas:
            response += f"💡 **{title}**"
            if len(content) > 40:
                response += "..."
            response += f"\n"
        await channel.send(response)

    await bot.process_commands(message)  # 確保指令仍然可用

@bot.command()
async def list_users(ctx):
    guild = ctx.guild
    members = guild.members  # 取得所有成員
    response = "**伺服器內的成員 ID 列表：**\n"
    for member in members:
        if not member.bot:
            response += f"👤 `{member.name}` - `{member.id}`\n"
    await ctx.send(response)

@bot.command()
async def list_channels(ctx):
    guild = ctx.guild  # 取得伺服器
    channels = guild.channels  # 取得所有頻道
    response = "**伺服器內的頻道 ID 列表：**\n"
    for channel in channels:
        response += f"📌 `{channel.name}` - `{channel.id}`\n"
    await ctx.send(response)

async def check_email(channel, *keywords):
    global last_course_subject, last_school_subject
    no_new_course_email = True
    no_new_school_email = True
    no_other_email = True

    if keywords:
        for keyword in keywords:
            emails = search_emails(keyword, 30)
            if emails:
                response = f"## <近30封符合 `{keyword}` 的郵件>\n"
                for email in emails:
                    response += f"📩 **寄件人：** {email['From']}\n📌 **主旨：** {email['Subject']}\n\n"
                await channel.send(response)
            else:
                await channel.send(f"🔍 找不到近30封符合 `{keyword}` 的郵件。")
        return

    # 課程郵件處理
    emails = search_emails("/", 30)
    if emails:
        response = f"## <課程郵件通知>\n"
        for email in emails:
            if email["Subject"] != last_course_subject:
                if no_new_course_email:
                    no_new_course_email = False
                    last_course_subject = email["Subject"]
                    await update_db_mail("last_course_subject", last_course_subject)
                response += f"**📩 寄件人：**{email['From']}\n**📌 主旨：**{email['Subject']}\n\n"
            else:
                break

        if not no_new_course_email:
            await channel.send(response)

    # 學校郵件處理
    emails = search_emails("陽明交通大學", 30)
    if emails:
        response = f"## <學校相關郵件通知>\n"
        for email in emails:
            if email["Subject"] != last_school_subject:
                if no_new_school_email:
                    no_new_school_email = False
                    last_school_subject = email["Subject"]
                    await update_db_mail("last_school_subject", last_school_subject)
                response += f"**📩 寄件人：**{email['From']}\n**📌 主旨：**{email['Subject']}\n\n"
            else:
                break

        if not no_new_school_email:
            await channel.send(response)

    # 其他郵件處理
    response = f"## <其他郵件通知>\n"
    emails = search_emails("蝦皮", 30)
    if emails:
        no_other_email = False
        no_new_email = False
        for email in emails:
            response += f"**📩 寄件人：**{email['From']}\n**📌 主旨：**{email['Subject']}\n\n"
    emails = search_emails("物理", 30)
    if emails:
        no_other_email = False
        no_new_email = False
        for email in emails:
            response += f"**📩 寄件人：**{email['From']}\n**📌 主旨：**{email['Subject']}\n\n"
    if not no_other_email:
        await channel.send(response)

    if no_new_email:
        await channel.send("📭 目前沒有新郵件！")

async def check_course_email(channel):
    emails = search_emails("/", 40)
    if emails:
        response = f"## <近期課程郵件通知>\n"
        for email in emails:
            if "Course" in email:
                response += f"**📚 課程：**{email['Course']}\n**📩 寄件人：**{email['From']}\n**📌 主旨：**{email['Subject']}\n\n"
            else:
                response += f"**📩 寄件人：**{email['From']}\n**📌 主旨：**{email['Subject']}\n\n"
        await channel.send(response)
    else:
        await channel.send("🔍 近期無課程郵件。")

@bot.command()
async def update_timer_cmd(ctx):
    view = TimerSelectView()
    await ctx.send("請選擇要修改的鬧鐘", view=view)

async def update_timer(channel):
    view = TimerSelectView()
    await channel.send("請選擇要設定的鬧鐘", view=view)

async def delete_timer(channel):
    view = TimerDeleteView()
    await channel.send("請選擇要刪除的鬧鐘", view=view)

async def delete_idea(channel):
    ideas = get_all_ideas()
    if not ideas:
        await channel.send("目前沒有靈感可以刪除！")
        return
    view = IdeaDeleteView()
    await channel.send("請選擇要刪除的靈感", view=view)

@tasks.loop(minutes=1)  # 每分鐘檢查一次是否到達設定時間
async def check_timer_task():
    global last_run_time
    now = datetime.datetime.now()

    # 檢查郵件
    channel = bot.get_channel(MAIL_CHANNEL_ID)
    for timer in mail_timers.values():
        if now.hour == timer.hour and now.minute == timer.minute:
            if channel:
                await check_email(channel=channel)

    # 檢查鬧鐘
    channel = bot.get_channel(TIMER_CHANNEL_ID)
    for timer in personal_timers.values():
        if now.hour == timer.hour and now.minute == timer.minute:
            if channel:
                YBJ = await bot.fetch_user(YBJ_ID)
                await channel.send(f"⏰ 鬧鐘提醒 {YBJ.mention}： **{timer.content}**！")

# 記錄上次讀取到的最新信件主旨
last_course_subject = get_data("Name", "last_course_subject", "content", "rich_text")
last_school_subject = get_data("Name", "last_school_subject", "content", "rich_text")

print("正在初始化...")
asyncio.run(init())
print("初始化完成")

print("延遲啟動，防止 rate limit...")
time.sleep(10)
bot.run(LILTLEYBJ_KEY)