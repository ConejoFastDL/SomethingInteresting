"""
Image Generator for CS2 Movement Recorder Pro

This script generates all the necessary icons and assets for the application.
"""
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

def create_directory(directory):
    """Create a directory if it doesn't exist"""
    if not os.path.exists(directory):
        os.makedirs(directory)

def generate_app_icon():
    """Generate the main application icon"""
    # Create images directory
    img_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images")
    create_directory(img_dir)
    
    # Create an icon (512x512)
    size = 512
    icon = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(icon)
    
    # Draw a rounded rectangle for the base
    bg_color = (0, 122, 204)  # Blue color
    radius = 80
    draw.rounded_rectangle([(50, 50), (size-50, size-50)], radius, fill=bg_color)
    
    # Draw the "play" triangle
    play_color = (255, 255, 255)  # White color
    points = [(size//3, size//3), (size//3, 2*size//3), (2*size//3, size//2)]
    draw.polygon(points, fill=play_color)
    
    # Add a circular record button
    record_color = (232, 17, 35)  # Red color
    record_center = (size//2 + size//4, size//2 + size//4)
    record_radius = size//8
    draw.ellipse((record_center[0]-record_radius, record_center[1]-record_radius, 
                  record_center[0]+record_radius, record_center[1]+record_radius), 
                  fill=record_color)
    
    # Apply a slight drop shadow
    shadow = Image.new('RGBA', icon.size, (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.rounded_rectangle([(55, 55), (size-45, size-45)], radius, fill=(0, 0, 0, 100))
    shadow = shadow.filter(ImageFilter.GaussianBlur(10))
    
    # Combine the images
    result = Image.alpha_composite(shadow, icon)
    
    # Save the icon in different formats and sizes
    result.save(os.path.join(img_dir, "icon.png"))
    
    # Create .ico file for Windows
    icon_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    icons = [result.resize(size, Image.Resampling.LANCZOS) for size in icon_sizes]
    
    result.save(os.path.join(img_dir, "icon.ico"), sizes=icon_sizes)
    
    # Create smaller icons for status indicators
    status_size = 24
    for color, name in [
        ((232, 17, 35), "recording"),     # Red for recording
        ((255, 105, 97), "recording_pulse"),  # Lighter red for recording pulse
        ((0, 122, 204), "playing"),       # Blue for playing
        ((128, 128, 128), "not_recording"), # Gray for not recording
        ((0, 183, 74), "ready"),          # Green for ready
        ((128, 128, 128), "no_file")      # Gray for no file
    ]:
        status_icon = Image.new('RGBA', (status_size, status_size), (0, 0, 0, 0))
        status_draw = ImageDraw.Draw(status_icon)
        
        if name == "recording":
            # Circle for recording
            status_draw.ellipse((2, 2, status_size-2, status_size-2), fill=color)
        elif name == "recording_pulse":
            # Pulsing record icon - circle with a ring
            status_draw.ellipse((2, 2, status_size-2, status_size-2), fill=color)
            status_draw.ellipse((6, 6, status_size-6, status_size-6), fill=(255, 255, 255, 100))
        elif name == "playing":
            # Triangle for playing
            points = [(4, 2), (4, status_size-2), (status_size-4, status_size//2)]
            status_draw.polygon(points, fill=color)
        elif name == "ready":
            # Checkmark for ready
            points = [(4, status_size//2), (status_size//3, status_size-4), 
                      (status_size-4, 4), (status_size//2, status_size//2)]
            status_draw.polygon(points, fill=color)
        else:
            # Circle with slash for not recording or no file
            status_draw.ellipse((2, 2, status_size-2, status_size-2), outline=color, width=2)
            status_draw.line((4, 4, status_size-4, status_size-4), fill=color, width=2)
            
        # Save directly with the name (no prefix)
        status_icon.save(os.path.join(img_dir, f"{name}.png"))
        
    print(f"Icons generated in {img_dir}")

def generate_logo():
    """Generate a logo for the application"""
    img_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images")
    create_directory(img_dir)
    
    # Create a logo (200x200)
    width, height = 200, 200
    logo = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(logo)
    
    # Draw a rounded rectangle for the base
    bg_color = (0, 122, 204)  # Blue color
    radius = 30
    draw.rounded_rectangle([(20, 20), (width-20, height-20)], radius, fill=bg_color)
    
    # Draw stylized "CS2" text
    try:
        font_path = os.path.join(os.environ.get('WINDIR', ''), 'Fonts', 'Arial.ttf')
        font = ImageFont.truetype(font_path, 60)
        draw.text((width//2, height//2-30), "CS2", fill=(255, 255, 255), font=font, anchor="mm")
    except Exception:
        # Fallback if no font available
        draw.text((width//2-40, height//2-40), "CS2", fill=(255, 255, 255))
    
    # Draw mouse cursor icon
    cursor_color = (255, 255, 255)  # White
    cursor_points = [
        (width//2-30, height//2+30),
        (width//2-10, height//2+30),
        (width//2-10, height//2+40),
        (width//2, height//2+50),
        (width//2+10, height//2+40),
        (width//2+10, height//2+20),
        (width//2+20, height//2+10),
        (width//2+30, height//2),
        (width//2+10, height//2-10),
        (width//2-10, height//2+10),
    ]
    draw.polygon(cursor_points, fill=cursor_color)
    
    # Save the logo
    logo.save(os.path.join(img_dir, "logo.png"))
    print(f"Logo generated in {img_dir}")

def generate_control_icons():
    """Generate control button icons"""
    img_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images")
    create_directory(img_dir)
    
    # Button icon size
    size = 24
    icons = {
        "record": {
            "color": (232, 17, 35),  # Red
            "shape": "circle"
        },
        "stop": {
            "color": (232, 17, 35),  # Red
            "shape": "square"
        },
        "play": {
            "color": (0, 183, 74),  # Green
            "shape": "triangle"
        },
        "pause": {
            "color": (0, 122, 204),  # Blue
            "shape": "double_bar"
        }
    }
    
    for name, config in icons.items():
        icon = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(icon)
        
        if config["shape"] == "circle":
            # Circle for record
            draw.ellipse((4, 4, size-4, size-4), fill=config["color"])
        elif config["shape"] == "square":
            # Square for stop
            draw.rectangle((4, 4, size-4, size-4), fill=config["color"])
        elif config["shape"] == "triangle":
            # Triangle for play
            points = [(4, 2), (4, size-2), (size-4, size//2)]
            draw.polygon(points, fill=config["color"])
        elif config["shape"] == "double_bar":
            # Double bar for pause
            draw.rectangle((4, 2, size//2-2, size-2), fill=config["color"])
            draw.rectangle((size//2+2, 2, size-4, size-2), fill=config["color"])
            
        icon.save(os.path.join(img_dir, f"{name}_icon.png"))
    
    print(f"Control icons generated in {img_dir}")

if __name__ == "__main__":
    generate_app_icon()
    generate_logo()
    generate_control_icons()
    print("All images generated successfully.")
