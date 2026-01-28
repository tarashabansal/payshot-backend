from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from gemini import extract_invoice_data
from fastapi import Body
from fastapi.responses import StreamingResponse
from jinja2 import Environment, FileSystemLoader
# from weasyprint import HTML
from fastapi.responses import HTMLResponse
import io
import time
import os
from collections import defaultdict
from pydantic import BaseModel, EmailStr
import requests
from io import BytesIO
from xhtml2pdf import pisa

SUPABASE_URL="https://ldewwmfkymjmokopulys.supabase.co/functions/v1/submit-support"
FORM_SECRET= os.getenv("FORM_SECRET")  # Replace with your actual form secret

def generate_pdf(html_content: str) -> bytes:
    pdf_buffer = BytesIO()

    result = pisa.CreatePDF(
        src=html_content,
        dest=pdf_buffer,
        encoding="utf-8"
    )

    if result.err:
        raise RuntimeError("Failed to generate PDF")

    return pdf_buffer.getvalue()


app = FastAPI()

# Rate limiting storage
# Map: IP -> List[timestamp]
request_counts = defaultdict(list)
RATE_LIMIT_DURATION = 15 * 60  # 15 minutes in seconds
MAX_REQUESTS = 5

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://www.payshot.entrext.in", "https://payshot.entrext.in"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/upload")
async def upload_images(request: Request, images: List[UploadFile] = File(...)):
    # Rate Limiting Logic
    client_ip = request.client.host
    current_time = time.time()
    
    # Filter out old timestamps
    request_counts[client_ip] = [
        t for t in request_counts[client_ip] 
        if current_time - t < RATE_LIMIT_DURATION
    ]
    
    if len(request_counts[client_ip]) >= MAX_REQUESTS:
        raise HTTPException(
            status_code=429, 
            detail="Rate limit exceeded. You can only generate 5 invoices every 15 minutes."
        )
        
    request_counts[client_ip].append(current_time)

    try:
        image_bytes = [await img.read() for img in images]
        return extract_invoice_data(image_bytes)
    except Exception as e:
        print("UPLOAD ERROR:", e)
        raise HTTPException(status_code=500, detail=str(e))
    
    
@app.post("/generate-invoice")
async def generate_invoice(data: dict):
    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("invoice.html")

    html_content = template.render(**data)
    pdf = generate_pdf(html_content)

    return StreamingResponse(
        io.BytesIO(pdf),
        media_type="application/pdf",
        headers={
            "Content-Disposition": "attachment; filename=invoice.pdf"
        }
    )
    




@app.post("/invoice-preview", response_class=HTMLResponse)
async def invoice_preview(data: dict):
    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("invoice.html")
    return template.render(**data)


class SupportRequest(BaseModel):
    product: str
    category: str
    message: str
    user_email: EmailStr
    metadata: dict | None = None


@app.post("/support")
def submit_support(payload: SupportRequest):
    response = requests.post(
        SUPABASE_URL,
        headers={
            "Content-Type": "application/json",
            "x-form-secret": FORM_SECRET
        },
        json=payload.dict()
    )

    if response.status_code == 429:
        raise HTTPException(
            status_code=429,
            detail="Too many submissions. Try again later."
        )

    if not response.ok:
        raise HTTPException(
            status_code=response.status_code,
            detail=response.text
        )

    return response.json()