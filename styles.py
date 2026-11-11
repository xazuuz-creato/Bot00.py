import re


def _s(name, c1, c2, accent, text, motif, tstyle, fx, prompt):
    return dict(name=name, c1=c1, c2=c2, accent=accent, text=text,
                motif=motif, tstyle=tstyle, fx=fx, prompt=prompt)


STYLES_LIST = [
    _s("الموشن جرافيك الحديث (Minimal Motion)", "#0f172a", "#1e293b", "#38bdf8", "#ffffff", "dots", "shadow", "", "clean minimal motion graphics, flat shapes, soft gradients"),
    _s("فلوج وتيك توك (Viral TikTok/Reels)", "#7c3aed", "#db2777", "#facc15", "#ffffff", "rays", "outline", "eq=saturation=1.2", "vibrant social media vlog look, bold colors, trending"),
    _s("الشرح التقني والمستقبلي (Cyberpunk/Tech)", "#050816", "#0b1f3a", "#22d3ee", "#e0f2fe", "grid", "glow", "", "cyberpunk futuristic technology, neon blue holograms, circuits"),
    _s("الرسوم الكرتونية (2D/3D Cartoon)", "#38bdf8", "#a7f3d0", "#ffffff", "#ffffff", "blocks", "outline", "", "colorful 3D cartoon illustration, soft lighting, playful"),
    _s("السرد التراثي والتاريخي (Vintage/Historical)", "#3b2a1a", "#8b6b3d", "#f5deb3", "#fff3d6", "paper", "box", "eq=saturation=0.7:contrast=1.05", "aged parchment manuscript, historical engraving, sepia"),
    _s("الغموض والرعب النفسي (Dark Horror)", "#050505", "#3b0a0a", "#ef4444", "#e5e5e5", "noise", "shadow", "eq=contrast=1.25:brightness=-0.04,noise=alls=10:allf=t", "dark psychological horror, fog, deep shadows, eerie"),
    _s("ريلز إنستغرام الجمالي (Aesthetic Minimalist)", "#e7d9c5", "#c9b79c", "#5b4636", "#3d2f24", "none", "plain", "", "aesthetic minimalist photography, earthy tones, natural light"),
    _s("النيون المضيء المتوهج (Glow Neon)", "#09090b", "#1e1b4b", "#f0abfc", "#ffffff", "rings", "glow", "", "glowing neon lights on dark background, bloom, vivid colors"),
    _s("الخطوط العربية الحرة (Arabic Calligraphy Art)", "#0c0a09", "#292524", "#fbbf24", "#fde68a", "waves", "glow", "", "arabic calligraphy art, golden brush strokes, dark cinematic space"),
    _s("قصص الكوميكس والمانجا (Comic/Manga)", "#ffffff", "#e5e7eb", "#ef4444", "#111111", "dots", "box", "eq=contrast=1.15", "comic book panel, halftone dots, manga ink, bold outlines"),
    _s("العروض الهندسية المعمارية (Architectural Blueprint)", "#0b3a6e", "#0a2a52", "#93c5fd", "#ffffff", "grid", "plain", "", "architectural blueprint, technical drawing, white lines on blue"),
    _s("تصميم الطباشير والسبورة (Whiteboard Chalk)", "#1f3d2b", "#14532d", "#fef08a", "#ffffff", "noise", "shadow", "", "chalk drawing on green blackboard, hand drawn doodles"),
    _s("أسلوب الجرائد الورقية (Vintage Newspaper)", "#d6cfc2", "#b8ae9a", "#111111", "#111111", "paper", "plain", "hue=s=0", "vintage newspaper print, halftone black and white photo"),
    _s("النمط الرياضي الحماسي (Sports/Gym Kinetic)", "#111827", "#dc2626", "#fde047", "#ffffff", "stripes", "outline", "eq=contrast=1.15:saturation=1.3", "intense sports action, kinetic energy, gym, dramatic"),
    _s("الخيال العلمي والفضاء (Sci-Fi Deep Space)", "#020617", "#1e1b4b", "#a78bfa", "#f1f5f9", "stars", "glow", "", "deep space nebula, sci-fi spaceship, stars, cosmic"),
    _s("عالم الألعاب والـ Pixel Art (8-Bit Gaming)", "#1a1033", "#3b0764", "#4ade80", "#ffffff", "blocks", "box", "", "8-bit pixel art video game scene, retro arcade"),
    _s("نمط المجلات الفاخرة (Luxury/Fashion Editorial)", "#0a0a0a", "#1c1917", "#d4af37", "#f5f5f4", "lines", "plain", "vignette=PI/4", "luxury fashion editorial, black and gold, elegant"),
    _s("السفر والمغامرات (Travel Vlog / Polaroid)", "#fef3c7", "#fdba74", "#7c2d12", "#422006", "paper", "shadow", "eq=saturation=1.15", "travel adventure polaroid photo, warm sunlight, landscape"),
    _s("المظهر الورقي المقطع (Paper Collage/Stop-Motion)", "#fecaca", "#fde68a", "#b91c1c", "#1f2937", "blocks", "box", "", "paper cut collage, stop motion, layered colored paper"),
    _s("الإعلانات السينمائية واللوحات الضخمة (Epic Cinematic Trailer)", "#020617", "#7f1d1d", "#fbbf24", "#ffffff", "rays", "shadow", "eq=contrast=1.2:saturation=0.9,vignette=PI/4", "epic cinematic movie trailer, dramatic lighting, grand scale"),
    _s("الأسلوب الزيتي الفني (Oil Painting/Artistic)", "#3f2a1d", "#9a3412", "#fcd34d", "#fff7ed", "waves", "shadow", "", "oil painting on canvas, thick brush strokes, rich colors"),
    _s("الرسوم المائية الهادئة (Watercolor Splatter)", "#dbeafe", "#fbcfe8", "#1e3a8a", "#1e3a8a", "blocks", "plain", "", "soft watercolor painting, paint splatter, pastel"),
    _s("نمط شركات المليار (Corporate Tech Clean)", "#0f2a4a", "#1d4ed8", "#93c5fd", "#ffffff", "lines", "shadow", "", "clean corporate technology, modern office, blue palette"),
    _s("المونتاج السيكيدلي السريالي (Psychedelic/Surreal)", "#7e22ce", "#f97316", "#22d3ee", "#ffffff", "rings", "outline", "eq=saturation=1.6", "psychedelic surreal art, kaleidoscope, vivid swirling colors"),
    _s("المحاكاة الواقعية وعناصر VFX (Photorealistic VFX)", "#0b0b0f", "#27272a", "#f97316", "#fafafa", "rays", "shadow", "vignette=PI/4", "photorealistic VFX, volumetric light, sparks, cinematic"),
    _s("الرسوم الطبية والبيولوجية (Medical/Sci-Explainer)", "#ecfeff", "#a5f3fc", "#0e7490", "#134e4a", "rings", "plain", "", "medical illustration, biology cells, clean scientific diagram"),
    _s("نمط الطبخ وصناعة الأطعمة (Cinematic Food/ASMR)", "#451a03", "#b45309", "#fde68a", "#fffbeb", "dots", "shadow", "eq=saturation=1.3", "cinematic food photography, macro, steam, warm light"),
    _s("اللمسة الطينية Claymation (Clay/Plasticine)", "#fde68a", "#fb7185", "#7c2d12", "#ffffff", "blocks", "outline", "", "claymation plasticine characters, stop motion, soft clay texture"),
    _s("أسلوب Vector الكرتوني المسطح (Flat Vector Animation)", "#2563eb", "#7c3aed", "#fde047", "#ffffff", "blocks", "shadow", "", "flat vector illustration, geometric shapes, bold colors"),
    _s("النمط الكولونيالي العتيق (Retro 80s/90s VHS)", "#1e1b4b", "#be185d", "#22d3ee", "#ffffff", "stripes", "glow", "noise=alls=20:allf=t,eq=saturation=1.4", "retro 80s 90s VHS aesthetic, synthwave, scanlines"),
]

STYLES = {s["name"]: s for s in STYLES_LIST}

PROPS = {
    "وثائقي": dict(fps=24, zoom=1.06, fade=0.5, text_fade=0.6, slide=0, rate="-5%", fx="eq=saturation=0.9",
                   look="calm documentary photography, balanced colors", min_scene=4.0),
    "سينمائي": dict(fps=30, zoom=1.15, fade=0.4, text_fade=0.5, slide=40, rate="+0%", fx="vignette=PI/5",
                    look="cinematic lighting, shallow depth of field, dramatic", min_scene=4.0),
    "ديناميكي": dict(fps=60, zoom=1.30, fade=0.12, text_fade=0.15, slide=90, rate="+12%", fx="eq=contrast=1.1:saturation=1.3",
                     look="high energy, dynamic motion, bold", min_scene=3.0),
}


def get_style(name: str) -> dict:
    if name in STYLES:
        return STYLES[name]
    m = re.search(r"\(([^)]+)\)", name or "")
    if m:
        for s in STYLES_LIST:
            if m.group(1) in s["name"]:
                return s
    return STYLES_LIST[0]


def get_prop(name: str) -> dict:
    return PROPS.get(name, PROPS["سينمائي"])
