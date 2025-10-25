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
                    print(f"API Request Status for {channel_id}: {response.status}")
                    if response.status == 401:
                        print(f"ERROR: 401 Unauthorized for {channel_id}. Token invalid or bot lacks permissions. Check TOKEN and channel access.")
                        await asyncio.sleep(5)
                        continue
                    elif response.status == 403:
                        print(f"ERROR: 403 Forbidden for {channel_id}. Bot missing 'Read Messages' permission.")
                        await asyncio.sleep(5)
                        continue
                    elif response.status == 404:
                        print(f"ERROR: 404 Not Found for {channel_id}. Channel ID may be incorrect.")
                        await asyncio.sleep(5)
                        continue
                    elif response.status != 200:
                        error_text = await response.text()
                        print(f"ERROR: Failed to fetch messages from {channel_id}. Status: {response.status}, Details: {error_text}")
                        await asyncio.sleep(3)
                        continue
                    messages = await response.json()
                    print(f"DEBUG: Fetched {len(messages)} messages from {channel_id}")
                    if not messages:
                        print(f"WARNING: No messages fetched from {channel_id}. Channel may be empty or bot can't see them.")
                    for message in messages:
                        content = message.get('content', '')
                        print(f"DEBUG: Raw message content from {channel_id}: {repr(content)}")
                        if not content:
                            print(f"WARNING: Message from {channel_id} has no content: {message}")
                            continue
                        match = re.search(r'(?:[a-f0-9]{8}-?[a-f0-9]{4}-?[a-f0-9]{4}-?[a-f0-9]{4}-?[a-f0-9]{12}|[a-f0-9]{32})', content, re.IGNORECASE)
                        if match:
                            job_id = match.group(0)
                            latest_job_id = job_id
                            print(f"SUCCESS: Extracted job ID from {channel_id}: {job_id}")
                        else:
                            print(f"WARNING: No job ID matched in content from {channel_id}: {repr(content)}")
                        last_message_id = message['id']
            except aiohttp.ClientConnectionError as e:
                print(f"NETWORK ERROR: Connection failed for {channel_id}: {str(e)}. Retrying...")
                await asyncio.sleep(5)
            except Exception as e:
                print(f"UNEXPECTED ERROR monitoring {channel_id}: {str(e)}. Type: {type(e).__name__}")
                await asyncio.sleep(3)
            await asyncio.sleep(0.05)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
