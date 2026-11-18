#!/usr/bin/env python3
"""Tasarımlar/ ve Müzikler/ klasörlerini Instagram hikâye biçimine çevirip media/ ile eşitler.

- Tasarımlar/ : oyun klasörleri (örn. Tasarımlar/FC27/) içinde görseller (jpg/png/webp/heic) ve videolar
                (mp4/mov/m4v). Adı "_" ile başlayan klasör (örn. _FC27) paylaşıma dahil edilmez.
- Müzikler/   : mp3/m4a/wav/aac. Boşsa görseller sessiz JPG olarak paylaşılır.
Müzik varsa her tasarım, müzikler arasında dengeli ve rastgele dağıtılarak videoya çevrilir.
Müzik eklenince/silinince sadece dengeyi sağlamaya yetecek kadar tasarım yeniden üretilir.
Klasörden silinen tasarım media/'dan da silinir.

Kullanım: python3 hazirla.py
"""
import json
import random
import re
import subprocess
import unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "media"
MANIFEST = OUT / "eslesme.json"
CONFIG = json.loads((ROOT / "config.json").read_text())
SURE = int(CONFIG.get("story_seconds", 15))
IMG = {".jpg", ".jpeg", ".png", ".webp", ".heic"}
VID = {".mp4", ".mov", ".m4v"}
AUD = {".mp3", ".m4a", ".wav", ".aac"}
# 9:16 kanvas: tasarım ortada, boşluklar tasarımın bulanık hâliyle dolar
FIT = ("split[a][b];[a]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=40:2[bg];"
       "[b]scale=1080:1920:force_original_aspect_ratio=decrease[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1,format=yuv420p")
VIDEO = ["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-maxrate", "8M", "-bufsize", "16M",
         "-pix_fmt", "yuv420p", "-r", "30", "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2",
         "-movflags", "+faststart"]


def slug(name):
    s = unicodedata.normalize("NFKD", name.replace("ı", "i").replace("İ", "I"))
    s = s.encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_").lower()


def klasor(ad):
    """Türkçe karakter/Unicode farkından bağımsız klasör bul; yoksa oluştur."""
    for p in ROOT.iterdir():
        if p.is_dir() and slug(p.name) == slug(ad):
            return p
    p = ROOT / ad
    p.mkdir()
    return p


def dosyalar(d, uzantilar, alt_klasorler=False):
    adaylar = d.rglob("*") if alt_klasorler else d.iterdir()
    return sorted(p for p in adaylar if p.is_file() and p.suffix.lower() in uzantilar
                  and not any(x.startswith((".", "_")) for x in p.relative_to(d).parts))


def ff(*args):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args], check=True, timeout=600)


def saglam(p, tur):
    """Dosyanın ilk karesi/ilk saniyesi gerçekten çözülebiliyor mu? (tur: v=görüntü, a=ses)"""
    secim = ["-map", "0:v:0", "-frames:v", "1"] if tur == "v" else ["-map", "0:a:0", "-t", "1"]
    try:
        r = subprocess.run(["ffmpeg", "-v", "error", "-xerror", "-i", str(p), *secim, "-f", "null", "-"],
                           capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        return False
    return r.returncode == 0 and not r.stderr.strip()


def main():
    TAS = klasor("Tasarımlar")
    tasarimlar = dosyalar(TAS, IMG | VID, alt_klasorler=True)
    muzikler = {m.name: m for m in dosyalar(klasor("Müzikler"), AUD)}
    for m in [m for m in muzikler.values() if not saglam(m, "a")]:
        print(f"! Müzik açılamadı, kullanılmayacak: {m.name}")
        del muzikler[m.name]
    OUT.mkdir(exist_ok=True)
    eski = json.loads(MANIFEST.read_text()).get("dosyalar", {}) if MANIFEST.exists() else {}

    # Her tasarıma çakışmasız bir çıktı adı ver (a.png ve a.jpg -> a.mp4, a_2.mp4)
    plan, adlar = [], set()
    for src in tasarimlar:
        ext = "mp4" if muzikler or src.suffix.lower() in VID else "jpg"
        rel = src.relative_to(TAS)
        kok = "_".join(filter(None, [slug(x) for x in rel.parent.parts] + [slug(src.stem) or "tasarim"]))
        hedef, i = f"{kok}.{ext}", 2
        while hedef in adlar:
            hedef, i = f"{kok}_{i}.{ext}", i + 1
        adlar.add(hedef)
        plan.append((src, hedef, str(rel)))

    # Geçerli eşleşmeleri koru; sadece kaynağı/müziği değişenleri ve dengeyi bozanları yeniden üret.
    # Böylece müzik eklemek/silmek sadece gerektiği kadar tasarımı etkiler.
    tavan = -(-len(plan) // len(muzikler)) if muzikler else 0
    sayac = Counter({m: 0 for m in muzikler})
    yeni, isler = {}, []
    random.shuffle(plan)
    for src, hedef, rel in plan:
        k = eski.get(hedef) or {}
        m = k.get("muzik")
        gecerli = ((OUT / hedef).exists() and k.get("kaynak") == rel and k.get("mtime") == src.stat().st_mtime
                   and (m is None if not muzikler else
                        m in muzikler and k.get("muzik_mtime") in (None, muzikler[m].stat().st_mtime) and sayac[m] < tavan))
        if gecerli:
            yeni[hedef] = k
            if m:
                k["muzik_mtime"] = muzikler[m].stat().st_mtime  # eski kayıtları tamamla
                sayac[m] += 1
        else:
            isler.append((src, hedef, rel))

    hatalar = 0
    for src, hedef, rel in isler:
        muzik = None
        if muzikler:  # en az kullanılan müziklerden rastgele biri
            az = min(sayac.values())
            muzik = muzikler[random.choice([m for m in muzikler if sayac[m] == az])]
        dst = OUT / hedef
        if not saglam(src, "v"):
            hatalar += 1
            print(f"! Tasarım açılamadı, atlandı: {rel}")
            continue
        try:
            if src.suffix.lower() in IMG and not muzik:
                ff("-i", str(src), "-vf", FIT, "-q:v", "2", "-frames:v", "1", str(dst))
            elif src.suffix.lower() in IMG:
                ff("-loop", "1", "-framerate", "30", "-i", str(src), "-stream_loop", "-1", "-i", str(muzik),
                   "-t", str(SURE), "-vf", FIT, "-af", f"afade=t=out:st={SURE - 1}:d=1",
                   "-tune", "stillimage", *VIDEO, str(dst))
            else:
                ses = ["-stream_loop", "-1", "-i", str(muzik), "-map", "0:v", "-map", "1:a", "-shortest"] if muzik else []
                ff("-i", str(src), *ses, "-t", "59", "-vf", FIT, *VIDEO, str(dst))
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            dst.unlink(missing_ok=True)
            hatalar += 1
            print(f"! {rel}" + (f" + {muzik.name}" if muzik else "") + " işlenemedi, atlandı (dosya bozuk olabilir).")
            continue
        if muzik:
            sayac[muzik.name] += 1
        yeni[hedef] = {"kaynak": rel, "mtime": src.stat().st_mtime,
                       "muzik": muzik.name if muzik else None,
                       "muzik_mtime": muzik.stat().st_mtime if muzik else None}
        print(f"+ {rel} -> media/{hedef}" + (f"  ♪ {muzik.name}" if muzik else ""))

    for old in OUT.iterdir():
        if old.suffix.lower() in {".jpg", ".mp4"} and old.name not in yeni:
            old.unlink()
            print(f"- media/{old.name} (artık kullanılmıyor, silindi)")
    MANIFEST.write_text(json.dumps({"dosyalar": dict(sorted(yeni.items()))}, ensure_ascii=False, indent=1) + "\n")
    print(f"Hazır: {len(yeni)} tasarım, {len(muzikler)} müzik." + (f" {hatalar} dosya atlandı." if hatalar else ""))


if __name__ == "__main__":
    main()
