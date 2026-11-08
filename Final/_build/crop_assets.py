"""Crop real screenshots (Final/Evidence/screenshots) into slide assets. Needs Pillow.
Crops only: no pixels are edited, so every asset is still a true capture of the final build."""
from pathlib import Path
from PIL import Image

FINAL = Path(__file__).resolve().parents[1]
SRC = FINAL / 'Evidence' / 'screenshots'
OUT = FINAL / 'Presentation' / 'source' / 'assets'
OUT.mkdir(parents=True, exist_ok=True)
CROPS = {
    'hero': ('S02_browse.png', (100, 28, 1340, 560)),
    # student journey frames: all 1.3 : 1 so they fill 2.85 x 2.2 in frames without distortion
    'post': ('S04_post_form.png', (130, 40, 1016, 722)),
    'saved': ('S05_notice_created.png', (130, 138, 832, 678)),
    'search': ('S06_search_result.png', (130, 345, 780, 845)),
    'returned': ('S08_returned.png', (130, 138, 1000, 807)),
    'contact': ('S07_detail_contact.png', (1008, 184, 1310, 654)),
    'admin': ('S09_admin_panel.png', (100, 28, 1340, 700)),
    'analytics': ('S10_analytics.png', (150, 198, 1290, 848)),
    'remove': ('S12_remove_confirm.png', (130, 203, 1310, 478)),
    'locker_alert': ('S16_locker_alert.png', (195, 120, 1245, 440)),
    'locker_controls': ('S16_locker_alert.png', (195, 455, 1245, 700)),
    'offline': ('S18_offline_message.png', (220, 646, 1220, 698)),
    'phone': ('M01_browse_360.png', (0, 0, 720, 1300)),
    'phone_post': ('M02_post_360.png', (0, 0, 720, 1300)),
    'keyboard': ('K01_keyboard_focus.png', (130, 328, 1016, 508)),
    'analytics_full': ('S10_analytics_full.png', None),
}
for name, (file, box) in CROPS.items():
    im = Image.open(SRC / file).convert('RGB')
    if box:
        im = im.crop(box)
    im.save(OUT / f'{name}.png', optimize=True)
    print(name, im.size)
