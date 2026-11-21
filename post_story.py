#!/usr/bin/env python3
"""Sıradaki medyayı Instagram hikâyesi olarak paylaşır (resmî Graph API).

Ortam değişkenleri:
  IG_USER_ID   Instagram işletme hesabının ID'si
  IG_TOKEN     Süresiz system-user erişim anahtarı
  MEDIA_BASE   Medyanın herkese açık adresi (örn. https://kullanici.github.io/repo/media)
  FORCE=1      Saat kontrolünü atla, hemen paylaş (test için)
  DRY_RUN=1    Instagram'a göndermeden ne yapacağını yazdır
"""
import json
import os
import random
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
MEDIA_DIR = ROOT / "media"
CONFIG = json.loads((ROOT / "config.json").read_text())
STATE_FILE = ROOT / "state.json"
# Instagram-login anahtarları "IG" ile başlar ve graph.instagram.com'da çalışır; diğerleri graph.facebook.com
_HOST = "graph.instagram.com" if os.environ.get("IG_TOKEN", "").startswith("IG") else "graph.facebook.com"
GRAPH = f"https://{_HOST}/{CONFIG.get('graph_version', 'v24.0')}"
IMAGE_EXT = {".jpg", ".jpeg"}
VIDEO_EXT = {".mp4", ".mov"}


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"last_slot": None, "log": []}


def pick(files, log, today):
    """Rastgele seçim: bugün paylaşılmamış tasarımlar arasından, en uzun süredir paylaşılmayanlara öncelik."""
    last_seen = {}
    for entry in log:  # log: "2026-11-18T10:07+02:00 dosya.jpg", eskiden yeniye
        ts, name = entry.split(" ", 1)
        last_seen[name] = ts
    candidates = [f for f in files if not last_seen.get(f, "").startswith(today)]
    if not candidates:  # tasarım sayısı günlük paylaşımdan azsa: sadece bir öncekini tekrarlama
        prev = log[-1].split(" ", 1)[1] if log else None
        candidates = [f for f in files if f != prev] or files
    candidates.sort(key=lambda f: last_seen.get(f, ""))  # hiç paylaşılmayanlar en başta
    pool = candidates[:max(1, (len(candidates) + 1) // 2)]  # en uzun süredir paylaşılmayan yarı
    return random.choice(pool)


def current_slot(now):
    """Açık saatler içindeysek o anki paylaşım diliminin başlangıcını döndürür, değilse None."""
    oh, om = map(int, CONFIG["open"].split(":"))
    ch, cm = map(int, CONFIG["close"].split(":"))
    interval = timedelta(minutes=int(CONFIG["interval_minutes"]))
    for day_offset in (0, -1):  # gece yarısını geçen kapanışlar için dünkü açılışı da kontrol et
        open_dt = (now + timedelta(days=day_offset)).replace(hour=oh, minute=om, second=0, microsecond=0)
        close_dt = open_dt.replace(hour=ch, minute=cm)
        if close_dt <= open_dt:
            close_dt += timedelta(days=1)
        if open_dt.weekday() in CONFIG.get("closed_days", []):  # 0=Pazartesi ... 6=Pazar
            continue
        if open_dt <= now < close_dt:
            return open_dt + ((now - open_dt) // interval) * interval
    return None


def api(method, path, params):
    data = urllib.parse.urlencode(params).encode()
    url = f"{GRAPH}/{path}"
    if method == "GET":
        req = urllib.request.Request(f"{url}?{data.decode()}")
    else:
        req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        sys.exit(f"API hatası {e.code}: {e.read().decode()}")


def publish(filename):
    token = os.environ["IG_TOKEN"]
    ig_id = os.environ["IG_USER_ID"]
    url = f"{os.environ['MEDIA_BASE'].rstrip('/')}/{urllib.parse.quote(filename)}"
    is_video = Path(filename).suffix.lower() in VIDEO_EXT
    params = {"media_type": "STORIES", "access_token": token,
              ("video_url" if is_video else "image_url"): url}
    container = api("POST", f"{ig_id}/media", params)["id"]
    for _ in range(20):  # en fazla ~5 dk işlenmesini bekle; Meta'ya az istek için 15 sn arayla sor
        time.sleep(15)
        status = api("GET", container, {"fields": "status_code", "access_token": token}).get("status_code")
        if status == "FINISHED":
            break
        if status in ("ERROR", "EXPIRED"):
            sys.exit(f"Medya işlenemedi ({status}): {filename}")
    else:
        sys.exit(f"Medya zamanında işlenmedi: {filename}")
    return api("POST", f"{ig_id}/media_publish", {"creation_id": container, "access_token": token})["id"]


def main():
    tz = ZoneInfo(CONFIG.get("timezone", "Europe/Sofia"))
    now = datetime.now(tz)
    force = os.environ.get("FORCE") == "1"
    dry = os.environ.get("DRY_RUN") == "1"
    state = load_state()

    slot = current_slot(now)
    slot_key = slot.isoformat(timespec="minutes") if slot else None
    if not force:
        if slot is None:
            print(f"{now:%H:%M} kapalı saat, paylaşım yok.")
            return
        if state.get("last_slot") == slot_key:
            print(f"{slot_key} dilimi zaten paylaşıldı.")
            return

    files = sorted(p.name for p in MEDIA_DIR.iterdir()
                   if p.suffix.lower() in IMAGE_EXT | VIDEO_EXT)
    if not files:
        sys.exit("media/ klasöründe paylaşılacak dosya yok.")
    secim = os.environ.get("DOSYA", "").strip()  # test: tam dosya adı ya da önek (örn. gta6_)
    if secim:
        files = [f for f in files if f == secim or f.startswith(secim)]
        if not files:
            sys.exit(f"'{secim}' ile eşleşen medya yok.")
    log = state.get("log", [])
    filename = pick(files, log, now.date().isoformat())

    if dry:
        print(f"[DRY] {now:%Y-%m-%d %H:%M} -> {filename} ({len(files)} tasarım, dilim {slot_key})")
        return
    media_id = publish(filename)
    print(f"Paylaşıldı: {filename} (media id {media_id})")
    if slot_key:
        state["last_slot"] = slot_key
    state["log"] = (log + [f"{now.isoformat(timespec='minutes')} {filename}"])[-500:]
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
