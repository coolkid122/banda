import aiohttp
import os
import asyncio
import re
from flask import Flask, request, jsonify
import threading
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.environ.get("TOKEN")
PORT = int(os.environ.get("PORT", 8080))

CHANNEL_ID = 1423730052872536094

PHRASES = [
    "Chipso and Queso","Los Primos","Eviledon","Los Tacoritas","Tang Tang Keletang",
    "Ketupat Kepat","Tictac Sahur","La Supreme Combinasion","Ketchuru and Musturu",
    "Garama and Madundung","Spaghetti Tualetti","Spooky and Pumpky","La Casa Boo",
    "La Secret Combinasion","Burguro And Fryuro","Headless Horseman",
    "Dragon Cannelloni","Meowl","Strawberry Elephant"
]

job_ids = {
    "job_ids10m": "No job ID available",
    "job_ids100m": "No job ID available",
    "job_idsrare": "No job ID available"
}

app = Flask(__name__)

@app.route("/pets", methods=["GET"])
async def pets():
    return jsonify(job_ids)

@app.route("/", methods=["GET"])
async def root():
    return jsonify(job_ids)

UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")

def extract_job_id(msg):
    if "embeds" in msg:
        for emb in msg["embeds"]:
            if "fields" in emb:
                for f in emb["fields"]:
                    txt = f.get("value","") + f.get("name","")
                    m = UUID_RE.search(txt)
                    if m:
                        return m.group(0)
    m = UUID_RE.search(msg.get("content",""))
    return m.group(0) if m else None

async def make_request(sess, url, hdr, retries=5):
    delay = 5
    for _ in range(retries):
        try:
            async with sess.get(url, headers=hdr) as r:
                if r.status == 429:
                    await asyncio.sleep(float(r.headers.get("Retry-After", delay)))
                    delay *= 2
                    continue
                if r.status != 200:
                    return None
                return await r.json()
        except:
            await asyncio.sleep(delay)
            delay *= 2
    return None

async def monitor():
    global job_ids
    hdr = {
        "Authorization": TOKEN,
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    async with aiohttp.ClientSession() as s:
        last = None
        msgs = await make_request(s, f"https://discord.com/api/v9/channels/{CHANNEL_ID}/messages?limit=1", hdr)
        if msgs:
            last = msgs[0]["id"]
        while True:
            try:
                url = f"https://discord.com/api/v9/channels/{CHANNEL_ID}/messages?after={last}&limit=10"
                msgs = await make_request(s, url, hdr)
                if msgs:
                    for msg in reversed(msgs):
                        triggered = any(p.lower() in msg["content"].lower() for p in PHRASES)
                        job = extract_job_id(msg)
                        if job:
                            money = msg.get("content", "")
                            if "$22M/s" in money or ("$" in money and "M/s" in money):
                                job_ids["job_ids100m"] = job
                            else:
                                job_ids["job_ids10m"] = job
                            if triggered:
                                job_ids["job_idsrare"] = job
                        last = msg["id"]
                await asyncio.sleep(5)
            except:
                await asyncio.sleep(5)

def run_flask():
    app.run(host="0.0.0.0", port=PORT)

async def main():
    if not TOKEN:
        return
    threading.Thread(target=run_flask, daemon=True).start()
    await monitor()

if __name__ == "__main__":
    asyncio.run(main())
