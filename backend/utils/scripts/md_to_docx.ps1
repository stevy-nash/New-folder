# md_to_docx.ps1
# Converts all .md files in outputs/ to a single combined.docx in docs/docx/
# Tables use 8pt font and autofit column widths via the Lua filter.
# Each document starts on a new page.
#
# Usage:
#   .\md_to_docx.ps1

$RepoRoot   = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$OutputsDir = Join-Path $RepoRoot "outputs"
$DocxDir    = Join-Path $RepoRoot "docs\docx"
$LuaFilter  = Join-Path $RepoRoot "scripts\full-width-tables.lua"

# Create destination folder if needed
New-Item -ItemType Directory -Path $DocxDir -Force | Out-Null

$mdFiles   = Get-ChildItem -Path $OutputsDir -Filter "*.md" | Sort-Object Name
$combined  = Join-Path $DocxDir "combined.docx"
$tempMerge = [System.IO.Path]::GetTempFileName() + ".md"

if ($mdFiles.Count -gt 0) {
    Write-Host "Building combined.docx from $($mdFiles.Count) markdown files ..."

    # Concatenate all .md files separated by a raw OpenXML page break so
    # pandoc inserts a real Word page break between each document.
    $pageBreak = @"

``````{=openxml}
<w:p><w:r><w:br w:type="page"/></w:r></w:p>
``````

"@
    $first = $true
    foreach ($md in $mdFiles) {
        if (-not $first) {
            Add-Content -Path $tempMerge -Value $pageBreak
        }
        Get-Content -Path $md.FullName -Raw | Add-Content -Path $tempMerge
        $first = $false
    }

    pandoc $tempMerge `
        --from markdown `
        --to docx `
        --output $combined `
        --lua-filter $LuaFilter `
        --standalone

    Remove-Item $tempMerge -ErrorAction SilentlyContinue

    if ($LASTEXITCODE -eq 0) {
        Write-Host "  Combined file: $combined" -ForegroundColor Green
    } else {
        Write-Host "  FAILED (exit $LASTEXITCODE)" -ForegroundColor Red
    }
} else {
    Write-Host "No .md files found in $OutputsDir" -ForegroundColor Yellow
}
