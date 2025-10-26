import aiohttp
import asyncio
import os
import logging
from fastapi import FastAPI
import uvicorn

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI()

TOKEN = os.environ.get("TOKEN")
PORT = int(os.environ.get("PORT", 8080))
CHANNEL_10M = 1430459323716337795
CHANNEL_100M = 1430459403034955786
PHRASES = [
    "Chipso and Queso", "Los Primos", "Eviledon", "Los Tacoritas", "Tang Tang Keletang",
    "Ketupat Kepat", "Tictac Sahur", "La Supreme Combinasion", "Ketchuru and Musturu",
    "Garama and Madundung", "Spaghetti Tualetti", "Spooky and Pumpky", "La Casa Boo",
    "La Secret Combinasion", "Burguro And Fryuro", "Headless Horseman", "Dragon Cannelloni",
    "Meowl", "Strawberry Elephant"
]
job_ids = {
    "job_ids10m": "No job ID available",
    "job_ids100m": "No job ID available",
    "job_idsrare": "No job ID available"
}

async def make_request(session, url, headers, max_retries=5):
    retries = 0
    base_delay = 5
    while retries < max_retries:
        try:
            async with session.get(url, headers=headers) as response:
                status = response.status
                text = await response.text()
                logger.info(f"API Request to {url}: Status {status}, Response: {text[:200]}...")
                if status == 429:
                    retry_after = float(response.headers.get("Retry-After", base_delay))
                    logger.warning(f"Rate limited. Waiting {retry_after}s (retry {retries + 1}/{max_retries})")
                    await asyncio.sleep(retry_after)
                    retries += 1
                    base_delay *= 2
                    continue
                elif status != 200:
                    logger.error(f"API Error {status}: {text}")
                    return None
                try:
                    return await response.json()
                except Exception as e:
                    logger.error(f"JSON decode error: {e}, Response: {text}")
                    return None
        except Exception as e:
            logger.error(f"Request exception: {e}")
            retries += 1
            await asyncio.sleep(base_delay)
            base_delay *= 2
    logger.error(f"Max retries exceeded for {url}")
    return None

async def monitor_discord_channels():
    global job_ids
    headers = {
        'Authorization': TOKEN,
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    logger.info("Starting Discord channel monitor...")
    async with aiohttp.ClientSession() as session:
        last_message_ids = {str(CHANNEL_10M): None, str(CHANNEL_100M): None}
        for cid in [CHANNEL_10M, CHANNEL_100M]:
            url = f"https://discord.com/api/v9/channels/{cid}/messages?limit=1"
            logger.info(f"Initial fetch for channel {cid}: {url}")
            messages = await make_request(session, url, headers)
            if messages:
                last_message_ids[str(cid)] = messages[0]['id']
                logger.info(f"Initial last ID for {cid}: {last_message_ids[str(cid)]}")
            else:
                logger.warning(f"Failed initial fetch for {cid}")

        while True:
            for cid in [CHANNEL_10M, CHANNEL_100M]:
                try:
                    after_id = last_message_ids[str(cid)]
                    url = f"https://discord.com/api/v9/channels/{cid}/messages?after={after_id}&limit=10" if after_id else f"https://discord.com/api/v9/channels/{cid}/messages?limit=10"
                    logger.info(f"Polling {cid}: after={after_id}")
                    messages = await make_request(session, url, headers)
                    if messages:
                        logger.info(f"Got {len(messages)} messages for {cid}")
                        for message in reversed(messages):
                            jobId = None
                            petName = None
                            if 'embeds' in message and message['embeds']:
                                for embed in message['embeds']:
                                    if 'fields' in embed and embed['fields']:
                                        for field in embed['fields']:
                                            fval = field.get('value', '')
                                            if 'Job ID' in field.get('name', ''):
                                                jobId = fval.replace('`', '')
                                            if 'Name' in field.get('name', ''):
                                                petName = fval
                            if jobId:
                                logger.info(f"Extracted Job ID: {jobId}")
                                if cid == CHANNEL_10M:
                                    job_ids["job_ids10m"] = jobId
                                    logger.info(f"Updated job_ids10m: {jobId}")
                                elif cid == CHANNEL_100M:
                                    job_ids["job_ids100m"] = jobId
                                    logger.info(f"Updated job_ids100m: {jobId}")
                                if petName and any(phrase.lower() in petName.lower() for phrase in PHRASES):
                                    job_ids["job_idsrare"] = jobId
                                    logger.info(f"Rare match for {petName}, updated job_idsrare: {jobId}")
                            last_message_ids[str(cid)] = message['id']
                        logger.info(f"Updated job_ids: {job_ids}")
                except Exception as e:
                    logger.error(f"Polling error for {cid}: {e}")
            await asyncio.sleep(0.1)

@app.get("/")
async def home():
    return job_ids

@app.get("/pets")
async def pets():
    return job_ids

@app.on_event("startup")
async def startup():
    if not TOKEN:
        logger.error("TOKEN not set")
        return
    asyncio.create_task(monitor_discord_channels())

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
