import os
import aiohttp
import asyncio
from fastapi import FastAPI
from contextlib import asynccontextmanager
import re

app = FastAPI()

latest_job_id = None
CHANNEL_MOBILE = 1430459323716337795
TOKEN = os.environ.get('TOKEN')

@asynccontextmanager
async def lifespan(app):
    asyncio.create_task(monitor_channel(TOKEN, CHANNEL_MOBILE))
    yield

app.lifespan = lifespan

@app.get("/pets")
async def get_job_id():
    return {"job_ids": latest_job_id} if latest_job_id else {"job_ids": "No job ID available"}

async def monitor_channel(token, channel_id):
    global latest_job_id
    headers = {'Authorization': token, 'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}
    async with aiohttp.ClientSession() as session:
        last_message_id = None
        while True:
            try:
                url = f"https://discord.com/api/v9/channels/{channel_id}/messages?limit=5"
                async with session.get(url, headers=headers) as response:
                    if response.status == 401:
                        print(f"401 Unauthorized for {channel_id}: Check TOKEN permissions")
                        await asyncio.sleep(5)
                        continue
                    elif response.status != 200:
                        print(f"Failed to fetch from {channel_id}: Status {response.status} - {await response.text()}")
                        await asyncio.sleep(3)
                        continue
                    messages = await response.json()
                    print(f"Fetched {len(messages)} messages from {channel_id}")
                    for message in messages:
                        content = message.get('content', '')
                        print(f"Message content: {repr(content)}")
                        match = re.search(r'[a-f0-9]{32}|[a-f0-9]{8}-?[a-f0-9]{4}-?[a-f0-9]{4}-?[a-f0-9]{4}-?[a-f0-9]{12}', content, re.IGNORECASE)
                        if match:
                            job_id = match.group(0)
                            latest_job_id = job_id
                            print(f"Job ID matched from {channel_id}: {job_id}")
                        last_message_id = message['id']
            except Exception as e:
                print(f"Error monitoring {channel_id}: {str(e)}")
            await asyncio.sleep(0.05)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
