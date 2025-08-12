# AI Pass Scan API

A streamlined FastAPI backend for extracting structured information from travel documents using OCR and AI processing.

## Features

- **Simple API**: Just two endpoints - root (`/`) and scan (`/scan`)
- **Multiple file support**: Process one or more documents in a single request
- **Intelligent processing**: Automatic text extraction with fallback mechanisms
- **No external dependencies**: Uses pip-only packages (EasyOCR, PyMuPDF, pdf2image)
- **Dual processing modes**: OCR-based and direct AI processing

## Supported Documents

- ✈️ Flight tickets and boarding passes
- 🚂 Train tickets and reservations
- 🚌 Bus tickets and bookings
- 🚗 Cab/taxi receipts
- 🏨 Hotel confirmations
- 🛂 Visa documents
- 📄 Travel insurance papers
- 🎫 Any travel-related documents

## Supported Formats

- **PDF**: Portable Document Format
- **JPG/JPEG**: Image formats
- **PNG**: Portable Network Graphics

## Quick Start

### 1. Installation

```bash
# Clone or download the ai-pass-scan directory
cd ai-pass-scan

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Setup

```bash
# Copy environment template
cp .env.example .env

# Edit .env file and add your Gemini API key
# Get your API key from: https://makersuite.google.com/app/apikey
GEMINI_API_KEY=your_actual_api_key_here
```

### 3. Run the API

```bash
python main.py
```

The API will start on `http://localhost:8000`

## API Endpoints

### GET `/` - API Information

Returns API details and usage information.

**Response:**
```json
{
  "name": "AI Pass Scan API",
  "version": "1.0.0",
  "description": "Extract structured information from travel documents",
  "status": "active",
  "endpoints": {
    "/": "API information",
    "/scan": "Upload and process travel documents"
  },
  "supported_formats": ["PDF", "JPG", "JPEG", "PNG"]
}
```

### POST `/scan` - Document Processing

Upload and process travel documents to extract structured information.

**Parameters:**
- `files`: One or more document files (PDF, JPG, JPEG, PNG)
- `gemini_only` (optional): Boolean, use direct Gemini processing for PDFs (default: false)

**Processing Methods:**

1. **OCR-based (default)**:
   - PDF → Text extraction (PyMuPDF) → OCR fallback (EasyOCR) → AI processing
   - Images → OCR (EasyOCR) → AI processing
   - Best for scanned documents and images

2. **Direct Gemini (PDF only)**:
   - PDF → Direct AI processing (Gemini)
   - Faster for text-based PDFs
   - Set `gemini_only=true`

## Usage Examples

### Single File Processing

```bash
# OCR-based processing (default)
curl -X POST -F "files=@ticket.pdf" http://localhost:8000/scan

# Direct Gemini processing (PDF only)
curl -X POST -F "files=@ticket.pdf" -F "gemini_only=true" http://localhost:8000/scan

# Image processing
curl -X POST -F "files=@boarding_pass.jpg" http://localhost:8000/scan
```

### Multiple Files Processing

```bash
# Process multiple documents
curl -X POST \
  -F "files=@flight_ticket.pdf" \
  -F "files=@hotel_booking.pdf" \
  -F "files=@train_ticket.jpg" \
  http://localhost:8000/scan
```

### Python Example

```python
import requests

# Single file
with open('ticket.pdf', 'rb') as f:
    files = {'files': f}
    response = requests.post('http://localhost:8000/scan', files=files)
    result = response.json()

# Multiple files
files = [
    ('files', open('flight.pdf', 'rb')),
    ('files', open('hotel.pdf', 'rb'))
]
response = requests.post('http://localhost:8000/scan', files=files)
result = response.json()

# Close files
for _, file_obj in files:
    file_obj.close()
```

### JavaScript Example

```javascript
// Single file upload
const formData = new FormData();
formData.append('files', fileInput.files[0]);

fetch('http://localhost:8000/scan', {
    method: 'POST',
    body: formData
})
.then(response => response.json())
.then(data => console.log(data));

// Multiple files with direct processing
const formData = new FormData();
for (let file of fileInput.files) {
    formData.append('files', file);
}
formData.append('gemini_only', 'true');

fetch('http://localhost:8000/scan', {
    method: 'POST',
    body: formData
})
.then(response => response.json())
.then(data => console.log(data));
```

## Response Format

### Successful Processing

```json
{
  "total_files": 2,
  "successful_extractions": 2,
  "failed_extractions": 0,
  "total_processing_time": 3.45,
  "results": [
    {
      "file_index": 0,
      "filename": "flight_ticket.pdf",
      "processing_method": "ocr_based",
      "processing_time": 2.1,
      "data": {
        "document_type": "Flight",
        "pnr_booking_id": "ABC123",
        "route": "DEL-BOM",
        "service_provider": "IndiGo",
        "vehicle_number": "6E-123",
        "journey_date": "2024-01-15",
        "journey_time": "10:30",
        "arrival_time": "12:45",
        "travel_class": "Economy",
        "booking_amount": "₹4,500.00",
        "passenger_list": [
          {
            "name": "John Doe",
            "age": "32",
            "primary": true
          }
        ],
        "additional_info": {
          "terminal": "Terminal 2",
          "gate": "A12"
        }
      }
    }
  ]
}
```

### With Errors

```json
{
  "total_files": 2,
  "successful_extractions": 1,
  "failed_extractions": 1,
  "total_processing_time": 2.8,
  "results": [
    // ... successful results
  ],
  "errors": [
    {
      "file_index": 1,
      "filename": "corrupted_file.pdf",
      "error": "PDF text extraction failed: file appears to be corrupted"
    }
  ]
}
```

## Extracted Information Fields

The API extracts the following information when available:

- **document_type**: Type of document (Flight, Train, Bus, Hotel, etc.)
- **pnr_booking_id**: PNR or booking ID
- **route**: Travel route (e.g., "DEL-BOM", "NYC-LAX")
- **service_provider**: Company name (IndiGo, Marriott, etc.)
- **vehicle_number**: Flight number, train number, room number, etc.
- **journey_date**: Travel date (YYYY-MM-DD format)
- **journey_time**: Departure/check-in time
- **arrival_time**: Arrival/check-out time
- **travel_class**: Class of service (Economy, Business, etc.)
- **booking_amount**: Cost with currency
- **passenger_list**: List of travelers with details
- **additional_info**: Extra details specific to document type

## Error Handling

The API provides comprehensive error handling:

- **400 Bad Request**: Invalid file format, no files uploaded
- **500 Internal Server Error**: Processing failures
- **Detailed error messages**: Specific error descriptions for troubleshooting

## Performance Notes

- **OCR Processing**: 2-5 seconds per document
- **Direct Gemini**: 1-3 seconds per PDF
- **Memory usage**: Optimized for multiple file processing
- **Cleanup**: Automatic temporary file cleanup

## Deployment

### Local Development
```bash
python main.py
```

### Production with Gunicorn
```bash
pip install gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Docker
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["python", "main.py"]
```

## Requirements

- Python 3.7+
- Gemini API key
- ~2GB RAM for OCR processing
- Internet connection for AI processing

## License

MIT License - feel free to use in your projects!

## Support

For issues or questions:
1. Check the error messages in the API response
2. Ensure your Gemini API key is valid
3. Verify document formats are supported
4. Check network connectivity for AI processing
