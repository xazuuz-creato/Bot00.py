import re
from PIL import features

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    _HAS_SHAPER = True
except Exception:
    _HAS_SHAPER = False

HAS_RAQM = features.check("raqm")
_AR = re.compile(r"[\u0600-\u06FF\u0750-\u077F]")


def has_arabic(text: str) -> bool:
    return bool(_AR.search(text or ""))


def fix_arabic_text(text: str) -> str:
    if not text:
        return ""
    if not _HAS_SHAPER:
        return text
    try:
        return get_display(arabic_reshaper.reshape(text))
    except Exception as e:
        print(f"[Warning] Arabic Reshaper Error: {e}")
        return text


def for_pil(text: str):
    """يرجع (النص المهيأ, kwargs لـ draw.text / textlength)."""
    if not has_arabic(text):
        return text, {}
    if HAS_RAQM:
        return text, {"direction": "rtl", "language": "ar"}
    return fix_arabic_text(text), {}
