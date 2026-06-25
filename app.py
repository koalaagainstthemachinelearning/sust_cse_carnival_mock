# pyrefly: ignore [missing-import]
from google import genai
import os
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv
# pyrefly: ignore [missing-import]
from fastapi import FastAPI# pyrefly: ignore [missing-import]
# pyrefly: ignore [missing-import]
from pydantic import BaseModel
from typing import Optional 
import json
load_dotenv()

app=FastAPI()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

class TicketStr(BaseModel):
    ticket_id:str
    channel:Optional[str]=None
    locale:Optional[str]=None
    message:str

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/sort-ticket")
async def sort_ticket(ticket:TicketStr):
    prompt = f"""
You are a classifier for a digital finance support system in Bangladesh.

Given a customer message, return ONLY a valid JSON object with these exact fields:
- case_type: one of [wrong_transfer, payment_failed, refund_request, phishing_or_social_engineering, other]
- severity: one of [low, medium, high, critical]
- department: one of [customer_support, dispute_resolution, payments_ops, fraud_risk]
- agent_summary: 1-2 neutral sentences. NEVER mention PIN, OTP, password, or card number.
- confidence: a float between 0.0 and 1.0

Routing rules:
- wrong_transfer → dispute_resolution, severity high
- payment_failed → payments_ops, severity high
- phishing_or_social_engineering → fraud_risk, severity critical
- simple refund → customer_support, severity low
- other → customer_support, severity low

Customer message: "{ticket.message}"

Return ONLY the JSON object. No explanation, no markdown, no extra text.
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    raw = response.text.strip()

    # Strip markdown if Gemini wraps in ```json ... ```
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    result = json.loads(raw)

    # You calculate this — never trust LLM for safety rules
    human_review = (
    result["severity"] in ["critical", "high"]
    or result["case_type"] == "phishing_or_social_engineering"
)

    return {
        "ticket_id": ticket.ticket_id,
        "case_type": result["case_type"],
        "severity": result["severity"],
        "department": result["department"],
        "agent_summary": result["agent_summary"],
        "human_review_required": human_review,
        "confidence": result["confidence"]
    }