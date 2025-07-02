# Download-MP4.ps1
# Prompts for a video URL and downloads it as an MP4 via yt-dlp

# Prompt the user
$url = Read-Host "Enter the video URL"

# Check for empty input
if ([string]::IsNullOrWhiteSpace($url)) {
    Write-Host "No URL provided. Exiting." -ForegroundColor Yellow
    exit 1
}

# Run yt-dlp to get best video+audio and merge into MP4
yt-dlp `
    -f bestvideo+bestaudio `
    --merge-output-format mp4 `
    -o "%(title)s.mp4" `
    $url

# Notify on completion
if ($LASTEXITCODE -eq 0) {
    Write-Host "Download complete!" -ForegroundColor Green
} else {
    Write-Host "yt-dlp encountered an error (exit code $LASTEXITCODE)." -ForegroundColor Red
}
