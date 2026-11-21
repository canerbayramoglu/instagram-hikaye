#!/usr/bin/env python3
"""Paylaşım durunca ve düzelince Telegram'a tek mesaj atar (her başarısız denemede değil).

GitHub Actions'ta "Paylaş" adımından sonra çalışır. Ortam: SONUC (success/failure), TG_TOKEN, TG_CHAT,
GH_TOKEN (önceki çalışmanın sonucunu okumak için). Paylaş adımının çıktısı cikti.txt'de.
"""
import json
import os
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def onceki_sonuc():
    """Bundan önceki, gerçekten çalışmış (atlanmamış) son çalışmanın sonucu."""
    r = subprocess.run(["gh", "run", "list", "--workflow", "hikaye.yml", "--status", "completed", "-L", "20",
                        "--json", "conclusion,databaseId"], capture_output=True, text=True, cwd=ROOT)
    simdiki = os.environ.get("GITHUB_RUN_ID")
    for k in json.loads(r.stdout or "[]"):
        if str(k["databaseId"]) != simdiki and k["conclusion"] in ("success", "failure"):
            return k["conclusion"]
    return "success"


def gonder(metin):
    data = urllib.parse.urlencode({"chat_id": os.environ["TG_CHAT"], "text": metin,
                                   "disable_web_page_preview": "true"}).encode()
    urllib.request.urlopen(f"https://api.telegram.org/bot{os.environ['TG_TOKEN']}/sendMessage", data, timeout=20)


def main():
    if not os.environ.get("TG_TOKEN") or not os.environ.get("TG_CHAT"):
        return
    sonuc = os.environ.get("SONUC")
    onceki = onceki_sonuc()
    cikti = (ROOT / "cikti.txt").read_text(errors="ignore").strip().splitlines() if (ROOT / "cikti.txt").exists() else []
    son = cikti[-1] if cikti else "(çıktı yok)"
    adres = f"{os.environ.get('GITHUB_SERVER_URL')}/{os.environ.get('GITHUB_REPOSITORY')}/actions/runs/{os.environ.get('GITHUB_RUN_ID')}"
    if sonuc == "failure" and onceki != "failure":
        gonder(f"⚠️ Elite Game hikâye paylaşımı DURDU\n\n{son[:500]}\n\nDüzelince ayrıca haber vereceğim.\n{adres}")
    elif sonuc == "success" and onceki == "failure":
        paylasilan = next((s for s in cikti if s.startswith("Paylaşıldı:")), "")
        gonder("✅ Elite Game hikâye paylaşımı yeniden çalışıyor." + (f"\n{paylasilan}" if paylasilan else ""))


if __name__ == "__main__":
    main()
