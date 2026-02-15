from PIL import Image, ImageDraw
import math

def create_gear_icon(path):
    size = (64, 64)
    image = Image.new("RGBA", size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(image)
    
    center = (32, 32)
    outer_radius = 28
    inner_radius = 20
    hole_radius = 10
    num_teeth = 8
    
    # Draw teeth
    for i in range(num_teeth):
        angle = (360 / num_teeth) * i
        start_angle = angle - 10
        end_angle = angle + 10
        
        # Convert to radians
        start_rad = math.radians(start_angle)
        end_rad = math.radians(end_angle)
        
        # Points for tooth
        p1 = (center[0] + inner_radius * math.cos(start_rad), center[1] + inner_radius * math.sin(start_rad))
        p2 = (center[0] + outer_radius * math.cos(start_rad), center[1] + outer_radius * math.sin(start_rad))
        p3 = (center[0] + outer_radius * math.cos(end_rad), center[1] + outer_radius * math.sin(end_rad))
        p4 = (center[0] + inner_radius * math.cos(end_rad), center[1] + inner_radius * math.sin(end_rad))
        
        draw.polygon([p1, p2, p3, p4], fill="black")

    # Draw main circle
    draw.ellipse([center[0]-inner_radius, center[1]-inner_radius, center[0]+inner_radius, center[1]+inner_radius], fill="black")
    
    # Draw center hole (transparent)
    draw.ellipse([center[0]-hole_radius, center[1]-hole_radius, center[0]+hole_radius, center[1]+hole_radius], fill=(0,0,0,0), outline=None)
    
    # Make hole transparent explicitly by masking? 
    # Actually simpler: Draw white hole then make white transparent? No, better use alpha composite or just draw everything on a mask.
    # Simpler approach: 
    # just draw black circle with hole?
    # Let's redraw the center hole with clear mode.
    
    # Re-create image to be safe for transparency operations
    img_final = Image.new("RGBA", size, (255, 255, 255, 0))
    d = ImageDraw.Draw(img_final)
    
    # Draw the black parts
    # Teeth
    for i in range(num_teeth):
        angle = (360 / num_teeth) * i
        start_angle = angle - 12
        end_angle = angle + 12
        start_rad = math.radians(start_angle)
        end_rad = math.radians(end_angle)
        p1 = (center[0] + (inner_radius-1) * math.cos(start_rad), center[1] + (inner_radius-1) * math.sin(start_rad))
        p2 = (center[0] + outer_radius * math.cos(start_rad), center[1] + outer_radius * math.sin(start_rad))
        p3 = (center[0] + outer_radius * math.cos(end_rad), center[1] + outer_radius * math.sin(end_rad))
        p4 = (center[0] + (inner_radius-1) * math.cos(end_rad), center[1] + (inner_radius-1) * math.sin(end_rad))
        d.polygon([p1, p2, p3, p4], fill="black")

    # Body
    d.ellipse([center[0]-inner_radius, center[1]-inner_radius, center[0]+inner_radius, center[1]+inner_radius], fill="black")
    
    # Hole (Clear)
    d.ellipse([center[0]-hole_radius, center[1]-hole_radius, center[0]+hole_radius, center[1]+hole_radius], fill=(0,0,0,0), outline="black") 
    # Wait, fill (0,0,0,0) on RGBA just draws nothing if over existing. usage: blend modes.
    # PIL defaults to over. We need to cut out.
    
    # Proper way: Create mask
    mask = Image.new("L", size, 0)
    draw_mask = ImageDraw.Draw(mask)
    
    # Draw opaque parts on mask
    for i in range(num_teeth):
        angle = (360 / num_teeth) * i
        start_angle = angle - 15
        end_angle = angle + 15
        start_rad = math.radians(start_angle)
        end_rad = math.radians(end_angle)
        p1 = (center[0] + (inner_radius-2) * math.cos(start_rad), center[1] + (inner_radius-2) * math.sin(start_rad))
        p2 = (center[0] + outer_radius * math.cos(start_rad), center[1] + outer_radius * math.sin(start_rad))
        p3 = (center[0] + outer_radius * math.cos(end_rad), center[1] + outer_radius * math.sin(end_rad))
        p4 = (center[0] + (inner_radius-2) * math.cos(end_rad), center[1] + (inner_radius-2) * math.sin(end_rad))
        draw_mask.polygon([p1, p2, p3, p4], fill=255)
        
    draw_mask.ellipse([center[0]-inner_radius, center[1]-inner_radius, center[0]+inner_radius, center[1]+inner_radius], fill=255)
    draw_mask.ellipse([center[0]-hole_radius, center[1]-hole_radius, center[0]+hole_radius, center[1]+hole_radius], fill=0) # Cut hole
    
    # Create solid black image
    black_img = Image.new("RGBA", size, "black")
    black_img.putalpha(mask)
    
    black_img.save(path)
    print(f"Icon created at {path}")

create_gear_icon("assets/config_gear.png")
