import os
import io
import threading
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from PIL import Image, ImageDraw, ImageFilter
from contextlib import asynccontextmanager

# Lazy load rembg to avoid startup issues
_rembg_session = None
_model_loading = False

def get_rembg():
    global _rembg_session, _model_loading
    if _rembg_session is None and not _model_loading:
        _model_loading = True
        from rembg import remove, new_session
        # Use silueta (43MB) - fast, lightweight, works on free-tier servers
        _rembg_session = new_session("silueta")
        _model_loading = False
    return _rembg_session

def preload_model():
    """Preload model in background thread on startup"""
    print("Preloading rembg model...")
    get_rembg()
    print("Model preloaded and ready!")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: preload model in background
    thread = threading.Thread(target=preload_model)
    thread.start()
    yield
    # Shutdown: nothing to clean up

app = FastAPI(title="OwnACar Background Removal API", lifespan=lifespan)

def remove_bg(image_bytes):
    from rembg import remove
    session = get_rembg()
    return remove(image_bytes, session=session)

# CORS for your frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update with your domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def create_turntable_background(width: int, height: int) -> Image.Image:
    """Create a Cars24-style turntable background with stage"""
    
    # Create gradient background (light gray to white)
    bg = Image.new('RGB', (width, height), (245, 245, 245))
    draw = ImageDraw.Draw(bg)
    
    # Gradient from top (lighter) to bottom (slightly darker before platform)
    for y in range(height):
        # Top 70% is gradient white to light gray
        if y < height * 0.7:
            ratio = y / (height * 0.7)
            gray = int(250 - (ratio * 15))  # 250 to 235
            draw.line([(0, y), (width, y)], fill=(gray, gray, gray))
    
    return bg

def add_turntable_platform(bg: Image.Image) -> Image.Image:
    """Add the dark circular turntable platform at the bottom"""
    width, height = bg.size
    draw = ImageDraw.Draw(bg)
    
    # Platform parameters
    platform_y = int(height * 0.78)  # Where platform starts
    platform_height = int(height * 0.08)
    ellipse_width = int(width * 0.85)
    ellipse_x_start = (width - ellipse_width) // 2
    
    # Draw the dark elliptical platform
    # Main platform (dark gray)
    platform_color = (60, 60, 65)
    draw.ellipse([
        ellipse_x_start, 
        platform_y,
        ellipse_x_start + ellipse_width, 
        platform_y + platform_height * 2
    ], fill=platform_color)
    
    # Platform highlight ring (slightly lighter)
    ring_color = (80, 80, 85)
    ring_width = 3
    draw.ellipse([
        ellipse_x_start + 10, 
        platform_y + 5,
        ellipse_x_start + ellipse_width - 10, 
        platform_y + platform_height * 2 - 5
    ], outline=ring_color, width=ring_width)
    
    # Inner darker circle
    inner_ellipse_width = int(ellipse_width * 0.7)
    inner_x_start = (width - inner_ellipse_width) // 2
    inner_color = (45, 45, 50)
    draw.ellipse([
        inner_x_start,
        platform_y + platform_height * 0.3,
        inner_x_start + inner_ellipse_width,
        platform_y + platform_height * 1.7
    ], fill=inner_color)
    
    return bg

def add_car_shadow(bg: Image.Image, car_mask: Image.Image, car_bbox: tuple) -> Image.Image:
    """Add a subtle shadow under the car"""
    width, height = bg.size
    
    if car_bbox:
        left, top, right, bottom = car_bbox
        car_width = right - left
        car_center_x = (left + right) // 2
        
        # Create shadow ellipse
        shadow = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow)
        
        shadow_width = int(car_width * 0.9)
        shadow_height = int(shadow_width * 0.15)
        shadow_y = int(height * 0.76)
        
        shadow_x_start = car_center_x - shadow_width // 2
        
        # Draw shadow ellipse
        shadow_draw.ellipse([
            shadow_x_start,
            shadow_y,
            shadow_x_start + shadow_width,
            shadow_y + shadow_height
        ], fill=(0, 0, 0, 60))
        
        # Blur the shadow
        shadow = shadow.filter(ImageFilter.GaussianBlur(radius=15))
        
        # Composite shadow onto background
        bg = Image.alpha_composite(bg.convert('RGBA'), shadow).convert('RGB')
    
    return bg

def process_car_image(image_bytes: bytes) -> bytes:
    """Remove background and add turntable effect"""
    
    # Load original image
    original = Image.open(io.BytesIO(image_bytes)).convert('RGBA')
    width, height = original.size
    
    # Remove background using rembg (lazy loaded)
    output_bytes = remove_bg(image_bytes)
    car_no_bg = Image.open(io.BytesIO(output_bytes)).convert('RGBA')
    
    # Get car bounding box (non-transparent area)
    bbox = car_no_bg.getbbox()
    
    # Create turntable background
    background = create_turntable_background(width, height)
    background = add_turntable_platform(background)
    
    # Add shadow
    if bbox:
        background = add_car_shadow(background, car_no_bg.split()[3], bbox)
    
    # Composite car onto background
    background = background.convert('RGBA')
    
    # Position car - move it up slightly so it sits on the platform
    car_y_offset = -int(height * 0.02)  # Slight upward adjustment
    
    # Create a new image for positioning
    positioned_car = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    positioned_car.paste(car_no_bg, (0, car_y_offset), car_no_bg)
    
    # Final composite
    final = Image.alpha_composite(background, positioned_car)
    
    # Convert to RGB and save as JPEG
    final_rgb = final.convert('RGB')
    
    output_buffer = io.BytesIO()
    final_rgb.save(output_buffer, format='JPEG', quality=92)
    output_buffer.seek(0)
    
    return output_buffer.getvalue()

@app.get("/")
async def root():
    return {"status": "ok", "service": "OwnACar Background Removal API"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/remove-background")
async def remove_background(file: UploadFile = File(...)):
    """
    Remove background from car image and add turntable effect.
    Returns processed image as JPEG.
    """
    
    # Validate file type
    if not file.content_type or not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # Read file
    contents = await file.read()
    
    # Check file size (max 10MB)
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Max 10MB.")
    
    try:
        # Process image
        processed_image = process_car_image(contents)
        
        return Response(
            content=processed_image,
            media_type="image/jpeg",
            headers={
                "Content-Disposition": f"inline; filename=processed_{file.filename}"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")

@app.post("/remove-background-base64")
async def remove_background_base64(file: UploadFile = File(...)):
    """
    Remove background and return as base64 string.
    Useful for direct frontend integration.
    """
    import base64
    
    if not file.content_type or not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    contents = await file.read()
    
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Max 10MB.")
    
    try:
        processed_image = process_car_image(contents)
        base64_image = base64.b64encode(processed_image).decode('utf-8')
        
        return {
            "success": True,
            "image": f"data:image/jpeg;base64,{base64_image}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
