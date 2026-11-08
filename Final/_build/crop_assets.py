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
    'saved': ('S05_notice_created.png', (130, 190, 832, 730)),
    'search': ('S06_search_result.png', (130, 345, 780, 845)),
    'returned': ('S08_returned.png', (130, 190, 1000, 859)),
    'contact': ('S07_detail_contact.png', (1008, 236, 1310, 706)),
    'admin': ('S09_admin_panel.png', (100, 28, 1340, 700)),
    'analytics': ('S10_analytics.png', (150, 250, 1290, 900)),
    'remove': ('S12_remove_confirm.png', (130, 255, 1310, 530)),
    'locker_alert': ('S16_locker_alert.png', (195, 120, 1245, 440)),
    'locker_controls': ('S16_locker_alert.png', (195, 455, 1245, 700)),
    'offline': ('S18_offline_message.png', (220, 646, 1220, 698)),
    'phone': ('M01_browse_360.png', (0, 0, 720, 1300)),
    'phone_post': ('M02_post_360.png', (0, 0, 720, 1300)),
    'keyboard': ('K01_keyboard_focus.png', (130, 380, 1016, 560)),
    'analytics_full': ('S10_analytics_full.png', None),
}
for name, (file, box) in CROPS.items():
    im = Image.open(SRC / file).convert('RGB')
    if box:
        im = im.crop(box)
    im.save(OUT / f'{name}.png', optimize=True)
    print(name, im.size)
