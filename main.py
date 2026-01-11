from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from gemini import extract_invoice_data
from fastapi import Body
from fastapi.responses import StreamingResponse
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
from fastapi.responses import HTMLResponse
import io


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/upload")
async def upload_images(images: List[UploadFile] = File(...)):
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
    pdf = HTML(string=html_content).write_pdf()

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
