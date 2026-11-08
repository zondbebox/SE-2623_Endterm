# Final demo video — put it here

1. Record the new video on the current interface (scene list: `Final/Demo/Demo_Plan_and_Backup.md`, section "Assignment 4 video").
2. Upload it (YouTube unlisted or Google Drive "anyone with the link").
3. Paste the link into `Final/_build/report_config.json` → `"updated_video_url": "https://…"`.
4. Optional: keep the MP4 here as `SE-2623_Campus_Lost_Found_Final.mp4` for offline playback (large files: GitHub accepts up to 100 MB).
5. Rebuild:
   ```bat
   Campus_Lost_Found\python\python.exe -B Final\_build\build_report.py
   cd Final\Presentation\source && node build_deck.js && cd ..\..\..
   powershell -ExecutionPolicy Bypass -File Final\_build\export_pptx.ps1
   ```
The report (Section 6) and backup slide B1 then show the new link instead of "link to be added".
