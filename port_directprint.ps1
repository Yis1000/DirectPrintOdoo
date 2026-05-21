param([string]$branch)

Write-Host "Porting to branch $branch"
git checkout $branch

# Remove old files
Remove-Item -Path yis_direct_print\* -Recurse -Force -ErrorAction SilentlyContinue

# Copy new local files
Copy-Item -Path 'C:\Users\Jesus\Desktop\DOCKERS ODOO\Modulos\DirectPrintOdoo\*' -Destination yis_direct_print -Recurse

# Add banner
New-Item -ItemType Directory -Force -Path yis_direct_print\static\description
Copy-Item -Path 'C:\Users\Jesus\Desktop\DOCKERS ODOO\Imagenes\Banners\BannerDirectPrint.png' -Destination yis_direct_print\static\description\banner.png

# Modify manifest
$manifestPath = "yis_direct_print\__manifest__.py"
$manifest = Get-Content $manifestPath -Raw
$manifest = $manifest -replace "'version': '1.0'", "'version': '$branch.1.0.0'"
if ($manifest -notmatch "'images'") {
    $manifest = $manifest -replace "'installable': True", "'images': ['static/description/banner.png'],`n    'installable': True"
}
Set-Content $manifestPath -Value $manifest

# Commit and Push
git add .
git commit -m "Port to $branch from local and update banner"
git push origin $branch
