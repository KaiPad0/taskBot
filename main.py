import config
import discord
from discord import app_commands
from discord.ext import tasks
import sqlite3
import variable
import logging
from command import detabase
from command.sendLog import sendLog
from command.loggerLog import  DiscordLogHandler
from datetime import datetime, timedelta
from sync_calender import sync as update

intents = discord.Intents.default() 
client = discord.Client(intents=intents) 
tree = app_commands.CommandTree(client)
channelID = int(config.channelID)
channelLogID = int(config.channelLogID)
api = int(config.api)
calendar = int(config.calendar)

detabase.init_db()

@client.event
async def on_ready():
    #logingの初期設定
    logger = logging.getLogger()
    format = "%(levelname)-9s  %(asctime)s [%(filename)s:%(lineno)d] %(message)s"
    dc_handler = DiscordLogHandler(client, channelLogID)
    fl_handler = logging.FileHandler(filename="taskBot.log", encoding="utf-8")
    dc_handler.setLevel(logging.DEBUG)
    fl_handler.setLevel(logging.WARNING)
    dc_handler.setFormatter(logging.Formatter(format))
    fl_handler.setFormatter(logging.Formatter(format))
    #logger.addHandler(dc_handler)
    logger.addHandler(fl_handler)
    # アクティビティを設定 
    new_activity = f"課題" 
    await client.change_presence(activity=discord.Game(new_activity)) 
    # スラッシュコマンドを同期 
    await tree.sync()
    announce.start()
    await sendLog(client,'ログインしました')
    await update(client)

@tree.command(name='add', description='課題の追加をするコマンド')
@discord.app_commands.choices(
    教科 = variable.subject
)
@discord.app_commands.describe(
    期限日="1/31 形式で入力してください",
    時間="23:59 形式で入力してください"
)
async def register(interaction: discord.Interaction, 教科:str, 期限日:str, 時間:str ="23:59"): 
    if '/' not in 期限日:
        await interaction.response.send_message("日付は'/'で区切ってください",ephemeral=True)
        await sendLog(client,"日付入力間違い")
    elif ':' not in 時間:
        await interaction.response.send_message("時間は':'で区切ってください",ephemeral=True)
        await sendLog(client,"時間入力間違い")
    else:
        date = 期限日.split('/')
        time = 時間.split(':')
        detabase.add(教科,date,time,)
        await sendLog(client,f'{教科}({期限日},{時間}まで)')
        try:
            await interaction.response.send_message(f'{教科}({期限日},{時間}まで)')
        except discord.errors.NotFound:
            await sendLog(client,"インタラクションが無効のためメッセージ送信に失敗しました。")
        await update(client)
        await sendLog(client,"added!")

async def task_autocomplete(interaction: discord.Interaction, current: str):
    rows = detabase.get_task_choice_rows()
    choices = []

    for row in rows:
        subject, month, day, hour, minute = row
        label = f"{subject} ({month}/{day} {hour:02}:{minute:02})"
        value = f"{subject}|{month}|{day}|{hour}|{minute}"

        if current.lower() in label.lower():
            choices.append(app_commands.Choice(name=label, value=value))

        if len(choices) >= 25:  # Discordが許容する最大件数
            break

    return choices

@tree.command(name='delete', description='追加した課題を取り消すコマンド')
@app_commands.describe(課題="削除する課題を選んでください")
@app_commands.autocomplete(課題=task_autocomplete)
async def delete(interaction: discord.Interaction, 課題: str):
    subject, month, day, hour, minute = 課題.split('|')
    conn = sqlite3.connect(detabase.dbname)
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM task WHERE subject=? AND month=? AND day=? AND hour=? AND minute=?",
        (subject, int(month), int(day), int(hour), int(minute))
    )
    conn.commit()
    cur.close()
    conn.close()

    try:
        await interaction.response.send_message(f"{subject} ({month}/{day} {hour}:{minute}) を削除しました。")
    except discord.errors.NotFound:
        await sendLog(client,"インタラクションが無効のためメッセージ送信に失敗しました。")
    await sendLog(client,f"{subject}({month}/{day} {hour}:{minute})を削除しました。")
    await update(client)
    await sendLog(client,"deleted!")

@tree.command(name='calendar', description='googleカレンダーのurlを送信')
async def calendar(interaction: discord.Interaction):
    await interaction.response.send_message(calendar,ephemeral=True)

@tasks.loop(seconds=60)
async def announce():
    now = datetime.now()
    if now.hour == 17 and now.minute == 00:
        conn = sqlite3.connect(detabase.dbname)
        cur = conn.cursor()
        cur2 = conn.cursor()
        now = datetime.now()
        tomorrow  = now + timedelta(days=1)
        yesterday = now - timedelta(days=1)

        cur.execute("""
            SELECT * FROM task 
            WHERE (CAST(day AS INTEGER) = ? AND CAST(month AS INTEGER) = ? AND CAST(hour AS INTEGER) BETWEEN 18 AND 24)
            OR (CAST(day AS INTEGER) = ? AND CAST(month AS INTEGER) = ? AND CAST(hour AS INTEGER) BETWEEN 0 AND 17)
            """, (now.day, now.month, tomorrow.day, tomorrow.month))
        rows = cur.fetchall()

        if rows:
            result = "期限間近:\n"
            result += "\n".join(f"{row[0]} ({row[1]}/{row[2]},{row[3]}:{row[4]})" for row in rows)
            channel = client.get_channel(channelID)
        else:
            result = "一致するレコードはありませんでした。"
            channel = client.get_channel(channelLogID)
        await channel.send(result)
        cur2.execute("""DELETE FROM task WHERE (CAST(month AS INTEGER) = ? AND CAST(day AS INTEGER) = ?)
                    OR (CAST(month AS INTEGER) = ? AND CAST(day AS INTEGER) = ? AND CAST(hour AS INTEGER) BETWEEN 0 AND 17)
                    """,(yesterday.month, yesterday.day, now.month, now.day))
        conn.commit()
        cur.close()
        cur2.close()
        conn.close()
        await update(client)
        await sendLog(client,"announced!")

client.run(api)