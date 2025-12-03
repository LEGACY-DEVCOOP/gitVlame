from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import httpx
from supabase import create_client, Client
from app.config import settings
import asyncio

class ImageService:
    def __init__(self):
        self.supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        self.bucket_name = "blame-images"

    async def generate_blame_image(self, params: dict) -> str:
        # 1. Create Background
        width, height = 1200, 630
        image = Image.new('RGB', (width, height))
        draw = ImageDraw.Draw(image)
        
        # Gradient Background (Red to Orange)
        # Simplified gradient: just interpolate top to bottom
        for y in range(height):
            r = int(255 - (y / height) * 0) # Keep red high
            g = int(107 + (y / height) * (165 - 107)) # 6B -> A5
            b = int(107 - (y / height) * 107) # 6B -> 00
            # Color interpolation is rough here, let's use the hex values from prompt
            # #FF6B6B (255, 107, 107) -> #FFA500 (255, 165, 0)
            r = 255
            g = int(107 + (y / height) * (165 - 107))
            b = int(107 - (y / height) * 107)
            draw.line([(0, y), (width, y)], fill=(r, g, b))

        # 2. Fonts (Using default or trying to load system font if possible, otherwise fallback)
        # In a real env, we'd bundle a font file. Here we'll try to use a default or simple load.
        try:
            # Try to load a font (e.g., AppleGothic on Mac or standard paths)
            # For robustness in this environment, we might need to rely on default or a specific path if known.
            # Let's assume a font file exists or use default.
            # Since I can't easily download a font here without external access guaranteed, I will use default but scale it if possible.
            # PIL default font is very small.
            # I will try to load a common font.
            title_font = ImageFont.truetype("/System/Library/Fonts/Supplemental/AppleGothic.ttf", 60)
            text_font = ImageFont.truetype("/System/Library/Fonts/Supplemental/AppleGothic.ttf", 40)
            small_font = ImageFont.truetype("/System/Library/Fonts/Supplemental/AppleGothic.ttf", 30)
        except:
            title_font = ImageFont.load_default()
            text_font = ImageFont.load_default()
            small_font = ImageFont.load_default()

        # 3. Draw Text
        # Header
        draw.text((width//2, 50), "🔥 GitBlame 판결문 🔥", font=title_font, fill="white", anchor="mm")
        
        # Project Info
        draw.text((100, 150), f"📂 프로젝트: {params['repo_name']}", font=text_font, fill="white")
        draw.text((100, 200), f"🚨 사건: {params['title']}", font=text_font, fill="white")
        draw.text((100, 250), f"📅 발생일: {params['created_at'].strftime('%Y-%m-%d')}", font=text_font, fill="white")
        
        # Target Info
        draw.text((width//2, 350), "🏆 오늘의 범인 🏆", font=title_font, fill="white", anchor="mm")
        draw.text((width//2, 550), f"{params['target_username']}", font=text_font, fill="white", anchor="mm")
        draw.text((width//2, 600), f"책임도 {params['responsibility']}%", font=text_font, fill="white", anchor="mm")
        
        # Commit Msg
        draw.text((width//2, 700), f"\"{params['last_commit_msg']}\" 커밋이", font=text_font, fill="white", anchor="mm")
        draw.text((width//2, 750), "화근이었습니다...", font=text_font, fill="white", anchor="mm")
        
        # Coffee
        coffee_count = max(1, params['responsibility'] // 20)
        draw.text((width//2, 850), f"☕ 커피 {coffee_count}잔 추천", font=title_font, fill="white", anchor="mm")

        # 4. Avatar (Download and Paste)
        if params.get('target_avatar'):
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(params['target_avatar'])
                    if resp.status_code == 200:
                        avatar_img = Image.open(BytesIO(resp.content)).convert("RGBA")
                        avatar_img = avatar_img.resize((150, 150))
                        
                        # Circular mask
                        mask = Image.new('L', (150, 150), 0)
                        draw_mask = ImageDraw.Draw(mask)
                        draw_mask.ellipse((0, 0, 150, 150), fill=255)
                        
                        image.paste(avatar_img, (width//2 - 75, 400), mask)
            except Exception as e:
                print(f"Failed to load avatar: {e}")

        # 5. Save to Bytes
        output = BytesIO()
        image.save(output, format="PNG")
        image_bytes = output.getvalue()
        
        # 6. Upload
        filename = f"{params['judgment_id']}.png"
        return await self.upload_to_supabase(image_bytes, filename)

    async def upload_to_supabase(self, image_bytes: bytes, filename: str) -> str:
        try:
            # Run sync upload in thread
            await asyncio.to_thread(
                self.supabase.storage.from_(self.bucket_name).upload,
                path=filename,
                file=image_bytes,
                file_options={"content-type": "image/png", "upsert": "true"}
            )
            
            # Get Public URL
            return self.supabase.storage.from_(self.bucket_name).get_public_url(filename)
        except Exception as e:
            # If upload fails, maybe bucket doesn't exist or auth error.
            # Return a placeholder or raise
            print(f"Upload failed: {e}")
            raise e
