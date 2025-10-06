import logging
import asyncio

class DiscordLogHandler(logging.Handler):
    def __init__(self, client,channel_id):
        super().__init__()
        self.client = client
        self .channel_id = channel_id
    def emit(self, record):
        log_entry = self.format(record)
        if len(log_entry) > 1900:
            log_entry = log_entry[:1900] + "\n...(省略)"
        asyncio.run_coroutine_threadsafe(
            self.send_log(log_entry), self.client.loop
        )
    async def send_log(self, message):
        channel = self.client.get_channel(self.channel_id)
        if channel:
            await channel.send("@everyone")
            await channel.send({message})