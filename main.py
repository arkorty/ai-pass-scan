import json
import os
import uuid
import time
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from PIL import Image
import fitz  # PyMuPDF
from pdf2image import convert_from_path
import google.generativeai as genai

# Load environment variables
load_dotenv()

app = FastAPI(
    title="AI Pass Scan API",
    description="Extract structured information from travel documents",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure Gemini AI
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError("GEMINI_API_KEY environment variable is required")
genai.configure(api_key=api_key)


# Ensure temp directory exists
os.makedirs("tmp", exist_ok=True)


def get_extraction_prompt() -> str:
    """Generate the extraction prompt for travel document information"""
    return """Extract travel document information from the following and return ONLY a valid JSON object with these fields:

{
    "document_type": "string (e.g., Flight, Train, Bus, Hotel, Visa, Insurance)",
    "pnr_booking_id": "string (PNR/booking ID)",
    "route": "string (e.g., DEL-BOM, NYC-LAX)",
    "service_provider": "string (e.g., IndiGo, Indian Railways, Marriott)",
    "vehicle_number": "string (Flight/Train number, Room number, etc.)",
    "journey_date": "string (YYYY-MM-DD format)",
    "journey_time": "string (departure/check-in time)",
    "arrival_time": "string (arrival/check-out time)",
    "travel_class": "string (Economy, Business, Deluxe, etc.)",
    "booking_amount": "string (with currency)",
    "passenger_list": [
        {
            "name": "string",
            "age": "string",
            "primary": boolean
        }
    ],
    "additional_info": {}
}

If any field is not found or not applicable, use null. Return ONLY the JSON, no additional text."""


async def process_single_document(
    file: UploadFile, gemini_only: bool, file_index: int
) -> Dict[str, Any]:
    start_time = time.time()
    temp_id = f"{str(uuid.uuid4())[:8]}_{file_index}"

    # Determine file extension
    file_ext = os.path.splitext(file.filename)[1].lower()
    temp_file_path = f"tmp/{temp_id}{file_ext}"

    try:
        # Save uploaded file
        content = await file.read()
        with open(temp_file_path, "wb") as f:
            f.write(content)

        if file_ext == ".pdf":
            # Direct Gemini processing for PDF
            try:
                uploaded_file = genai.upload_file(
                    temp_file_path, mime_type="application/pdf"
                )
                model = genai.GenerativeModel("gemini-2.5-flash")
                prompt = get_extraction_prompt()
                response = model.generate_content([uploaded_file, prompt])
                genai.delete_file(uploaded_file.name)

                # Parse response
                response_text = response.text.strip()
                if response_text.startswith("```json"):
                    response_text = response_text[7:]
                elif response_text.startswith("```"):
                    response_text = response_text[3:]
                if response_text.endswith("```"):
                    response_text = response_text[:-3]

                data = json.loads(response_text.strip())
                processing_time = time.time() - start_time

                return {
                    "file_index": file_index,
                    "filename": file.filename,
                    "processing_method": "gemini_direct",
                    "processing_time": processing_time,
                    "data": data,
                }

            except Exception as e:
                raise Exception(f"Direct Gemini processing failed: {str(e)}")
        else:
            raise Exception(
                f"Only PDF files are supported for direct Gemini processing. Unsupported file type: {file_ext}"
            )

    except Exception as e:
        return {"file_index": file_index, "filename": file.filename, "error": str(e)}

    finally:
        # Clean up temporary file
        if os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception:
                pass  # Ignore cleanup errors


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "AI Pass Scan API",
        "version": "1.0.0",
        "description": "Extract structured information from travel documents",
        "status": "active",
        "endpoints": {
            "/": "API information",
            "/scan": "Upload and process travel documents (PDF, images)",
        },
        "supported_formats": ["PDF", "JPG", "JPEG", "PNG"],
        "processing_methods": [
            "Direct Gemini (PDF only): Direct AI processing for faster results"
        ],
    }


@app.post("/scan")
async def scan_documents(
    files: List[UploadFile] = File(..., description="Travel documents to process"),
    gemini_only: bool = Form(
        False, description="Use direct Gemini processing (PDF only)"
    ),
):
    """Process travel documents and extract structured information. Only PDF files are supported. Set gemini_only to true for direct PDF processing. Returns extracted information in structured JSON format."""
    start_time = time.time()

    # Validate input
    if not files or all(not file.filename for file in files):
        raise HTTPException(status_code=400, detail="No valid files uploaded")

    # Filter valid files
    valid_files = [f for f in files if f.filename and f.filename.strip()]

    if not valid_files:
        raise HTTPException(status_code=400, detail="No valid files to process")

    # Validate file extensions
    allowed_extensions = {".pdf", ".jpg", ".jpeg", ".png"}
    for file in valid_files:
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {file_ext}. Allowed: {', '.join(allowed_extensions)}",
            )

    # Process files
    results = []
    errors = []

    for file_index, file in enumerate(valid_files):
        try:
            result = await process_single_document(file, gemini_only, file_index)

            if "error" in result:
                errors.append(
                    {
                        "file_index": file_index,
                        "filename": file.filename,
                        "error": result["error"],
                    }
                )
            else:
                results.append(result)

        except Exception as e:
            errors.append(
                {"file_index": file_index, "filename": file.filename, "error": str(e)}
            )

    # Prepare response
    total_processing_time = time.time() - start_time

    response = {
        "total_files": len(valid_files),
        "successful_extractions": len(results),
        "failed_extractions": len(errors),
        "total_processing_time": total_processing_time,
        "results": results,
    }

    if errors:
        response["errors"] = errors

    return JSONResponse(content=response)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
