from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
import httpx
import asyncio
import time

app = FastAPI()

last_gen = {}
TIMEOUT = 60
semaphore = asyncio.Semaphore(5)
POLINATIONS_URL = "https://image.pollinations.ai/prompt/"

@app.post("/generate")
async def generate_image(request: Request):
    data = await request.json()
    prompt = data.get("prompt")
    user_id = data.get("user_id")
    if not prompt or not user_id:
        raise HTTPException(status_code=400, detail="Prompt и user_id обязательны")
    
    now = time.time()
    last_time = last_gen.get(user_id, 0)
    if now - last_time < TIMEOUT:
        raise HTTPException(status_code=429, detail=f"Подождите {int(TIMEOUT - (now - last_time))} секунд")
    
    last_gen[user_id] = now

    async with semaphore:
        async with httpx.AsyncClient(timeout=60) as client:
            try:
                url = f"{POLINATIONS_URL}{prompt.replace(' ', '%20')}"
                response = await client.get(url, follow_redirects=True)
                response.raise_for_status()
            except httpx.HTTPError as e:
                raise HTTPException(status_code=500, detail=f"Ошибка Polinations: {e}")
            return StreamingResponse(response.aiter_bytes(), media_type="image/png")
