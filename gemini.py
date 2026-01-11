import os
import json
import re
from dotenv import load_dotenv
from google import genai
from google.genai import types
from schemas import InvoiceData

load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

SYSTEM_PROMPT = """
You are extracting invoice-related information from chat screenshots.

Tasks:
1. Read all visible text from the images.
2. Infer missing details if context is obvious.
For "items":
- Always return an ARRAY
- Each item must be an object with:
  - description (string)
  - quantity (number, default 1)
  - rate (number, default 0)

If you see only one item, still return an array with one object.
If price is missing, use 0.
Never return items as a string.
3. Return ONLY valid JSON matching this schema:

{
  "companyName": string | null,
  "address": string | null,
  "GSTIN No.": string | null,
  "date": string | null,
  "items": array | null,
  "totalAmount": string | null,
  "paymentMode": string | null,
  "paymentStatus": string | null,
  "Client Name": string | null,
  "Client Address": string | null
}

Rules:
- Do not add explanations
- Do not add extra fields
- If unsure, return null
"""

def extract_invoice_data(images: list[bytes]) -> InvoiceData:
    parts = [SYSTEM_PROMPT]

    for img in images:
        parts.append(
            types.Part.from_bytes(
                data=img,
                mime_type="image/png"
            )
        )

    response = client.models.generate_content(
        model="gemini-2.5-flash-lite",
        contents=parts,
        config={
            "temperature": 0.1
        }
    )

    # Gemini may still wrap JSON in markdown
    text = response.text.strip()
    text = re.sub(r"^```json|```$", "", text).strip()

    data = json.loads(text)

# -------------------------------
# Normalize ITEMS (non-negotiable)
# -------------------------------

    raw_items = data.get("items")

    normalized_items = []

    if isinstance(raw_items, list):
        for item in raw_items:
            if isinstance(item, dict):
                normalized_items.append({
                    "description": str(item.get("description", "")),
                    "quantity": int(item.get("quantity", 1)),
                    "rate": float(item.get("rate", 0)),
                })

    elif isinstance(raw_items, str):
        # fallback: single item inferred from text
        normalized_items.append({
            "description": raw_items,
            "quantity": 1,
            "rate": 0,
        })

    # overwrite items with safe structure
    data["items"] = normalized_items
    return InvoiceData(**data)