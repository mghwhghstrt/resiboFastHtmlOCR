from fasthtml import FastHTML
from fasthtml.common import *
import os, uvicorn
from starlette.responses import FileResponse
from starlette.datastructures import UploadFile
import PIL.Image
import google.generativeai as genai

# Initialize FastHTML app
app = FastHTML()

# Ensure the uploads directory exists
os.makedirs("uploads", exist_ok=True)

def process_image(image_path, api_key):
    """Analyze image using Gemini and extract data"""
    try:
        # Configure API with user-provided key
        genai.configure(api_key=api_key)

        image = PIL.Image.open(image_path)
        model = genai.GenerativeModel(model_name="gemini-1.5-pro")

        # First check if it's a receipt
        is_receipt = model.generate_content(
            ["Is this image a picture of a receipt? Return only YES or NO.", image]
        ).text.strip().upper()

        if is_receipt == "YES":
            # If receipt, extract CSV data
            csv_response = model.generate_content([
                "Extract all text from this image and return it as a CSV file under appropriate headings. "
                "Return only the content of the csv file, no explanations.",
                image
            ])
            return f"Receipt detected:\n\n{csv_response.text}"
        return "Not a receipt - analysis stopped."

    except Exception as e:
        return f"API Error: {str(e)}"

@app.get("/")
def home():
    return Title("Receipt Analyzer"), Main(
        H1("Receipt Analysis System"),
        Form(
            Div(
                Label("Google Gemini API Key:", for_="api_key"),  # Changed For to for_
                Input(type="password", name="api_key", id="api_key", required=True,  # Added id
                      placeholder="Enter your API key", cls="mb-2"),
                cls="form-group"
            ),
            Div(
                Label("Receipt Image:", for_="image"),  # Changed here too
                Input(type="file", name="image", id="image", accept="image/*", required=True),  # Added id
                cls="form-group"
            ),
            Button("Analyze Receipt", type="submit", cls="primary"),
            enctype="multipart/form-data",
            hx_post="/analyze",
            hx_target="#result"
        ),
        Br(), Div(id="result"),
        cls="container"
    )

@app.post("/analyze")
async def handle_analysis(image: UploadFile, api_key: str):
    # Validate API key
    if not api_key.strip():
        return Div("❌ Error: API key is required!", cls="error")

    # Save the uploaded image
    image_path = f"uploads/{image.filename}"
    try:
        with open(image_path, "wb") as f:
            f.write(await image.read())

        # Process the image with user's API key
        analysis_result = process_image(image_path, api_key.strip())

        return Div(
            Pre(analysis_result) if "Receipt detected" in analysis_result else P(analysis_result),
            Img(src=f"/uploads/{image.filename}", alt="Uploaded image",
                style="max-width: 500px; margin-top: 20px; display: block;")
        )

    except Exception as e:
        return Div(f"Processing Error: {str(e)}", cls="error")

@app.get("/uploads/{filename}")
async def serve_upload(filename: str):
    return FileResponse(f"uploads/{filename}")

if __name__ == '__main__':
    uvicorn.run("main:app", host='0.0.0.0', port=int(os.getenv("PORT", default=5000)), reload=True)
