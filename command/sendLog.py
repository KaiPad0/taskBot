from datetime import datetime

channelLogID = 1371002002602983455

async def sendLog(client,message):
    channel = client.get_channel(channelLogID)
    now = datetime.now()
    await channel.send("[{}:{}]{}".format(now.hour,now.minute,message))