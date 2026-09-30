#!/bin/bash
# Watch photos-drop/ and publish automatically whenever Jason adds or replaces a photo.
cd "$(dirname "$0")/.."
sig() { find photos-drop -maxdepth 1 -type f \( -iname '*.png' -o -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.webp' -o -iname '*.heic' -o -iname '*.tif' -o -iname '*.tiff' -o -name '_skip.txt' \) -exec stat -f '%N %z %m %i' {} + 2>/dev/null | sort | md5; }
echo "$(date '+%H:%M:%S') watching photos-drop/"
last=""
while true; do
  now=$(sig)
  if [ "$now" != "$last" ]; then
    sleep 6                                  # let Finder finish copying
    [ "$(sig)" != "$now" ] && continue
    last=$now
    dev/publish_photos.sh
  fi
  sleep 15
done
