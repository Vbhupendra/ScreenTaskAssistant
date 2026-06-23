from PIL import Image, ImageDraw
import os

def generate_icon(color, filename):
    # Create a 64x64 image with a transparent background
    image = Image.new('RGBA', (64, 64), (255, 255, 255, 0))
    draw = ImageDraw.Draw(image)
    
    # Draw a colored circle
    draw.ellipse((4, 4, 60, 60), fill=color, outline=(0, 0, 0))
    
    # Ensure assets directory exists
    if not os.path.exists('assets'):
        os.makedirs('assets')
        
    image.save(f'assets/{filename}')
    print(f"Generated assets/{filename}")

if __name__ == "__main__":
    generate_icon('green', 'icon_idle.png')
    generate_icon('blue', 'icon_thinking.png')
    generate_icon('yellow', 'icon_speaking.png')
