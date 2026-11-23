<#
.SYNOPSIS
Executes a disposable, non-production PostgreSQL backup/restore rehearsal.

.DESCRIPTION
Starts a throwaway postgres:16-alpine container on localhost:55432, applies the
repository's Alembic migrations, inserts synthetic representative records,
creates a custom-format pg_dump, restores it into (1) a fresh scratch database
and (2) an existing migrated database with --clean --if-exists, then compares
schema and representative-record fingerprints. No existing Compose volume,
remote database, or production credential is used or modified.
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $repoRoot 'backend'
$evidenceDir = Join-Path (Join-Path $repoRoot 'docs') 'evidence'
$dumpPath = Join-Path $evidenceDir 'rehearsal.dump'
$evidencePath = Join-Path $evidenceDir 'backup_restore_rehearsal.json'
$python = Join-Path (Join-Path (Join-Path $backendDir '.venv') 'Scripts') 'python.exe'

$container = 'smartquery-backup-restore-rehearsal'
$image = 'postgres:16-alpine'
$db = 'smartquery_db'
$user = 'smartquery'
# Disposable local-only credential; never reused outside this rehearsal.
$password = 'rehearsal-only-password'
$port = 55432
$reference = 'TKT-RESTORE01'
$staleReference = 'TKT-STALE001'

New-Item -ItemType Directory -Force -Path $evidenceDir | Out-Null

function Invoke-Docker {
    param([string[]]$DockerArgs)
    & docker @DockerArgs
    if ($LASTEXITCODE -ne 0) {
        throw "docker $($DockerArgs -join ' ') failed with exit code ${LASTEXITCODE}"
    }
}

function Invoke-Python {
    param([string[]]$PythonArgs)
    & $python @PythonArgs
    if ($LASTEXITCODE -ne 0) {
        throw "python $($PythonArgs -join ' ') failed with exit code ${LASTEXITCODE}"
    }
}

function Get-Sha256Text {
    param([string]$Text)
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($Text)
    $hash = [System.Security.Cryptography.SHA256]::Create().ComputeHash($bytes)
    return ($hash | ForEach-Object { $_.ToString('x2') }) -join ''
}

# pg_dump 16 embeds a random \restrict token and re-deparses CHECK expressions,
# so its raw SQL is not byte-stable across a dump/restore cycle. This catalog
# query captures the same schema semantics in a deterministic form.
$schemaFingerprintSql = @'
SELECT 'table|' || table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
UNION ALL
SELECT 'column|' || table_name || '|' || column_name || '|' || data_type || '|' || is_nullable || '|' || COALESCE(column_default, '') FROM information_schema.columns WHERE table_schema = 'public'
UNION ALL
SELECT 'constraint|' || c.conrelid::regclass::text || '|' || c.conname || '|' || pg_get_constraintdef(c.oid) FROM pg_constraint c JOIN pg_namespace n ON n.oid = c.connamespace WHERE n.nspname = 'public'
UNION ALL
SELECT 'index|' || tablename || '|' || indexname || '|' || indexdef FROM pg_indexes WHERE schemaname = 'public'
UNION ALL
SELECT 'alembic|' || version_num FROM alembic_version
ORDER BY 1;
'@

function Get-SchemaHash {
    param([string]$Database)
    $rows = (& docker exec $container psql -U $user -d $Database -At -c $schemaFingerprintSql)
    if ($LASTEXITCODE -ne 0) { throw "schema fingerprint query failed for ${Database}" }
    # PostgreSQL re-deparses IN (...) CHECK expressions after restore. Compare
    # the ordered allowed values instead of the incidental cast formatting.
    $normalizedRows = $rows | ForEach-Object {
        $line = [string]$_
        if ($line.StartsWith('constraint|') -and $line -match '\|CHECK ') {
            $parts = $line.Split('|')
            $values = @([regex]::Matches($line, "'([^']*)'") | ForEach-Object { $_.Groups[1].Value })
            if ($values.Count -gt 0) {
                $line = "constraint|$($parts[1])|$($parts[2])|CHECK_VALUES($($values -join ','))"
            }
        }
        $line
    }
    $schemaText = ($normalizedRows -join "`n").Trim()
    $fingerprintPath = Join-Path $evidenceDir "schema_fingerprint_${Database}.txt"
    Set-Content -Path $fingerprintPath -Value $schemaText -Encoding UTF8
    return Get-Sha256Text $schemaText
}

function Get-RecordHash {
    param([string]$Database)
    $sql = "SELECT d.name, u.email, u.role, t.public_reference, t.subject, t.status, t.priority, t.channel FROM tickets t JOIN departments d ON d.id = t.department_id JOIN users u ON u.id = t.student_id WHERE t.public_reference = '$reference';"
    $row = (& docker exec $container psql -U $user -d $Database -At -F '|' -c $sql) -join "`n"
    if ($LASTEXITCODE -ne 0) { throw "representative-record query failed for ${Database}" }
    return Get-Sha256Text $row.Trim()
}

function Set-DatabaseUrl {
    param([string]$Database)
    $env:DATABASE_URL = "postgresql+psycopg://${user}:${password}@127.0.0.1:${port}/${Database}"
}

$previousDatabaseUrl = $env:DATABASE_URL
$containerStarted = $false
$results = [ordered]@{}

try {
    $imageDigest = (& docker image inspect $image --format '{{index .RepoDigests 0}}')
    if ($LASTEXITCODE -ne 0) { throw "Unable to inspect ${image}" }

    # The rehearsal container name is dedicated; remove any leftover from a
    # previous interrupted run before starting again.
    & docker rm --force $container 2>$null | Out-Null

    Invoke-Docker @(
        'run', '--detach', '--name', $container,
        '--env', "POSTGRES_DB=$db", '--env', "POSTGRES_USER=$user",
        '--env', "POSTGRES_PASSWORD=$password", '--publish', "${port}:5432",
        $image
    )
    $containerStarted = $true

    $ready = $false
    for ($attempt = 1; $attempt -le 30; $attempt++) {
        & docker exec $container pg_isready -U $user -d $db | Out-Null
        if ($LASTEXITCODE -eq 0) { $ready = $true; break }
        Start-Sleep -Seconds 1
    }
    if (-not $ready) { throw 'Disposable PostgreSQL container did not become ready' }

    Set-DatabaseUrl $db
    Push-Location $backendDir
    try {
        Invoke-Python @('-m', 'alembic', 'upgrade', 'head')

        $seed = @'
from sqlalchemy.orm import Session
from app.core.security import hash_password
from app.db.session import engine
from app.models import Department, Ticket, User

with Session(engine) as db:
    department = Department(name="Rehearsal Registrar", description="Synthetic backup fixture")
    student = User(
        full_name="Rehearsal Student",
        email="rehearsal.student@example.invalid",
        password_hash=hash_password("RehearsalOnly123!"),
        role="student",
    )
    db.add_all([department, student])
    db.flush()
    db.add(Ticket(
        public_reference="TKT-RESTORE01",
        subject="Restore rehearsal ticket",
        description="Synthetic representative record for backup verification.",
        priority="normal",
        status="new",
        channel="web",
        student_id=student.id,
        department_id=department.id,
    ))
    db.commit()
print("seeded")
'@
        $seed | & $python -
        if ($LASTEXITCODE -ne 0) { throw 'Representative-record seed failed' }

        $alembicVersion = (& docker exec $container psql -U $user -d $db -At -c 'SELECT version_num FROM alembic_version;') -join ''
        if ($LASTEXITCODE -ne 0) { throw 'Alembic version query failed' }
    }
    finally {
        Pop-Location
    }

    $sourceSchema = Get-SchemaHash $db
    $sourceRecord = Get-RecordHash $db

    Invoke-Docker @('exec',$container, 'pg_dump', '-U', $user, '-d', $db, '-Fc', '-f', '/tmp/rehearsal.dump')
    Invoke-Docker @('cp', "${container}:/tmp/rehearsal.dump", $dumpPath)
    $dumpSize = (Get-Item $dumpPath).Length
    if ($dumpSize -le 0) { throw 'Backup dump is empty' }

    # Restore 1: completely fresh database.
    Invoke-Docker @('exec',$container, 'createdb', '-U', $user, 'restore_fresh')
    Invoke-Docker @('exec',$container, 'pg_restore', '-U', $user, '-d', 'restore_fresh', '/tmp/rehearsal.dump')
    $freshSchema = Get-SchemaHash 'restore_fresh'
    $freshRecord = Get-RecordHash 'restore_fresh'

    # Restore 2: existing migrated database containing a stale row.
    Invoke-Docker @('exec',$container, 'createdb', '-U', $user, 'restore_existing')
    Set-DatabaseUrl 'restore_existing'
    Push-Location $backendDir
    try {
        Invoke-Python @('-m', 'alembic', 'upgrade', 'head')
        $stale = @'
from sqlalchemy.orm import Session
from app.core.security import hash_password
from app.db.session import engine
from app.models import Department, Ticket, User

with Session(engine) as db:
    department = Department(name="Stale Department", description="Must be removed by restore")
    student = User(
        full_name="Stale Student",
        email="stale.student@example.invalid",
        password_hash=hash_password("RehearsalOnly123!"),
        role="student",
    )
    db.add_all([department, student])
    db.flush()
    db.add(Ticket(
        public_reference="TKT-STALE001",
        subject="Stale pre-restore row",
        description="This row must not survive a clean restore.",
        priority="normal",
        status="new",
        channel="web",
        student_id=student.id,
        department_id=department.id,
    ))
    db.commit()
print("stale seeded")
'@
        $stale | & $python -
        if ($LASTEXITCODE -ne 0) { throw 'Stale-row seed failed' }
    }
    finally {
        Pop-Location
    }

    $staleBefore = (& docker exec $container psql -U $user -d restore_existing -At -c "SELECT count(*) FROM tickets WHERE public_reference = '$staleReference';") -join ''
    Invoke-Docker @('exec',$container, 'pg_restore', '--clean', '--if-exists', '-U', $user, '-d', 'restore_existing', '/tmp/rehearsal.dump')
    $existingSchema = Get-SchemaHash 'restore_existing'
    $existingRecord = Get-RecordHash 'restore_existing'
    $staleAfter = (& docker exec $container psql -U $user -d restore_existing -At -c "SELECT count(*) FROM tickets WHERE public_reference = '$staleReference';") -join ''

    $checks = [ordered]@{
        source_schema_sha256 = $sourceSchema
        fresh_restore_schema_sha256 = $freshSchema
        schema_match_fresh = ($sourceSchema -eq $freshSchema)
        existing_restore_schema_sha256 = $existingSchema
        schema_match_existing_clean = ($sourceSchema -eq $existingSchema)
        source_record_sha256 = $sourceRecord
        fresh_restore_record_sha256 = $freshRecord
        record_match_fresh = ($sourceRecord -eq $freshRecord)
        existing_restore_record_sha256 = $existingRecord
        record_match_existing_clean = ($sourceRecord -eq $existingRecord)
        stale_row_count_before_clean_restore = [int]$staleBefore.Trim()
        stale_row_count_after_clean_restore = [int]$staleAfter.Trim()
    }

    $rehearsalStatus = 'PASS'
    $booleanChecks = @(
        $checks.schema_match_fresh,
        $checks.schema_match_existing_clean,
        $checks.record_match_fresh,
        $checks.record_match_existing_clean
    )
    if ($booleanChecks -contains $false -or $checks.stale_row_count_after_clean_restore -ne 0) {
        $rehearsalStatus = 'FAIL'
    }

    $results = [ordered]@{
        status = $rehearsalStatus
        executed_at_utc = (Get-Date).ToUniversalTime().ToString('o')
        image = $image
        image_digest = $imageDigest
        container = $container
        port = $port
        database = $db
        alembic_version = $alembicVersion.Trim()
        dump_size_bytes = $dumpSize
        representative_reference = $reference
        stale_reference = $staleReference
        checks = $checks
        production_touched = $false
    }

    if ($results.status -ne 'PASS') { throw 'Backup/restore verification checks failed' }
    Write-Host 'Backup/restore rehearsal: PASS'
}
finally {
    if ($containerStarted) {
        # Removing the disposable container also discards both scratch databases.
        & docker rm --force $container 2>$null | Out-Null
    }
    if (Test-Path $dumpPath) { Remove-Item $dumpPath -Force }
    if ($null -eq $previousDatabaseUrl) { Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue }
    else { $env:DATABASE_URL = $previousDatabaseUrl }
    if ($results.Count -gt 0) {
        $results | ConvertTo-Json -Depth 8 | Set-Content -Path $evidencePath -Encoding UTF8
    }
}
