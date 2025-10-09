import sys
import os

# このファイルのディレクトリの親ディレクトリを取得して、検索パスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
import config

channelLogID = int(config.channelLogID)
print(f"IDの値: {channelLogID}")
print(f"IDの型: {type(channelLogID)}") # ← この行を追加して型を確認
print(channelLogID)

async def sendLog(client,message):
    channel = client.get_channel(channelLogID)
    now = datetime.now()
    await channel.send("[{}:{}]{}".format(now.hour,now.minute,message))