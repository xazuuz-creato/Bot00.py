import os

from config import StudioConfig
from net import request


class StudioToolsLibrary:
    def __init__(self):
        self.enabled_tools = ["supabase_cloud_uploader"]

    async def upload_to_cloud_storage(self, file_path: str, task_id: str):
        if not (StudioConfig.SUPABASE_URL and StudioConfig.SUPABASE_KEY):
            return None
        with open(file_path, "rb") as f:
            data = f.read()
        key = StudioConfig.SUPABASE_KEY
        name = f"{task_id}{os.path.splitext(file_path)[1]}"
        url = f"{StudioConfig.SUPABASE_URL}/storage/v1/object/{StudioConfig.SUPABASE_BUCKET}/{name}"
        st, raw = await request("POST", url, {"Authorization": f"Bearer {key}", "apikey": key,
                                              "Content-Type": "video/mp4", "x-upsert": "true"}, data, timeout=180)
        if st not in (200, 201):
            raise RuntimeError(f"Supabase HTTP {st}: {raw[:120]!r}")
        return f"{StudioConfig.SUPABASE_URL}/storage/v1/object/public/{StudioConfig.SUPABASE_BUCKET}/{name}"
