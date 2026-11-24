$ErrorActionPreference = 'Stop'

$root = (git rev-parse --show-toplevel).Trim()
$submission = Join-Path $root 'submission'
$package = Join-Path $submission 'SmartQuerySystem_Final_Submission'
$zip = Join-Path $submission 'SmartQuerySystem_Final_Submission.zip'
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
    '(^|/)\.env(\.|$)',
    '(^|/)\.venv/',
    '(^|/)node_modules/',
    '(^|/)\.next/',
    '(^|/)__pycache__/',
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

$manifest = [ordered]@{
    package = 'Smart Query Routing System - Final Hackathon Submission'
    generated_at_local = (Get-Date).ToString('yyyy-MM-ddTHH:mm:sszzz')
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
    tracked_files_copied = $copied
}
$manifestPath = Join-Path $package 'RELEASE_MANIFEST.json'
$enc = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($manifestPath, ($manifest | ConvertTo-Json -Depth 8), $enc)

Copy-Item -LiteralPath (Join-Path $root 'docs\HACKATHON_DEPLOYMENT_REPORT.pdf') -Destination (Join-Path $submission 'HACKATHON_DEPLOYMENT_REPORT.pdf') -Force
Copy-Item -LiteralPath (Join-Path $root 'docs\HACKATHON_DEPLOYMENT_SLIDES.pdf') -Destination (Join-Path $submission 'HACKATHON_DEPLOYMENT_SLIDES.pdf') -Force

Compress-Archive -Path (Join-Path $package '*') -DestinationPath $zip -CompressionLevel Optimal

$packageFiles = @(Get-ChildItem -LiteralPath $package -Recurse -File)
$secretFiles = @($packageFiles | Where-Object { $_.Name -like '.env*' -or $_.Extension -in @('.key', '.pem', '.pfx', '.p12', '.db', '.sqlite', '.dump') })
$dependencyDirs = @(Get-ChildItem -LiteralPath $package -Recurse -Directory | Where-Object { $_.Name -in @('node_modules', '.venv', '__pycache__', '.next') })

[pscustomobject]@{
    source_commit = $commit
    files_in_package = $packageFiles.Count
    zip_bytes = (Get-Item -LiteralPath $zip).Length
    secret_or_binary_files = $secretFiles.Count
    dependency_directories = $dependencyDirs.Count
    package = $package
    zip = $zip
} | ConvertTo-Json -Depth 4
