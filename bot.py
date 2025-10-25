import os
import discord
import threading
from flask import Flask, jsonify

latest_job_id = "No job ID available"

class MyClient(discord.Client):
    async def on_ready(self):
        global latest_job_id
        channels = [1430459323716337795, 1430459403034955786]
        latest_message = None
        latest_time = None
        for ch_id in channels:
            channel = self.get_channel(ch_id)
            if channel:
                async for msg in channel.history(limit=1):
                    if not latest_message or msg.created_at > latest_time:
                        latest_message = msg
                        latest_time = msg.created_at
        if latest_message:
            latest_job_id = latest_message.content

    async def on_message(self, message):
        if message.channel.id not in [1430459323716337795, 1430459403034955786]:
            return
        global latest_job_id
        latest_job_id = message.content

TOKEN = os.environ["TOKEN"]
PORT = int(os.environ.get("PORT", 8080))
intents = discord.Intents.default()
intents.message_content = True
client = MyClient(intents=intents)

def run_bot():
    client.run(TOKEN)

threading.Thread(target=run_bot).start()

app = Flask(__name__)

@app.route('/pets')
def pets():
    return jsonify({"job_ids": latest_job_id})

app.run(host='0.0.0.0', port=PORT)
