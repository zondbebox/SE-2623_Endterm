# Export the deck to PDF (and optionally PNG previews) with Microsoft PowerPoint.
# Usage: powershell -ExecutionPolicy Bypass -File Final\_build\export_pptx.ps1 [-PngDir <folder>]
param([string]$PngDir = "")
$ErrorActionPreference = "Stop"
$final = Split-Path -Parent $PSScriptRoot
$pptx = Join-Path $final "Presentation\Group_Team_ICT_FinalPresentation.pptx"
$pdf = Join-Path $final "Presentation\Group_Team_ICT_FinalPresentation.pdf"
$app = New-Object -ComObject PowerPoint.Application
try {
    $deck = $app.Presentations.Open($pptx, $true, $false, $false)   # read-only, no window
    $deck.SaveAs($pdf, 32)                                           # ppSaveAsPDF
    if ($PngDir) {
        New-Item -ItemType Directory -Force $PngDir | Out-Null
        $i = 0
        foreach ($slide in $deck.Slides) { $i++; $slide.Export((Join-Path $PngDir ("slide{0:D2}.png" -f $i)), "PNG", 1600, 900) }
    }
    "Slides: $($deck.Slides.Count)  PDF: $pdf"
    $deck.Close()
} finally {
    $app.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($app) | Out-Null
}
