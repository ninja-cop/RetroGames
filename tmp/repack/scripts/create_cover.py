from PIL import Image, ImageDraw, ImageFont

W, H = 630, 500
# Create gradient background (dark blue to near-black)
img = Image.new('RGB', (W, H), '#000')
d = ImageDraw.Draw(img)
for y in range(H):
    t = y / (H - 1)
    # gradient from #0b1533 to #02020a
    r = int(11 * (1 - t) + 2 * t)
    g = int(21 * (1 - t) + 2 * t)
    b = int(51 * (1 - t) + 10 * t)
    d.line([(0, y), (W, y)], fill=(r, g, b))

# Draw moon (simple circle)
moon_center = (W - 140, 120)
moon_radius = 70
d.ellipse([moon_center[0]-moon_radius, moon_center[1]-moon_radius, moon_center[0]+moon_radius, moon_center[1]+moon_radius], fill=(255,245,200))

# Draw pixel-style stars
import random
for _ in range(90):
    x = random.randint(10, W-10)
    y = random.randint(10, H-10)
    size = random.choice([1,1,2])
    d.rectangle([x, y, x+size, y+size], fill=(255,255,230))

# Titles
title_jp = '月下の陣'
subtitle_jp = '月夜に刻む一手の運命'
title_en = 'Moonlit Formation'

# Try to load TTF fonts; fallback to default if not found
try:
    # Japanese font
    jp_font_path = 'C:/Windows/Fonts/MSGOTHIC.TTC'
    title_font = ImageFont.truetype(jp_font_path, 72)
    subtitle_font = ImageFont.truetype(jp_font_path, 28)
except Exception:
    title_font = ImageFont.load_default()
    subtitle_font = ImageFont.load_default()

try:
    en_font_path = 'C:/Windows/Fonts/arial.ttf'
    en_font = ImageFont.truetype(en_font_path, 28)
except Exception:
    en_font = ImageFont.load_default()

# draw Japanese title with slight shadow
tx, ty = 40, H//2 - 30
shadow_color = (0,0,0)
text_color = (255,245,230)

d.text((tx+2, ty+2), title_jp, font=title_font, fill=shadow_color)
d.text((tx, ty), title_jp, font=title_font, fill=text_color)
# Japanese subtitle
d.text((tx, ty+80), subtitle_jp, font=subtitle_font, fill=(200,200,190))

# English title below the Japanese subtitle
en_x = tx
en_y = ty + 80 + 36
d.text((en_x+1, en_y+1), title_en, font=en_font, fill=(0,0,0))
d.text((en_x, en_y), title_en, font=en_font, fill=(235,230,210))

# Save
out_path = '../cover_630x500.png'
img.save(out_path)
print('Wrote', out_path)
