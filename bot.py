import asyncio
import aiohttp
import json
import os
from aiohttp import web

current_job_id = "No job ID available"

async def process_message(message):
    global current_job_id
    if 'embeds' in message and message['embeds']:
        for embed in message['embeds']:
            if 'fields' in embed and embed['fields']:
                jobId = None
                for field in embed['fields']:
                    if 'Job ID' in field.get('name', ''):
                        jobId = field.get('value', '').replace('`', '')
                if jobId:
                    current_job_id = jobId

async def monitor_discord_channel(token, channel_id):
    headers = {
        'Authorization': token,
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    async with aiohttp.ClientSession() as session:
        url = f"https://discord.com/api/v9/channels/{channel_id}/messages?limit=1"
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                messages = await response.json()
                if messages:
                    await process_message(messages[0])
                    last_message_id = messages[0]['id']
                else:
                    last_message_id = None
        while True:
            if last_message_id:
                url = f"https://discord.com/api/v9/channels/{channel_id}/messages?after={last_message_id}&limit=10"
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        messages = await response.json()
                        for message in reversed(messages):
                            await process_message(message)
                            last_message_id = message['id']

async def handle(request):
    return web.json_response({"job_ids": current_job_id})

async def main():
    TOKEN = os.environ['TOKEN']
    PORT = 8080
    channels = [1430459323716337795, 1430459403034955786]
    tasks = []
    for channel_id in channels:
        tasks.append(asyncio.create_task(monitor_discord_channel(TOKEN, channel_id)))
    app = web.Application()
    app.add_routes([web.get('/pets', handle)])
    await web._run_app(app, port=PORT, print=False, access_log=False)

if __name__ == "__main__":
    asyncio.run(main())
