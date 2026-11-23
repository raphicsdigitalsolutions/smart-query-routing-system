<#
.SYNOPSIS
    Safe, reproducible local demonstration starter and verifier for the
    Smart Query Routing & Email Automation System.

.DESCRIPTION
    - Checks local dependencies (Python venv, Node.js/npm, Docker CLI & Compose files).
    - Checks required environment variable names in .env.example / backend/.env.example
      WITHOUT printing secret values.
    - Automatically detects if the requested API or Frontend port is already
      occupied by another process (such as a pre-existing uvicorn server on 8000)
      and selects a free local port so demo_server.py never collides with
      unrelated processes.
    - Starts the disposable local demonstration stack (FastAPI backend with
      seeded SQLite demo database + Next.js production server) without
      connecting to any production or external database/provider resource.
    - Performs health checks, BFF-to-backend connectivity checks, and an
      end-to-end BFF login verification for demo.student@university.edu.
    - Explains how to stop the services cleanly (or stops them automatically
      when -SmokeTest is specified).

.PARAMETER SmokeTest
    Starts the local demo backend and frontend, verifies all health endpoints,
    BFF connectivity, and student demo login, and stops the services cleanly.

.PARAMETER Stop
    Stops any running background local demo processes started by this script.

.PARAMETER ApiPort
    Preferred local loopback port for the FastAPI demo server (default: 8010).
    If occupied, the script automatically selects the next available port.

.PARAMETER FrontendPort
    Preferred local loopback port for the Next.js frontend server (default: 3000).
    If occupied, the script automatically selects the next available port.
#>
[CmdletBinding()]
param(
    [switch]$SmokeTest,
    [switch]$Stop,
    [int]$ApiPort = 8010,
    [int]$FrontendPort = 3000
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$BackendDir = Join-Path $RepoRoot "backend"
$FrontendDir = Join-Path $RepoRoot "frontend-next"
$StateDir = Join-Path $FrontendDir ".e2e"
$PidFile = Join-Path $StateDir "local_demo_pids.json"

if (-not (Test-Path $StateDir)) {
    New-Item -ItemType Directory -Path $StateDir -Force | Out-Null
}

function Stop-LocalDemoServices {
    Write-Host "`n[Stop] Stopping local demo services..." -ForegroundColor Cyan
    if (Test-Path $PidFile) {
        try {
            $saved = Get-Content $PidFile -Raw | ConvertFrom-Json
            foreach ($procId in @($saved.backend_pid, $saved.frontend_pid)) {
                if ($procId) {
                    $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
                    if ($proc) {
                        Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
                        Write-Host "  Stopped process PID $procId ($($proc.ProcessName))" -ForegroundColor Green
                    }
                }
            }
        } finally {
            Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
        }
    } else {
        Write-Host "  No active PID file found at $PidFile." -ForegroundColor Yellow
    }
}

if ($Stop) {
    Stop-LocalDemoServices
    exit 0
}

# Clean up any previous demo processes recorded in our own PID file first.
if (Test-Path $PidFile) {
    Stop-LocalDemoServices
}

function Test-PortInUse([int]$Port) {
    $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    return ($null -ne $conn)
}

function Resolve-FreePort([int]$PreferredPort, [string]$ServiceName) {
    $candidate = $PreferredPort
    while (Test-PortInUse $candidate) {
        $ownerPid = (Get-NetTCPConnection -LocalPort $candidate -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1).OwningProcess
        Write-Host "  [WARN] Port $candidate is already in use by PID $ownerPid ($ServiceName will not touch PID $ownerPid)." -ForegroundColor Yellow
        $candidate++
    }
    if ($candidate -ne $PreferredPort) {
        Write-Host "  [OK] Selected free port $candidate for $ServiceName." -ForegroundColor Green
    }
    return $candidate
}

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host " Smart Query Routing System - Local Demonstration Setup & Check" -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan

# 1. Dependency & Docker Configuration Check
Write-Host "`n[1/6] Checking dependencies and Docker configuration..." -ForegroundColor Cyan
$VenvPython = Join-Path $BackendDir ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    throw "Backend Python virtual environment not found at $VenvPython"
}
$pyVer = & $VenvPython --version 2>&1
Write-Host "  [OK] Backend Python: $pyVer" -ForegroundColor Green

$nodeVer = & node --version 2>&1
$npmVer = & cmd /c "npm --version" 2>&1
Write-Host "  [OK] Node.js: $nodeVer | npm: v$npmVer" -ForegroundColor Green

$dockerCmd = Get-Command docker -ErrorAction SilentlyContinue
if ($dockerCmd) {
    Write-Host "  [OK] Docker CLI installed: $($dockerCmd.Source)" -ForegroundColor Green
} else {
    Write-Host "  [WARN] Docker CLI not on PATH (disposable SQLite demo mode does not require Docker)" -ForegroundColor Yellow
}

foreach ($relPath in @("docker-compose.yml", "docker-compose.db.yml", "backend\Dockerfile", "frontend-next\Dockerfile", ".dockerignore", "backend\.dockerignore", "frontend-next\.dockerignore")) {
    $full = Join-Path $RepoRoot $relPath
    if (-not (Test-Path $full)) {
        throw "Required Docker packaging file missing: $relPath"
    }
}
Write-Host "  [OK] Dockerfiles, Compose files, and .dockerignore exclusions present." -ForegroundColor Green

# 2. Environment Variable Documentation & Presence Check (NEVER prints values)
Write-Host "`n[2/6] Auditing required environment variable names (values redacted)..." -ForegroundColor Cyan
$RequiredVars = @(
    "ENVIRONMENT",
    "DATABASE_URL",
    "JWT_SECRET_KEY",
    "JWT_ALGORITHM",
    "ACCESS_TOKEN_EXPIRE_MINUTES",
    "BYOK_ENCRYPTION_KEY",
    "ALLOW_GLOBAL_OPENAI_FALLBACK",
    "SLA_HOURS",
    "ESCALATION_CRON_SECRET",
    "EMAIL_NOTIFICATIONS_ENABLED",
    "WHATSAPP_ENABLED",
    "GOOGLE_OAUTH_ENABLED",
    "MAX_UPLOAD_BYTES",
    "ALLOWED_UPLOAD_TYPES",
    "ATTACHMENT_STORAGE_DIR",
    "MALWARE_SCAN_ENABLED"
)

function Get-EnvFileKeys([string]$Path) {
    $keys = @{}
    if (Test-Path $Path) {
        foreach ($line in (Get-Content $Path)) {
            $trimmed = $line.Trim()
            if ($trimmed -and -not $trimmed.StartsWith("#") -and $trimmed.Contains("=")) {
                $k = ($trimmed.Split("=", 2)[0]).Trim()
                $v = ($trimmed.Split("=", 2)[1]).Trim()
                $keys[$k] = ($v.Length -gt 0)
            }
        }
    }
    return $keys
}

$rootExampleKeys = Get-EnvFileKeys (Join-Path $RepoRoot ".env.example")
$backendExampleKeys = Get-EnvFileKeys (Join-Path $BackendDir ".env.example")

$missingInExamples = @()
foreach ($varName in $RequiredVars) {
    if (-not $rootExampleKeys.ContainsKey($varName) -or -not $backendExampleKeys.ContainsKey($varName)) {
        $missingInExamples += $varName
    }
}
if ($missingInExamples.Count -gt 0) {
    throw "Missing required variable documentation in .env.example files: $($missingInExamples -join ', ')"
}
Write-Host "  [OK] All $($RequiredVars.Count) required environment variables are documented in .env.example and backend/.env.example (0 values printed)." -ForegroundColor Green

# 3. Ensure Next.js Production Build Exists
$NextBuildId = Join-Path $FrontendDir ".next\BUILD_ID"
if (-not (Test-Path $NextBuildId)) {
    Write-Host "`n[3/6] Building Next.js frontend production bundle..." -ForegroundColor Cyan
    Push-Location $FrontendDir
    try {
        & cmd /c "npm run build"
        if ($LASTEXITCODE -ne 0) { throw "Next.js build failed." }
    } finally {
        Pop-Location
    }
} else {
    Write-Host "`n[3/6] Next.js production build present (.next/BUILD_ID verified)." -ForegroundColor Cyan
}

# 4. Resolve Conflict-Free Local Ports & Start Services
Write-Host "`n[4/6] Starting disposable local demo services (isolated SQLite, no production resources)..." -ForegroundColor Cyan
$ApiPort = Resolve-FreePort -PreferredPort $ApiPort -ServiceName "Demo FastAPI Backend"
$FrontendPort = Resolve-FreePort -PreferredPort $FrontendPort -ServiceName "Demo Next.js Frontend"

$BackendLog = Join-Path $StateDir "demo_backend.log"
$BackendErr = Join-Path $StateDir "demo_backend.err.log"
$FrontendLog = Join-Path $StateDir "demo_frontend.log"
$FrontendErr = Join-Path $StateDir "demo_frontend.err.log"

$env:DEMO_API_PORT = "$ApiPort"
$env:API_BASE_URL = "http://127.0.0.1:$ApiPort/api/v1"
$env:NEXT_PUBLIC_API_BASE_URL = "http://127.0.0.1:$ApiPort/api/v1"

$backendProc = Start-Process -FilePath $VenvPython `
    -ArgumentList @("demo_server.py") `
    -WorkingDirectory $BackendDir `
    -RedirectStandardOutput $BackendLog `
    -RedirectStandardError $BackendErr `
    -PassThru -WindowStyle Hidden

$NextCli = Join-Path $FrontendDir "node_modules\next\dist\bin\next"
$frontendProc = Start-Process -FilePath "node" `
    -ArgumentList @($NextCli, "start", "--hostname", "127.0.0.1", "--port", "$FrontendPort") `
    -WorkingDirectory $FrontendDir `
    -RedirectStandardOutput $FrontendLog `
    -RedirectStandardError $FrontendErr `
    -PassThru -WindowStyle Hidden

@{
    backend_pid = $backendProc.Id
    frontend_pid = $frontendProc.Id
    api_port = $ApiPort
    frontend_port = $FrontendPort
    started_at = (Get-Date).ToString("o")
} | ConvertTo-Json | Set-Content -Path $PidFile -Encoding UTF8

Write-Host "  Started Backend PID $($backendProc.Id) on http://127.0.0.1:$ApiPort" -ForegroundColor Green
Write-Host "  Started Frontend PID $($frontendProc.Id) on http://127.0.0.1:$FrontendPort (BFF -> http://127.0.0.1:$ApiPort/api/v1)" -ForegroundColor Green

# 5. Health & Connectivity Verification (verifies spawned process is still alive)
Write-Host "`n[5/6] Performing health and BFF-to-backend connectivity checks..." -ForegroundColor Cyan
function Wait-ForEndpoint([string]$Url, [System.Diagnostics.Process]$OwnerProcess, [int]$TimeoutSeconds = 120) {
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if ($null -ne $OwnerProcess) {
            $OwnerProcess.Refresh()
            if ($OwnerProcess.HasExited) {
                throw "Process PID $($OwnerProcess.Id) exited unexpectedly (exit code $($OwnerProcess.ExitCode)) while waiting for $Url. Check logs in $StateDir."
            }
        }
        $prevEap = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        try {
            $body = & curl.exe -fs --max-time 3 $Url
            $code = $LASTEXITCODE
        } finally {
            $ErrorActionPreference = $prevEap
        }
        if ($code -eq 0) {
            return [PSCustomObject]@{
                StatusCode = 200
                Content    = ($body -join "`n")
            }
        }
        Start-Sleep -Milliseconds 750
    }
    throw "Timed out waiting for endpoint: $Url"
}

try {
    $beHealth = Wait-ForEndpoint -Url "http://127.0.0.1:$ApiPort/health" -OwnerProcess $backendProc
    Write-Host "  [PASS] Backend Liveness (/health): HTTP $($beHealth.StatusCode) -> $($beHealth.Content.Trim())" -ForegroundColor Green

    $beStatus = Wait-ForEndpoint -Url "http://127.0.0.1:$ApiPort/api/v1/status" -OwnerProcess $backendProc
    Write-Host "  [PASS] Backend API Status (/api/v1/status): HTTP $($beStatus.StatusCode)" -ForegroundColor Green

    $beDb = Wait-ForEndpoint -Url "http://127.0.0.1:$ApiPort/api/v1/status/database" -OwnerProcess $backendProc
    Write-Host "  [PASS] Backend Database Readiness (/api/v1/status/database): HTTP $($beDb.StatusCode) -> $($beDb.Content.Trim())" -ForegroundColor Green

    $feHealth = Wait-ForEndpoint -Url "http://127.0.0.1:$FrontendPort/api/health" -OwnerProcess $frontendProc
    Write-Host "  [PASS] Frontend BFF -> Backend Health (/api/health): HTTP $($feHealth.StatusCode) -> $($feHealth.Content.Trim())" -ForegroundColor Green

    $feLogin = Wait-ForEndpoint -Url "http://127.0.0.1:$FrontendPort/login" -OwnerProcess $frontendProc
    Write-Host "  [PASS] Frontend UI (/login): HTTP $($feLogin.StatusCode)" -ForegroundColor Green

    # 6. End-to-End BFF Student Login Verification
    Write-Host "`n[6/6] Verifying student demo login via Frontend BFF (POST /api/auth/login)..." -ForegroundColor Cyan
    $loginProbeScript = @"
import json, urllib.request
req = urllib.request.Request(
    'http://127.0.0.1:$FrontendPort/api/auth/login',
    data=json.dumps({'email': 'demo.student@university.edu', 'password': 'LocalTestDemo123!'}).encode('utf-8'),
    headers={'Content-Type': 'application/json'},
    method='POST',
)
with urllib.request.urlopen(req, timeout=10) as resp:
    payload = json.loads(resp.read().decode('utf-8'))
    cookies = resp.headers.get_all('Set-Cookie') or []
    has_session = any('smartquery_session=' in c for c in cookies)
    assert resp.status == 200, f'Unexpected status {resp.status}'
    assert payload['user']['email'] == 'demo.student@university.edu'
    assert payload['user']['role'] == 'student'
    assert has_session, 'Missing smartquery_session HttpOnly cookie'
    print('HTTP', resp.status, '-> user=' + payload['user']['email'], 'role=' + payload['user']['role'], 'session_cookie=present')
"@
    $loginCheckOut = & $VenvPython -c $loginProbeScript
    if ($LASTEXITCODE -ne 0) {
        throw "Student demo login verification failed via Frontend BFF."
    }
    Write-Host "  [PASS] Student BFF Login (/api/auth/login): $($loginCheckOut.Trim())" -ForegroundColor Green
} catch {
    Stop-LocalDemoServices
    throw
}

if ($SmokeTest) {
    Write-Host "`n[SmokeTest] All health and BFF login checks passed. Stopping services cleanly..." -ForegroundColor Cyan
    Stop-LocalDemoServices
    Write-Host "[SmokeTest] PASS" -ForegroundColor Green
    exit 0
}

Write-Host "`n=================================================================" -ForegroundColor Green
Write-Host " LOCAL DEMONSTRATION READY" -ForegroundColor Green
Write-Host "=================================================================" -ForegroundColor Green
Write-Host " Frontend UI:          http://127.0.0.1:$FrontendPort/login"
Write-Host " Backend API Docs:     http://127.0.0.1:$ApiPort/docs"
Write-Host " Backend Health:       http://127.0.0.1:$ApiPort/health"
Write-Host " Frontend BFF Health:  http://127.0.0.1:$FrontendPort/api/health"
Write-Host ""
Write-Host " Disposable Demo Accounts (see docs/DEMO_TEST_DATA_GUIDE.md):"
Write-Host "   Student 1:          demo.student@university.edu"
Write-Host "   Student 2:          demo.student2@university.edu"
Write-Host "   CS Instructor 1:    demo.staff.cs1@university.edu"
Write-Host "   CS Instructor 2:    demo.staff.cs2@university.edu (On Active Leave)"
Write-Host "   Registry Staff:     demo.staff.reg@university.edu"
Write-Host "   Scholarships Staff: demo.staff.fin@university.edu"
Write-Host "   CS HOD:             demo.hod.cs@university.edu"
Write-Host "   Registry HOD:       demo.hod.reg@university.edu"
Write-Host "   System Admin:       demo.admin@university.edu"
Write-Host ""
Write-Host " To stop the local demonstration services cleanly, run:" -ForegroundColor Yellow
Write-Host "   powershell -ExecutionPolicy Bypass -File .\scripts\start_local_demo.ps1 -Stop" -ForegroundColor Yellow
