import asyncio
import json
import urllib.error
import urllib.request


def _request(method, url, headers, body, timeout):
    headers = dict(headers or {})
    headers.setdefault("User-Agent", "StudioAIPro/1.0")
    data = None
    if body is not None:
        if isinstance(body, (bytes, bytearray)):
            data = bytes(body)
        else:
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
            headers.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:   # لا إنترنت / مهلة -> status 0 بدل انهيار الإنتاج
        return 0, str(e).encode("utf-8", "ignore")


async def request(method, url, headers=None, body=None, timeout=60):
    return await asyncio.to_thread(_request, method, url, headers, body, timeout)


async def request_json(method, url, headers=None, body=None, timeout=60):
    status, raw = await request(method, url, headers, body, timeout)
    try:
        return status, json.loads(raw.decode("utf-8"))
    except Exception:
        return status, {"raw": raw[:300].decode("utf-8", "ignore")}
