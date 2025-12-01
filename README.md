# GPX_helper
This repo includes some script for utalizing GPX for content creation. 

python3 crop_gpx_by_video.py \
  ~/GoPro/GX010415.MP4 \
  /path/to/ride.gpx \
  -o /path/to/ride_cropped.gpx


Fixing the split video by GoPro (UTC)
exiftool -overwrite_original -P -api QuickTimeUTC=0 \
  -CreateDate="2025:11:29 18:42:49" \
  -ModifyDate="2025:11:29 18:42:49" \
  -MediaCreateDate="2025:11:29 18:42:49" \
  -MediaModifyDate="2025:11:29 18:42:49" \
  -TrackCreateDate="2025:11:29 18:42:49" \
  -TrackModifyDate="2025:11:29 18:42:49" \
  GX020427.MP4