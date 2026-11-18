#!/bin/zsh
# Çift tıkla: otomatik hikâye paylaşımını AÇ / KAPAT.
R=canerbayramoglu/instagram-hikaye
DURUM=$(gh variable get PAYLASIM --repo $R 2>/dev/null)
if [[ "$DURUM" == "acik" ]]; then
  echo "Otomatik paylaşım şu an: AÇIK"
  echo "KAPATMAK için Enter'a basın (vazgeçmek için pencereyi kapatın)."
  read
  gh variable set PAYLASIM --body kapali --repo $R && echo "Otomatik paylaşım KAPATILDI. Bir sonraki saatten itibaren paylaşım yapılmaz."
else
  echo "Otomatik paylaşım şu an: KAPALI"
  echo "AÇMAK için Enter'a basın (vazgeçmek için pencereyi kapatın)."
  read
  gh variable set PAYLASIM --body acik --repo $R && gh workflow enable hikaye.yml --repo $R 2>/dev/null
  echo "Otomatik paylaşım AÇILDI. Açık saatlerde her saat başını 7 geçe paylaşım yapılır."
fi
echo "Kapatmak için bir tuşa basın."
read -k1
