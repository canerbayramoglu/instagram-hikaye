#!/bin/zsh
# Çift tıkla: Tasarımlar klasöründeki değişiklikleri hazırlar ve yayına gönderir.
cd "$(dirname "$0")" || exit 1
echo "Tasarımlar ve müzikler hazırlanıyor (müzik değiştiyse birkaç dakika sürebilir)..."
python3 hazirla.py || { echo "Hazırlama başarısız."; read -k1; exit 1; }
git pull -q --rebase
git add media
if git diff --cached --quiet; then
  echo "Değişiklik yok."
else
  git commit -q -m "Tasarımlar güncellendi" && git push -q && echo "Yayına gönderildi. Birkaç dakika içinde paylaşımlara dahil olur."
fi
echo "Kapatmak için bir tuşa basın."
read -k1
