#!/usr/bin/env python3
"""Hikâyeler için enerjik müzik üretir (KodAdamYap müzik motorunu değiştirmeden kullanır).

Her parça kısa bir girişle başlar, sonra tüm katmanlarla "drop"a geçer.

Kullanım (KodAdamYap venv'iyle):
  ~/YouTubeAraclari/KodAdamYap/motor/.venv/bin/python muzik_uret.py                # FC27 seti -> Muzik_Deneme/
  ~/YouTubeAraclari/KodAdamYap/motor/.venv/bin/python muzik_uret.py --varyasyon 3   # her tarzdan 3 farklı
  ~/YouTubeAraclari/KodAdamYap/motor/.venv/bin/python muzik_uret.py --set genel     # ilk 5 genel tarz
Beğendiklerinizi Muzik_Deneme/'den Müzikler/'e taşıyınca hikâyelerde kullanılır.
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
# FC27 rekabet seti: stadyum, kapışma, kazanma hırsı
TARZLAR.update({
    "derbi":         dict(key="D", minor=True, prog=["i", "bVI", "bVII", "i"], bpm=132, bars=1, bright=0.7,
                          layers=dict(pad=0, sub=0, brass=0, hat=0.4, kick=0.6, snare=0.6, clap=0.7, arp=0.8)),
    "son_dakika":    dict(key="C#", minor=True, prog=["i", "i", "bVI", "V"], bpm=150, bars=1, bright=0.6,
                          layers=dict(sub=0, pulse=0, tick=0, drone=0.4, kick=0.6, snare=0.6, hat=0.6, brass=0.8)),
    "kupa_finali":   dict(key="Bb", minor=False, prog=["I", "V", "vi", "IV"], bpm=128, bars=1, bright=0.75,
                          layers=dict(pad=0, sub=0, brass=0, arp=0.4, kick=0.6, clap=0.6, hat=0.6, bell=0.8)),
    "rovans":        dict(key="E", minor=True, prog=["i", "bII", "i", "bVII"], bpm=140, bars=1, bright=0.55,
                          layers=dict(sub=0, drone=0, pulse=0, kick=0.6, snare=0.6, hat=0.7, brass=0.6)),
    "gol_patlamasi": dict(key="F", minor=True, prog=["i", "bVI", "bIII", "bVII"], bpm=128, bars=1, bright=0.85,
                          layers=dict(sub=0, pluck=0, arp=0.4, pad=0.6, bass=0.6, kick=0.6, clap=0.6, hat=0.6, brass=0.8)),
})
# GTA VI seti: fragmanlardaki 80'ler synth-pop / synthwave havası (115-128 BPM)
TARZLAR.update({
    "vice_gece":       dict(key="A", minor=True, prog=["i", "bVI", "bIII", "bVII"], bpm=118, bars=1, bright=0.7,
                            layers=dict(pad=0, sub=0, arp=0, bass=0.6, kick=0.6, snare=0.6, hat=0.7)),
    "okyanus_bulvari": dict(key="D", minor=False, prog=["I", "vi", "IV", "V"], bpm=112, bars=1, bright=0.65,
                            layers=dict(pad=0, sub=0, pluck=0, bell=0.4, bass=0.6, kick=0.6, clap=0.6, hat=0.7)),
    "leonida_parti":   dict(key="F#", minor=True, prog=["i", "bVII", "bVI", "bVII"], bpm=124, bars=1, bright=0.8,
                            layers=dict(pad=0, pluck=0, arp=0.4, bass=0.6, kick=0.6, clap=0.6, hat=0.6)),
    "kovalamaca":      dict(key="C", minor=True, prog=["i", "bVI", "bVII", "V"], bpm=128, bars=1, bright=0.65,
                            layers=dict(sub=0, pulse=0, arp=0.4, kick=0.6, snare=0.6, hat=0.6, brass=0.7)),
    # Miami disko-funk: çan/piyano yok (ninni hissi veriyordu); dorian ton, her vuruşta davul, funk bas, brass
    "yat_partisi":     dict(key="G", minor=True, prog=["i", "IV", "i", "bVII"], bpm=122, bars=1, bright=0.8,
                            layers=dict(sub=0, pluck=0, bass=0, arp=0.4, kick=0.5, clap=0.6, hat=0.5, brass=0.7)),
})
SETLER = {"genel": ["arena", "neon_rush", "boss_fight", "victory_lap", "street_party"],
          "fc27": ["derbi", "son_dakika", "kupa_finali", "rovans", "gol_patlamasi"],
          "gta6": ["vice_gece", "okyanus_bulvari", "leonida_parti", "kovalamaca", "yat_partisi"]}
music.MOODS.update(TARZLAR)


NOTALAR = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]
# Varyasyon v: (ton kaydırma yarım ses, tempo farkı). v=1 orijinal parçanın aynısı.
VARYASYON = [(0, 0), (2, 4), (-2, -4), (3, 6), (-3, -3), (5, 2), (-5, 5), (1, -6)]
SES_LUFS = -12.5  # Instagram'ın -14'ünden ~1.5 dB yüksek, tepe -1 dBTP ile sınırlı


def uret(tarz, sure, seed, hedef, v=1):
    kay, dbpm = VARYASYON[(v - 1) % len(VARYASYON)]
    ad = tarz if v == 1 else f"{tarz}_v{v}"
    if v > 1:
        t = dict(TARZLAR[tarz])
        t["key"] = NOTALAR[(music.NOTE[t["key"]] + kay) % 12]
        t["bpm"] = t["bpm"] + dbpm
        music.MOODS[ad] = t
    giris = min(3.0, sure / 4)
    plan = [{"start": 0, "end": giris, "mood": ad, "intensity": 0.5},
            {"start": giris, "end": sure, "mood": ad, "intensity": 1.0}]
    wav = hedef.with_suffix(".wav")
    write_wav(str(wav), music.render_score(plan, sure, seed))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav), "-af",
                    f"loudnorm=I={SES_LUFS}:TP=-1,afade=t=out:st={sure - 1}:d=1", "-t", str(sure),
                    "-b:a", "192k", str(hedef)], check=True)
    wav.unlink()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--sure", type=float, default=15)
    p.add_argument("--varyasyon", type=int, default=1)
    p.add_argument("--set", default="fc27", choices=SETLER)
    p.add_argument("--tarz", help="sadece bu tarz(lar), virgülle: --tarz yat_partisi")
    p.add_argument("--klasor", default=str(ROOT / "Muzik_Deneme"))
    a = p.parse_args()
    out = Path(a.klasor)
    out.mkdir(parents=True, exist_ok=True)
    for tarz in (a.tarz.split(",") if a.tarz else SETLER[a.set]):
        for v in range(1, a.varyasyon + 1):
            hedef = out / (f"{tarz}.mp3" if a.varyasyon == 1 else f"{tarz}_{v}.mp3")
            uret(tarz, a.sure, seed=17 if v == 1 else v * 17, hedef=hedef, v=v)
            print(f"+ {hedef.name}")


if __name__ == "__main__":
    main()
