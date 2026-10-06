# OwnACar Background Removal API

Removes background from car images and adds a professional turntable/stage effect.

## Features
- AI-powered background removal using rembg (U2-Net model)
- Adds Cars24-style turntable platform
- Gradient background (white to light gray)
- Shadow effect under the car
- 100% free, no API limits

## Local Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run server
python main.py
```

Server runs at http://localhost:8000

## API Endpoints

### POST /remove-background
Upload an image file, returns processed JPEG.

```bash
curl -X POST "http://localhost:8000/remove-background" \
  -F "file=@car_image.jpg" \
  --output processed_car.jpg
```

### POST /remove-background-base64
Upload an image file, returns base64 encoded image.

```bash
curl -X POST "http://localhost:8000/remove-background-base64" \
  -F "file=@car_image.jpg"
```

### GET /health
Health check endpoint.

## Deploy to Render.com (Free)

1. Push this folder to a GitHub repository
2. Go to https://render.com
3. Click "New" → "Web Service"
4. Connect your GitHub repo
5. Select the `bg-removal-api` folder
6. Render will auto-detect the Dockerfile
7. Click "Create Web Service"

Your API will be live at: `https://ownacar-bg-removal.onrender.com`

## Environment Variables

None required for basic operation.

## Notes

- First request after cold start takes ~30 seconds (model loading)
- Subsequent requests: 2-5 seconds per image
- Max file size: 10MB
- Supported formats: JPEG, PNG, WebP
