# Assemble actual browser viewport captures using their recorded scroll positions.
# No changes to page contents or art assets; overlapping pixels are included once.
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
$captureRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../screenshots/home-art'))
$positions = Get-Content -LiteralPath (Join-Path $captureRoot 'scroll-positions.json') -Raw | ConvertFrom-Json
$first = [Drawing.Image]::FromFile((Join-Path $captureRoot 'scroll-0.jpg'))
$captureWidth = $first.Width
$captureScale = $first.Height / [double]$positions[0].viewport[1]
$captureHeight = [int][Math]::Round($positions[0].documentHeight * $captureScale)
$first.Dispose()
$canvas = [Drawing.Bitmap]::new($captureWidth, $captureHeight)
$graphics = [Drawing.Graphics]::FromImage($canvas)
$covered = 0.0
try {
    for ($index = 0; $index -lt $positions.Count; $index++) {
        $position = $positions[$index]
        if ($position.y -gt $covered + 1) { throw 'Missing page region between captures' }
        $frame = [Drawing.Image]::FromFile((Join-Path $captureRoot "scroll-$index.jpg"))
        try {
            if ($frame.Width -ne $captureWidth) { throw 'Capture widths differ' }
            $sourceTop = [int][Math]::Round(($covered - $position.y) * $captureScale)
            $destinationTop = [int][Math]::Round($covered * $captureScale)
            $stripHeight = [Math]::Min($frame.Height - $sourceTop, $captureHeight - $destinationTop)
            if ($stripHeight -gt 0) {
                $destination = [Drawing.Rectangle]::new(0, $destinationTop, $captureWidth, $stripHeight)
                $graphics.DrawImage($frame, $destination, 0, $sourceTop, $captureWidth, $stripHeight, [Drawing.GraphicsUnit]::Pixel)
            }
            $covered = [Math]::Min($position.documentHeight, $position.y + $position.viewport[1])
        }
        finally { $frame.Dispose() }
    }
    if ($covered -lt $positions[0].documentHeight) { throw 'Page footer was not captured' }
    $outputFile = Join-Path $captureRoot 'after-1440-full.jpg'
    $canvas.Save($outputFile, [Drawing.Imaging.ImageFormat]::Jpeg)
    Write-Output "Saved complete scroll capture: $captureWidth x $captureHeight"
}
finally { $graphics.Dispose(); $canvas.Dispose() }
