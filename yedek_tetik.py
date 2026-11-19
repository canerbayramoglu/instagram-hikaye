#!/opt/homebrew/bin/python3
"""Yedek tetikleyici (Mac'te launchd ile 5 dakikada bir çalışır).

GitHub'ın kendi zamanlayıcısı tetikleri sık atlıyor. Bu script, anahtar açıkken ve kafe açık saatteyken
o saat dilimi henüz paylaşılmadıysa GitHub'daki paylaşım işini başlatır. Asıl karar yine GitHub'daki
post_story.py'de: aynı dilim iki kez paylaşılmaz.
"""
import base64
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from post_story import CONFIG, current_slot  # noqa: E402

REPO = "canerbayramoglu/instagram-hikaye"
GH = "/opt/homebrew/bin/gh"


def gh(*a):
    r = subprocess.run([GH, *a, "-R", REPO] if a[0] != "api" else [GH, *a], capture_output=True, text=True, timeout=60)
    if r.returncode:
        sys.exit(f"gh hata: {' '.join(a)}: {r.stderr.strip()}")
    return r.stdout.strip()


def main():
    now = datetime.now(ZoneInfo(CONFIG.get("timezone", "Europe/Sofia")))
    slot = current_slot(now)
    if slot is None:
        return
    if gh("variable", "get", "PAYLASIM") not in ("acik", "açık"):
        return
    key = slot.isoformat(timespec="minutes")
    state = json.loads(base64.b64decode(json.loads(gh("api", f"repos/{REPO}/contents/state.json"))["content"]))
    if state.get("last_slot") == key:
        return
    calisan = gh("run", "list", "--workflow", "hikaye.yml", "-L", "10", "--json", "status",
                 "-q", '[.[] | select(.status != "completed")] | length')
    if calisan != "0":
        return
    gh("workflow", "run", "hikaye.yml")
    print(f"{now:%Y-%m-%d %H:%M} {key} dilimi için paylaşım başlatıldı", flush=True)


if __name__ == "__main__":
    main()
