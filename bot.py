import aiohttp
import os
import asyncio
import uuid
from flask import Flask, request, jsonify
import threading
from dotenv import load_dotenv
load_dotenv()
TOKEN=os.environ.get("TOKEN")
PORT=int(os.environ.get("PORT",8080))
CHANNEL_10M=1430459323716337795
CHANNEL_100M=1430459403034955786
PHRASES=["Chipso and Queso","Los Primos","Eviledon","Los Tacoritas","Tang Tang Keletang","Ketupat Kepat","Tictac Sahur","La Supreme Combinasion","Ketchuru and Musturu","Garama and Madundung","Spaghetti Tualetti","Spooky and Pumpky","La Casa Boo","La Secret Combinasion","Burguro And Fryuro","Headless Horseman","Dragon Cannelloni","Meowl","Strawberry Elephant"]
job_ids={"job_ids10m":"No job ID available","job_ids100m":"No job ID available","job_idsrare":"No job ID available"}
app=Flask(__name__)
@app.route("/pets",methods=["GET"])
async def pets():
    user_agent=request.headers.get("User-Agent")
    if not user_agent or "Roblox/WinInet" not in user_agent:
        return jsonify({"error":"access denied"}),403
    return jsonify(job_ids)
async def make_request(session,url,headers,max_retries=5):
    retries=0
    base_delay=5
    while retries<max_retries:
        try:
            async with session.get(url,headers=headers) as response:
                if response.status==429:
                    retry_after=float(response.headers.get("Retry-After",base_delay))
                    await asyncio.sleep(retry_after)
                    retries+=1
                    base_delay*=2
                    continue
                elif response.status!=200:
                    return None
                return await response.json()
        except:
            retries+=1
            await asyncio.sleep(base_delay)
            base_delay*=2
    return None
async def monitor_discord_channels():
    global job_ids
    headers={'Authorization':TOKEN,'Content-Type':'application/json','User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    async with aiohttp.ClientSession() as session:
        last_message_ids={str(CHANNEL_10M):None,str(CHANNEL_100M):None}
        for cid in [CHANNEL_10M,CHANNEL_100M]:
            url=f"https://discord.com/api/v9/channels/{cid}/messages?limit=1"
            messages=await make_request(session,url,headers)
            if messages is None:
                return
            last_message_ids[str(cid)]=messages[0]['id'] if messages else None
        while True:
            for cid in [CHANNEL_10M,CHANNEL_100M]:
                try:
                    url=f"https://discord.com/api/v9/channels/{cid}/messages?after={last_message_ids[str(cid)]}&limit=10"
                    messages=await make_request(session,url,headers)
                    if messages:
                        for message in reversed(messages):
                            for phrase in PHRASES:
                                if phrase.lower() in message['content'].lower():
                                    phrase_clean=phrase.replace(" ","_").replace("&","and")
                                    job_id=str(uuid.uuid5(uuid.NAMESPACE_DNS,f"{phrase_clean}_{message['id']}"))
                                    if cid==CHANNEL_10M:
                                        job_ids["job_ids10m"]=job_id
                                    elif cid==CHANNEL_100M:
                                        job_ids["job_ids100m"]=job_id
                                    job_ids["job_idsrare"]=job_id
                                    break
                            last_message_ids[str(cid)]=message['id']
                    await asyncio.sleep(5)
                except:
                    await asyncio.sleep(5)
def run_flask():
    app.run(host="0.0.0.0",port=PORT)
async def main():
    if not TOKEN:
        return
    flask_thread=threading.Thread(target=run_flask)
    flask_thread.start()
    try:
        await monitor_discord_channels()
    except:
        pass
if __name__=="__main__":
    asyncio.run(main())
