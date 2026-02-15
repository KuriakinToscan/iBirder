from PIL import Image, ImageDraw
import math

def create_search_icon(path):
    size = (64, 64)
    # Transparent background
    image = Image.new("RGBA", size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(image)
    
    # Magnifying glass parameters
    center_x, center_y = 26, 26
    radius = 18
    handle_width = 8
    handle_length = 24
    
    # Draw handle (diagonal line)
    # Calculate start and end points for handle
    # 45 degrees
    angle = 45
    rad = math.radians(angle)
    
    # Handle start (at the circle edge)
    start_x = center_x + radius * math.cos(rad)
    start_y = center_y + radius * math.sin(rad)
    
    # Handle end
    end_x = start_x + handle_length * math.cos(rad)
    end_y = start_y + handle_length * math.sin(rad)
    
    draw.line([(start_x, start_y), (end_x, end_y)], fill="black", width=handle_width)
    
    # Draw circle (lens rim)
    # Outer circle
    draw.ellipse([center_x - radius, center_y - radius, center_x + radius, center_y + radius], fill=None, outline="black", width=5)
    
    image.save(path)
    print(f"Icon created at {path}")

create_search_icon("assets/search_loupe.png")
