import asyncio
import io
import shutil
import time
import uuid

from PIL import Image

from agents_crew import MasterDirectorAgent
from config import StudioConfig
from media import (darken_bottom, fetch_ai_image, fit_cover, make_background,
                   probe_duration, render_text_png, synth_voice)
from styles import get_prop, get_style


async def run_ffmpeg(*args):
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *args,
        stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE)
    _, err = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError("ffmpeg: " + err.decode("utf-8", "ignore")[-600:])


def _srt_time(t):
    h, m, s = int(t // 3600), int(t % 3600 // 60), t % 60
    return f"{h:02d}:{m:02d}:{int(s):02d},{int((s % 1) * 1000):03d}"


async def render_scene(i, bg, txt_png, audio, D, style, prop, out, work):
    W, H = StudioConfig.WIDTH, StudioConfig.HEIGHT
    fps, Z = prop["fps"], prop["zoom"]
    inc = (Z - 1) / max(1, D * fps)
    fx = ",".join(f for f in (style["fx"], prop["fx"]) if f)
    fx = ("," + fx) if fx else ""
    tf, fd = prop["text_fade"], prop["fade"]
    slide = prop["slide"]
    ystr = f"if(lt(t,{tf}),(1-t/{tf})*{slide},0)" if slide else "0"
    fc = (
        f"[0:v]zoompan=z='min(zoom+{inc:.7f},{Z})':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
        f":d=1:s={W}x{H}:fps={fps}{fx},format=yuv420p[bg];"
        f"[1:v]format=rgba,fade=t=in:st=0.15:d={tf}:alpha=1[tx];"
        f"[bg][tx]overlay=x=0:y='{ystr}',fade=t=in:st=0:d={fd},fade=t=out:st={D - fd:.3f}:d={fd},format=yuv420p[v];"
        f"[2:a]aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo,apad=whole_dur={D:.3f}[a]"
    )
    audio_in = ["-i", audio] if audio else ["-f", "lavfi", "-t", f"{D:.3f}", "-i", "anullsrc=r=44100:cl=stereo"]
    await run_ffmpeg(
        "-loop", "1", "-framerate", str(fps), "-t", f"{D:.3f}", "-i", str(bg),
        "-loop", "1", "-framerate", str(fps), "-t", f"{D:.3f}", "-i", str(txt_png),
        *audio_in, "-filter_complex", fc, "-map", "[v]", "-map", "[a]",
        "-t", f"{D:.3f}", "-r", str(fps), "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2", str(out))


def cleanup_old_outputs():
    cutoff = time.time() - StudioConfig.KEEP_OUTPUTS_HOURS * 3600
    for p in StudioConfig.OUTPUT_DIR.glob("*"):
        try:
            if p.stat().st_mtime < cutoff:
                p.unlink()
        except OSError:
            pass


async def produce_video(idea: str, style_name: str, prop_name: str, duration: int, progress, job_id=None):
    """progress: async callable(pct:int, message:str)."""
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg غير مثبت على السيرفر")
    style, prop = get_style(style_name), get_prop(prop_name)
    job_id = job_id or uuid.uuid4().hex[:10]
    work = StudioConfig.WORK_DIR / job_id
    work.mkdir(parents=True, exist_ok=True)
    StudioConfig.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    W, H = StudioConfig.WIDTH, StudioConfig.HEIGHT
    warnings = []
    try:
        await progress(5, f"🧠 المخرج يكتب السيناريو بنمط ({style['name']}) - {prop_name} {prop['fps']}fps ...")
        scenes, title, w = await MasterDirectorAgent().plan(idea, style, prop_name, duration)
        warnings += w
        n = len(scenes)

        ai_ok, ai_fail = 0, ""
        for i, sc in enumerate(scenes):
            await progress(10 + int(30 * i / n), f"🎨 توليد خلفية المشهد {i + 1}/{n} ...")
            img = None
            raw, why = await fetch_ai_image(f"{sc['visual_prompt']}, {style['prompt']}, {prop['look']}, no text, 16:9")
            if raw:
                try:
                    img = darken_bottom(fit_cover(Image.open(io.BytesIO(raw)).convert("RGB"), (W * 2, H * 2)))
                    ai_ok += 1
                except Exception as e:
                    why = f"صورة غير صالحة: {e}"
            if img is None:
                ai_fail = why
                img = make_background(style, i, (W, H)).resize((W * 2, H * 2), Image.LANCZOS)
            img.save(work / f"bg{i}.jpg", quality=92)
            render_text_png(sc["on_screen_text"], style, (W, H), str(work / f"tx{i}.png"))
        if ai_ok < n:
            warnings.append(f"خلفيات {n - ai_ok} من {n} مشاهد رُسمت محلياً حسب النمط ({ai_fail}).")

        durs, audios, tts_ok = [], [], 0
        for i, sc in enumerate(scenes):
            await progress(40 + int(20 * i / n), f"🎙️ تعليق صوتي للمشهد {i + 1}/{n} ...")
            ap = work / f"a{i}.mp3"
            if await synth_voice(sc["narration"], str(ap), prop["rate"]):
                tts_ok += 1
                audios.append(str(ap))
                d = probe_duration(str(ap)) + 0.5
            else:
                audios.append(None)
                d = len(sc["narration"].split()) / 2.3 + 0.5
            durs.append(min(25.0, max(prop["min_scene"], d)))
        if tts_ok < n:
            warnings.append("التعليق الصوتي غير متاح (ثبّت edge-tts وتأكد من الإنترنت) - الفيديو صامت في بعض/كل المشاهد.")

        parts = []
        for i in range(n):
            await progress(60 + int(32 * i / n), f"🎞️ رندر المشهد {i + 1}/{n} عبر ffmpeg ...")
            out = work / f"s{i}.mp4"
            await render_scene(i, work / f"bg{i}.jpg", work / f"tx{i}.png", audios[i], durs[i], style, prop, out, work)
            parts.append(out)

        await progress(94, "🔗 دمج المشاهد وتصدير MP4 ...")
        (work / "list.txt").write_text("".join(f"file '{p.name}'\n" for p in parts))
        name = f"video_{job_id}"
        final = StudioConfig.OUTPUT_DIR / f"{name}.mp4"
        await run_ffmpeg("-f", "concat", "-safe", "0", "-i", str(work / "list.txt"), "-c", "copy",
                         "-movflags", "+faststart", str(final))
        t, srt = 0.0, []
        for i, (sc, d) in enumerate(zip(scenes, durs)):
            srt.append(f"{i + 1}\n{_srt_time(t)} --> {_srt_time(t + d)}\n{sc['on_screen_text']}\n")
            t += d
        (StudioConfig.OUTPUT_DIR / f"{name}.srt").write_text("\n".join(srt), encoding="utf-8")
        cleanup_old_outputs()
        await progress(100, "✅ اكتمل الفيديو")
        return {"video_path": str(final), "video_file": final.name, "srt_file": f"{name}.srt",
                "title": title, "scenes": n, "duration": round(sum(durs), 1), "fps": prop["fps"],
                "ai_images": ai_ok, "voiced_scenes": tts_ok, "warnings": warnings}
    finally:
        shutil.rmtree(work, ignore_errors=True)
