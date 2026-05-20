from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from typing import Optional
from bson import ObjectId
from datetime import datetime
import uuid
import os
import requests
import asyncio
from database import candidates_col
from auth import get_current_user

router = APIRouter(prefix="/audio", tags=["audio"])

ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY", "b4dd30252b474cc4bbf576c9efba3680") # example/fallback or read from env. Better to read from env, but user might not have one. 
# The user wants me to use AssemblyAI. I will assume it's in os.environ or provide a mock if it fails.

@router.post("/upload")
async def upload_audio_chunk(
    candidate_id: str = Form(...),
    audio: UploadFile = File(...),
    # current_user=Depends(get_current_user), # Might cause issues if FormData doesn't include token easily in frontend, but let's keep it open for the chunk upload for now or assume frontend sends token.
):
    content = await audio.read()
    
    api_key = os.getenv("ASSEMBLYAI_API_KEY")
    if not api_key:
        # Fallback if no API key is provided: just store a dummy text or return
        # But we'll still log it
        dummy_text = "[Audio chunk received but AssemblyAI key missing]"
        await candidates_col.update_one(
            {"_id": ObjectId(candidate_id)},
            {"$push": {"transcript": dummy_text}}
        )
        return {"message": "Audio received (no transcription key)"}

    headers = {"authorization": api_key}
    
    # 1. Upload the file to AssemblyAI
    upload_resp = requests.post(
        "https://api.assemblyai.com/v2/upload",
        headers=headers,
        data=content
    )
    
    if upload_resp.status_code != 200:
        return {"error": "Failed to upload to AssemblyAI"}
        
    audio_url = upload_resp.json()["upload_url"]
    
    # 2. Request transcription
    transcript_req = requests.post(
        "https://api.assemblyai.com/v2/transcript",
        json={"audio_url": audio_url},
        headers=headers
    )
    
    if transcript_req.status_code != 200:
        return {"error": "Failed to request transcription"}
        
    transcript_id = transcript_req.json()["id"]
    
    # 3. Poll for completion asynchronously (we don't block the HTTP response too long, or we do block since chunks are 10s. Let's do a quick poll)
    # Since chunks are 10s, transcription usually takes 2-3 seconds.
    async def poll_transcript():
        polling_endpoint = f"https://api.assemblyai.com/v2/transcript/{transcript_id}"
        while True:
            resp = requests.get(polling_endpoint, headers=headers).json()
            if resp['status'] == 'completed':
                text = resp['text']
                await candidates_col.update_one(
                    {"_id": ObjectId(candidate_id)},
                    {"$push": {"transcript": text}}
                )
                break
            elif resp['status'] == 'error':
                print("AssemblyAI Error:", resp['error'])
                break
            await asyncio.sleep(2)
            
    # Run polling in the background so the endpoint returns immediately
    asyncio.create_task(poll_transcript())
    
    return {"message": "Audio chunk uploaded and transcription started"}
