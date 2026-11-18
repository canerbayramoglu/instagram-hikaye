#!/usr/bin/env python3
"""Hikâyeler için enerjik müzik üretir (KodAdamYap müzik motorunu değiştirmeden kullanır).

Her parça kısa bir girişle başlar, sonra tüm katmanlarla "drop"a geçer.

Kullanım (KodAdamYap venv'iyle):
  ~/YouTubeAraclari/KodAdamYap/motor/.venv/bin/python muzik_uret.py              # 5 tarz, Müzikler/
  ~/YouTubeAraclari/KodAdamYap/motor/.venv/bin/python muzik_uret.py --varyasyon 3 # her tarzdan 3 farklı
"""
import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(Path.home() / "YouTubeAraclari/KodAdamYap/motor/studio/audio"))
import music  # noqa: E402
from dsp import write_wav  # noqa: E402

# Katman eşikleri: girişte (yoğunluk 0.5) sadece eşiği <= 0.5 olanlar çalar, drop'ta (1.0) hepsi
TARZLAR = {
    "arena":        dict(key="E", minor=True, prog=["i", "bVI", "bIII", "bVII"], bpm=140, bars=1, bright=0.7,
                         layers=dict(pad=0, sub=0, pulse=0, hat=0.4, arp=0.6, kick=0.6, snare=0.7, brass=0.8)),
    "neon_rush":    dict(key="F#", minor=True, prog=["i", "bVII", "bVI", "bVII"], bpm=128, bars=1, bright=0.8,
                         layers=dict(pad=0, sub=0, pluck=0, arp=0.4, bass=0.6, kick=0.6, clap=0.7, hat=0.6)),
    "boss_fight":   dict(key="C", minor=True, prog=["i", "bII", "i", "bVI"], bpm=150, bars=1, bright=0.6,
                         layers=dict(sub=0, drone=0, pulse=0, tick=0.4, kick=0.6, snare=0.6, hat=0.7, brass=0.7)),
    "victory_lap":  dict(key="A", minor=False, prog=["I", "V", "vi", "IV"], bpm=124, bars=1, bright=0.75,
                         layers=dict(pad=0, sub=0, pluck=0, bell=0.4, arp=0.6, bass=0.6, kick=0.6, clap=0.7, hat=0.7)),
    "street_party": dict(key="G", minor=True, prog=["i", "iv", "bVII", "bIII"], bpm=118, bars=1, bright=0.7,
                         layers=dict(sub=0, pluck=0, piano=0.4, bass=0.6, kick=0.6, clap=0.6, hat=0.6, arp=0.8)),
}
music.MOODS.update(TARZLAR)


def uret(tarz, sure, seed, hedef):
    giris = min(4.0, sure / 3)
    plan = [{"start": 0, "end": giris, "mood": tarz, "intensity": 0.5},
            {"start": giris, "end": sure, "mood": tarz, "intensity": 1.0}]
    wav = hedef.with_suffix(".wav")
    write_wav(str(wav), music.render_score(plan, sure, seed))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav), "-af",
                    f"loudnorm=I=-14:TP=-1,afade=t=out:st={sure - 1}:d=1", "-t", str(sure),
                    "-b:a", "192k", str(hedef)], check=True)
    wav.unlink()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--sure", type=float, default=15)
    p.add_argument("--varyasyon", type=int, default=1)
    p.add_argument("--klasor", default=str(ROOT / "Müzikler"))
    a = p.parse_args()
    out = Path(a.klasor)
    out.mkdir(exist_ok=True)
    for tarz in TARZLAR:
        for v in range(1, a.varyasyon + 1):
            hedef = out / (f"{tarz}.mp3" if a.varyasyon == 1 else f"{tarz}_{v}.mp3")
            uret(tarz, a.sure, seed=v * 17, hedef=hedef)
            print(f"+ {hedef.name}")


if __name__ == "__main__":
    main()
