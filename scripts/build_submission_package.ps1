$ErrorActionPreference = 'Stop'

Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem

$root = (git rev-parse --show-toplevel).Trim()
$submission = Join-Path $root 'submission'
$package = Join-Path $submission 'SmartQuerySystem_Final_Submission'
$zip = Join-Path $submission 'SmartQuerySystem_Final_Submission.zip'
$artifactHashFile = Join-Path $submission 'ARTIFACT_SHA256.txt'
$commit = (git rev-parse HEAD).Trim()

Write-Host "Building submission package from $commit"

if (Test-Path -LiteralPath $package) {
    Remove-Item -LiteralPath $package -Recurse -Force
}
if (Test-Path -LiteralPath $zip) {
    Remove-Item -LiteralPath $zip -Force
}
New-Item -ItemType Directory -Path $package -Force | Out-Null

$exclude = @(
    '^submission/',
    '(^|/)\.env$',
    '(^|/)\.env\.(?!example$)[^/]+$',
    '(^|/)\.venv/',
    '(^|/)node_modules/',
    '(^|/)\.next/',
    '(^|/)__pycache__/',
    '(^|/)\.e2e/',
    '\.(pyc|db|sqlite|dump|key|pem)$'
)

$copied = 0
foreach ($rel in (git ls-files)) {
    $skip = $false
    foreach ($pattern in $exclude) {
        if ($rel -match $pattern) {
            $skip = $true
            break
        }
    }
    if ($skip) { continue }

    $src = Join-Path $root $rel
    if (-not (Test-Path -LiteralPath $src -PathType Leaf)) { continue }
    $dst = Join-Path $package $rel
    $dstDir = Split-Path -Parent $dst
    if (-not (Test-Path -LiteralPath $dstDir)) {
        New-Item -ItemType Directory -Path $dstDir -Force | Out-Null
    }
    Copy-Item -LiteralPath $src -Destination $dst -Force
    $copied++
}

$envExamples = @(git ls-files | Where-Object {
    $_ -match '(^|/)\.env\.example$' -and $_ -notmatch '^submission/'
})

$generatedAt = (Get-Date).ToString('yyyy-MM-ddTHH:mm:sszzz')
$manifest = [ordered]@{
    package = 'Smart Query Routing System - Final Hackathon Submission'
    generated_at_local = $generatedAt
    source_commit = $commit
    github_main = 'https://github.com/raphicsdigitalsolutions/smart-query-routing-system'
    frontend = 'https://smart-query-routing-system.netlify.app'
    backend = 'https://smart-query-backend.vercel.app'
    vercel_deployment = 'dpl_CRo9kXq4CBL8p8oSaaAyKdSjNVoM'
    docker_hub = @{
        repository = 'raphicsdigitalsolutions/smart-query-system'
        tags = @('latest', 'v1.0.0')
        digest = 'sha256:2cf0a5dea54dffd643abf29a1fa7b72966899ff7235350b95fe1da793c9c2177'
        anonymous_pull = 'PASS'
    }
    release_v1_database = @{
        status = 'READ-ONLY VERIFIED'
        alembic = 'feedf21773e1'
        public_tables = 17
        departments = 4
        users = 0
        tickets = 0
        writes = 0
    }
    verification = @{
        backend_tests = '229 passed, 17 warnings in 0:06:50'
        playwright_axe = '12 passed in 2.0m'
        vitest = '3 passed'
        npm_audit = '0 vulnerabilities'
        cron = '0 0 * * * (daily; Vercel Hobby compatible)'
    }
    limitations = @(
        'Netlify authenticated deploy state and source sync are NOT VERIFIED.',
        'Hosted cron invocation was NOT VERIFIED; only the daily schedule exists.',
        'Google OAuth, SMTP, Meta WhatsApp and real-user OpenAI BYOK were NOT VERIFIED.',
        'University/institutional approval is NOT VERIFIED.'
    )
    env_examples_included = $envExamples
    excluded = @('.env variants other than .example', '.venv', 'node_modules', '.next', '__pycache__', '.e2e', 'caches', 'DB dumps', 'key files')
    tracked_files_copied = $copied
}
$enc = New-Object System.Text.UTF8Encoding($false)
$manifestPath = Join-Path $package 'RELEASE_MANIFEST.json'
[System.IO.File]::WriteAllText($manifestPath, ($manifest | ConvertTo-Json -Depth 8), $enc)

Copy-Item -LiteralPath (Join-Path $root 'docs\HACKATHON_DEPLOYMENT_REPORT.pdf') -Destination (Join-Path $submission 'HACKATHON_DEPLOYMENT_REPORT.pdf') -Force
Copy-Item -LiteralPath (Join-Path $root 'docs\HACKATHON_DEPLOYMENT_SLIDES.pdf') -Destination (Join-Path $submission 'HACKATHON_DEPLOYMENT_SLIDES.pdf') -Force

$packageFiles = @(Get-ChildItem -LiteralPath $package -Recurse -File | Sort-Object FullName)
$zipStream = [System.IO.File]::Open($zip, [System.IO.FileMode]::Create, [System.IO.FileAccess]::Write, [System.IO.FileShare]::None)
$archive = New-Object System.IO.Compression.ZipArchive($zipStream, [System.IO.Compression.ZipArchiveMode]::Create)
$fixedTime = [datetime]'2026-11-24T00:00:00'
foreach ($file in $packageFiles) {
    $rel = $file.FullName.Substring($package.Length + 1).Replace('\', '/')
    $entry = $archive.CreateEntry($rel, [System.IO.Compression.CompressionLevel]::Optimal)
    $entry.LastWriteTime = $fixedTime
    $srcStream = [System.IO.File]::OpenRead($file.FullName)
    $dstStream = $entry.Open()
    $srcStream.CopyTo($dstStream)
    $dstStream.Dispose()
    $srcStream.Dispose()
}
$archive.Dispose()
$zipStream.Dispose()

$zipHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $zip).Hash.ToLowerInvariant()
$reportHash = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $submission 'HACKATHON_DEPLOYMENT_REPORT.pdf')).Hash.ToLowerInvariant()
$slidesHash = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $submission 'HACKATHON_DEPLOYMENT_SLIDES.pdf')).Hash.ToLowerInvariant()
$secretFiles = @($packageFiles | Where-Object { $_.Name -like '.env*' -and $_.Name -ne '.env.example' -or $_.Extension -in @('.key', '.pem', '.pfx', '.p12', '.db', '.sqlite', '.dump') })
$dependencyDirs = @(Get-ChildItem -LiteralPath $package -Recurse -Directory | Where-Object { $_.Name -in @('node_modules', '.venv', '__pycache__', '.next', '.e2e') })

$hashPattern = '^[0-9a-f]{64}$'
$hashChecks = [ordered]@{
    zip_sha256_64_hex = [bool]($zipHash -cmatch $hashPattern)
    report_pdf_sha256_64_hex = [bool]($reportHash -cmatch $hashPattern)
    slides_pdf_sha256_64_hex = [bool]($slidesHash -cmatch $hashPattern)
}
if ($hashChecks.Values -contains $false) {
    throw 'One or more artifact hashes are not 64-character lowercase hexadecimal strings.'
}

$artifactLines = @(
    'Final submission artifact SHA-256 values (64 lowercase hexadecimal characters)'
    'Generated after archive rebuild; this file is gitignored and is not inside the ZIP.'
    ''
    "source_commit=$commit"
    "zip_sha256=$zipHash"
    "zip_bytes=$((Get-Item -LiteralPath $zip).Length)"
    "report_pdf_sha256=$reportHash"
    "slides_pdf_sha256=$slidesHash"
    ''
    "zip_sha256_64_hex=$($hashChecks.zip_sha256_64_hex)"
    "report_pdf_sha256_64_hex=$($hashChecks.report_pdf_sha256_64_hex)"
    "slides_pdf_sha256_64_hex=$($hashChecks.slides_pdf_sha256_64_hex)"
)
[System.IO.File]::WriteAllLines($artifactHashFile, $artifactLines, $enc)

[pscustomobject]@{
    source_commit = $commit
    files_in_package = $packageFiles.Count
    evidence_files = @($packageFiles | Where-Object { $_.FullName -like '*\docs\evidence\*' }).Count
    env_examples_included = $envExamples.Count
    zip_bytes = (Get-Item -LiteralPath $zip).Length
    zip_sha256 = $zipHash
    report_pdf_sha256 = $reportHash
    slides_pdf_sha256 = $slidesHash
    hash_checks = $hashChecks
    secret_or_binary_files = $secretFiles.Count
    dependency_directories = $dependencyDirs.Count
    artifact_hash_file = $artifactHashFile
} | ConvertTo-Json -Depth 4
