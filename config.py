import os

class StudioConfig:
    # مفتاح Supabase للتخزين السحابي الدائم
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "https://your-project.supabase.co")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "your-supabase-service-key")
    
    # مفتاح Replicate / Ideogram لتوليد الصور والفيديوهات
    REPLICATE_API_TOKEN: str = os.getenv("REPLICATE_API_TOKEN", "r8_your_replicate_token")
    
    # مفتاح OpenAI / Gemini لصياغة السيناريو
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "AIzaSy_your_gemini_key")
    
    # مفتاح ElevenLabs / Coqui للتعليق الصوتي الاحترافي
    ELEVENLABS_API_KEY: str = os.getenv("ELEVENLABS_API_KEY", "your_elevenlabs_key")
