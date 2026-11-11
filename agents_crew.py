import json
import re

from config import StudioConfig
from net import request_json

SYSTEM_PROMPT = """أنت المخرج التنفيذي لاستديو فيديو موشن جرافيك. تستلم فكرة فيديو ونمط تصميم وإعداد إخراج (وثائقي/سينمائي/ديناميكي)
وتكتب سيناريو مشاهد قصيرة. أعد JSON صافياً فقط بدون أي مقدمات أو علامات ```، بهذا الشكل بالضبط:
{"title": "...", "scenes": [{"narration": "نص التعليق الصوتي بالعربية الفصحى المبسطة، جملة أو جملتان",
 "on_screen_text": "نص قصير يظهر على الشاشة (حتى 10 كلمات) بالعربية",
 "visual_prompt": "English prompt describing the background image for this scene, no text in the image"}]}
قواعد: عدد المشاهد حسب المطلوب تماماً. الإيقاع حسب الإعداد: وثائقي=هادئ ومعلوماتي، سينمائي=درامي، ديناميكي=سريع ومختصر.
visual_prompt يجب أن يعكس نمط التصميم المطلوب. لا تضف أي حقائق مختلقة أو أرقام غير موثوقة."""


class MasterDirectorAgent:
    def __init__(self):
        self.role = "Senior Art Director & Quality Auditor"

    async def plan(self, idea: str, style: dict, prop_name: str, duration: int):
        """يرجع (scenes, title, warnings)."""
        n = max(2, min(StudioConfig.MAX_SCENES, round(duration / 6)))
        warnings = []
        if StudioConfig.ANTHROPIC_API_KEY:
            try:
                scenes, title = await self._plan_with_claude(idea, style, prop_name, n)
                return scenes, title, warnings
            except Exception as e:
                warnings.append(f"فشل كلود في كتابة السيناريو ({str(e)[:100]}) - استُخدم التقسيم المحلي.")
        else:
            warnings.append("ANTHROPIC_API_KEY غير مضبوط - استُخدم تقسيم محلي لنص الفكرة بدل كتابة سيناريو بالذكاء الاصطناعي.")
        scenes, title = self._local_plan(idea, style, n)
        return scenes, title, warnings

    async def _plan_with_claude(self, idea, style, prop_name, n):
        body = {
            "model": StudioConfig.ANTHROPIC_MODEL,
            "max_tokens": min(16000, 1000 + 350 * n),
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": json.dumps({
                "video_idea": idea, "design_style": style["name"],
                "property_setting": prop_name, "scenes_count": n}, ensure_ascii=False)}],
        }
        headers = {"x-api-key": StudioConfig.ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01"}
        status, data = await request_json("POST", f"{StudioConfig.ANTHROPIC_BASE_URL}/v1/messages",
                                          headers, body, timeout=240)
        if status != 200:
            raise RuntimeError(f"HTTP {status}: {str(data)[:150]}")
        text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
        parsed = self._parse_json(text)
        scenes = []
        for sc in parsed.get("scenes", [])[:n]:
            narr = str(sc.get("narration", "")).strip()
            if not narr:
                continue
            scenes.append({
                "narration": narr,
                "on_screen_text": str(sc.get("on_screen_text") or narr)[:120].strip(),
                "visual_prompt": str(sc.get("visual_prompt") or idea).strip(),
            })
        if not scenes:
            raise RuntimeError("الاستجابة لا تحتوي مشاهد صالحة")
        return scenes, str(parsed.get("title", idea))[:80]

    @staticmethod
    def _parse_json(text: str) -> dict:
        text = re.sub(r"```(?:json)?", "", text).strip()
        a, b = text.find("{"), text.rfind("}")
        if a == -1 or b == -1:
            raise ValueError("no JSON found")
        return json.loads(text[a:b + 1])

    @staticmethod
    def _local_plan(idea, style, n):
        words = idea.split()
        n = max(1, min(n, len(words) // 4 or 1))
        size = -(-len(words) // n)
        chunks = [" ".join(words[i:i + size]) for i in range(0, len(words), size)]
        scenes = [{"narration": c, "on_screen_text": c, "visual_prompt": f"{idea[:100]}"} for c in chunks]
        return scenes, idea[:60]

    def process_topic_to_uap(self, topic: str) -> str:
        return json.dumps({"sender": "MasterDirector_Agent", "content": topic}, ensure_ascii=False)
