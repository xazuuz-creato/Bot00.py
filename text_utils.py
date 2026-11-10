import arabic_reshaper
from bidi.algorithm import get_display

def fix_arabic_text(text: str) -> str:
    """
    إعادة تشكيل وتوجيه النص العربي لضمان تفادي التقطيع في FFmpeg و Remotion
    """
    if not text:
        return ""
    try:
        reshaped_text = arabic_reshaper.reshape(text)
        bidi_text = get_display(reshaped_text)
        return bidi_text
    except Exception as e:
        print(f"[Warning] Arabic Reshaper Error: {e}")
        return text
