import os
from pathlib import Path


class StudioConfig:
    BASE_DIR = Path(__file__).resolve().parent
    OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", BASE_DIR / "outputs"))
    WORK_DIR = Path(os.getenv("WORK_DIR", BASE_DIR / "work"))

    WIDTH = int(os.getenv("VIDEO_WIDTH", 1280))
    HEIGHT = int(os.getenv("VIDEO_HEIGHT", 720))
    MAX_SCENES = int(os.getenv("MAX_SCENES", 60))
    MAX_DURATION = int(os.getenv("MAX_DURATION", 300))   # أقصى مدة مطلوبة بالثواني
    MAX_CONCURRENT_JOBS = int(os.getenv("MAX_CONCURRENT_JOBS", 1))
    KEEP_OUTPUTS_HOURS = int(os.getenv("KEEP_OUTPUTS_HOURS", 24))

    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5")
    ANTHROPIC_BASE_URL = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com")

    REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN", "")
    REPLICATE_MODEL = os.getenv("REPLICATE_MODEL", "black-forest-labs/flux-schnell")
    REPLICATE_BASE_URL = os.getenv("REPLICATE_BASE_URL", "https://api.replicate.com")
    REPLICATE_POLL_SECONDS = float(os.getenv("REPLICATE_POLL_SECONDS", 1.5))

    TTS_VOICE = os.getenv("TTS_VOICE", "ar-SA-HamedNeural")
    FONT_PATH = os.getenv("FONT_PATH", "")

    SUPABASE_URL = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
    SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "videos")

    @classmethod
    def status(cls) -> dict:
        try:
            import edge_tts  # noqa: F401
            tts = True
        except ImportError:
            tts = False
        return {
            "script_llm_claude": bool(cls.ANTHROPIC_API_KEY),
            "ai_images_replicate": bool(cls.REPLICATE_API_TOKEN),
            "voice_edge_tts": tts,
            "cloud_upload_supabase": bool(cls.SUPABASE_URL and cls.SUPABASE_KEY),
        }
