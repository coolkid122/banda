import os
import aiohttp
import asyncio
from fastapi import FastAPI
from contextlib import asynccontextmanager
import re

app = FastAPI()

latest_job_id = None
MONITORED_CHANNEL_IDS = [1430459323716337795, 1430459403034955786]
TOKEN = os.environ.get('TOKEN')

@asynccontextmanager
async def lifespan(app):
    asyncio.create_task(monitor_channels(TOKEN, MONITORED_CHANNEL_IDS))
    yield

app.lifespan = lifespan

@app.get("/pets")
async def get_job_id():
    return {"job_ids": latest_job_id} if latest_job_id else {"job_ids": "No job ID available"}

async def monitor_channels(token, channel_ids):
    global latest_job_id
    headers = {'Authorization': token, 'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}
    async with aiohttp.ClientSession() as session:
        last_message_ids = {channel_id: None for channel_id in channel_ids}
        while True:
            for channel_id in channel_ids:
                try:
                    url = f"https://discord.com/api/v9/channels/{channel_id}/messages?limit=1"
                    async with session.get(url, headers=headers) as response:
                        if response.status != 200:
                            continue
                        messages = await response.json()
                        if messages:
                            message = messages[0]
                            content = message.get('content', '')
                            match = re.search(r'[a-f0-9]{8}-?[a-f0-9]{4}-?[a-f0-9]{4}-?[a-f0-9]{4}-?[a-f0-9]{12}', content, re.IGNORECASE)
                            if match:
                                job_id = match.group(0)
                                latest_job_id = job_id
                                print(f"New job ID from {channel_id}: {job_id}")
                except Exception as e:
                    print(f"Error monitoring {channel_id}: {str(e)}")
            await asyncio.sleep(0.1)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
