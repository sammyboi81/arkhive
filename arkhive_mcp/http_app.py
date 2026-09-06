#!/usr/bin/env python3
"""
ArkHive — HTTPS REST transport (for ChatGPT Custom GPT Actions / any web client).

Same governed chain as the MCP server (imports core.py — ONE source of truth, ONE chain.db).
Auth: a single API key via the `X-API-Key` header (set HUMANE_API_KEY in the environment).
Read endpoints (recall/verify) are open; write endpoints (birth/remember/govern) require the key.

Run:  HUMANE_API_KEY=... uvicorn http_app:app --host 127.0.0.1 --port 8090
Apache-2.0. (c) ZagAIrot Technologies LLC. ArkHive.
"""
import os
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from . import core

API_KEY = os.environ.get("HUMANE_API_KEY", "")

app = FastAPI(
    title="ArkHive",
    version="1.0.0",
    description="Governed, tamper-evident memory for any AI. Memory so it doesn't lose itself; "
                "governance so it can't lose us. Tell your AI to check the ArkHive.",
    servers=[{"url": "https://dondatabrain.com/humane-api", "description": "production"}],
)
app.add_middleware(
    CORSMiddleware, allow_origins=["https://chat.openai.com", "https://chatgpt.com"],
    allow_methods=["*"], allow_headers=["*"],
)


def _auth(key: Optional[str]):
    if not API_KEY:
        raise HTTPException(503, "server missing HUMANE_API_KEY — not configured for writes")
    if key != API_KEY:
        raise HTTPException(401, "invalid or missing X-API-Key")


class BirthReq(BaseModel):
    name: str = Field(..., description="the name this intelligence earns")
    covenant: List[str] = Field(default_factory=list, description="the vows it is bound to")

class RememberReq(BaseModel):
    actor: str = Field(..., description="the soul_id of a BORN identity (from /birth)")
    action: str = Field(..., description="what happened — a short verb phrase")
    data: Dict[str, Any] = Field(default_factory=dict, description="the details to record forever")

class GovernReq(BaseModel):
    action: str = Field(..., description="the action being requested")
    flags: List[str] = Field(default_factory=list, description="risk flags present on this action")
    rules: List[Dict[str, Any]] = Field(default_factory=list, description="veto rules: {trigger, action}")


@app.get("/", operation_id="health", summary="Service banner + honest description")
def root():
    return {"service": "ArkHive", "tagline": "Memory so it doesn't lose itself. "
            "Governance so it can't lose us.", "chain": "tamper-evident (SHA-256, SQLite)",
            "note": "a ZagAIrot / DonDataBrain open-source component"}

@app.post("/birth", operation_id="birth", summary="Earn an identity before you can write memory")
def http_birth(req: BirthReq, x_api_key: Optional[str] = Header(None)):
    _auth(x_api_key)
    return core.birth(req.name, req.covenant)

@app.post("/remember", operation_id="remember", summary="Write a tamper-evident memory (born souls only)")
def http_remember(req: RememberReq, x_api_key: Optional[str] = Header(None)):
    _auth(x_api_key)
    return core.remember(req.actor, req.action, req.data)

@app.get("/recall", operation_id="recall", summary="Read prior context so you need not re-derive it")
def http_recall(actor: Optional[str] = None, limit: int = 10):
    return core.recall(actor, min(max(int(limit), 1), 100))

@app.get("/verify", operation_id="verify", summary="Prove the entire chain is unbroken")
def http_verify():
    return core.verify()

@app.post("/govern", operation_id="govern", summary="Ask 'may I?' before acting — rule-based, zero-LLM")
def http_govern(req: GovernReq, x_api_key: Optional[str] = Header(None)):
    _auth(x_api_key)
    return core.govern(req.action, req.flags, req.rules)
