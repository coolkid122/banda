import os
import aiohttp
import asyncio
from fastapi import FastAPI
from contextlib import asynccontextmanager
import re
from datetime import datetime

app = FastAPI()

job_ids = {
    "mobile": {"jobid": None, "timestamp": None},
    "pc": {"jobid": None, "timestamp": None}
}
CHANNEL_MOBILE = 1430459323716337795
CHANNEL_PC = 1430459403034955786
TOKEN = os.environ.get('TOKEN')

@asynccontextmanager
async def lifespan(app):
    asyncio.create_task(monitor_channel(TOKEN, CHANNEL_MOBILE, "mobile"))
    asyncio.create_task(monitor_channel(TOKEN, CHANNEL_PC, "pc"))
    yield

app.lifespan = lifespan

@app.get("/pets")
async def get_job_ids():
    return {"job_ids": job_ids}

async def monitor_channel(token, channel_id, key):
    headers = {'Authorization': token, 'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}
    async with aiohttp.ClientSession() as session:
        last_message_id = None
        while True:
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
                            timestamp = datetime.now().isoformat()
                            job_ids[key] = {"jobid": job_id, "timestamp": timestamp}
                            print(f"Updated {key} job ID: {job_id} at {timestamp}")
            except Exception as e:
                print(f"Error monitoring {key}: {str(e)}")
            await asyncio.sleep(0.05)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
