$ErrorActionPreference = 'Stop'

$projectRoot = [System.IO.Path]::GetFullPath((Split-Path -Parent $MyInvocation.MyCommand.Path)).TrimEnd('\')
$basePath = [Environment]::GetFolderPath('LocalApplicationData')
if ([string]::IsNullOrWhiteSpace($basePath)) {
    $basePath = [System.IO.Path]::GetTempPath()
}
$bytes = [System.Text.Encoding]::UTF8.GetBytes($projectRoot.ToLowerInvariant())
$sha = [System.Security.Cryptography.SHA256]::Create()
try {
    $hash = [BitConverter]::ToString($sha.ComputeHash($bytes)).Replace('-', '').Substring(0, 16)
}
finally {
    $sha.Dispose()
}
$statePath = Join-Path (Join-Path $basePath 'GestorComercioAlPorMenor') "$hash.json"

function Get-ProcessSnapshot {
    param([int]$ProcessId)

    $process = Get-CimInstance -ClassName Win32_Process -Filter "ProcessId = $ProcessId" -ErrorAction SilentlyContinue
    if (-not $process) {
        return $null
    }

    $created = [datetime]$process.CreationDate
    return [pscustomobject]@{
        ProcessId = [int]$process.ProcessId
        ParentProcessId = [int]$process.ParentProcessId
        CreationTicks = [string]$created.ToUniversalTime().Ticks
        ExecutablePath = [string]$process.ExecutablePath
        CommandLine = [string]$process.CommandLine
    }
}

function Test-ProcessMatches {
    param(
        [object]$Expected,
        [object]$Actual
    )

    if (-not $Expected -or -not $Actual) {
        return $false
    }
    return (
        [string]$Expected.CreationTicks -eq [string]$Actual.CreationTicks -and
        [string]$Expected.ExecutablePath -ieq [string]$Actual.ExecutablePath -and
        [string]$Expected.CommandLine -ieq [string]$Actual.CommandLine
    )
}

function Get-ProcessTree {
    param([int]$RootProcessId)

    $allProcesses = @(Get-CimInstance -ClassName Win32_Process -ErrorAction SilentlyContinue)
    $byParent = @{}
    foreach ($process in $allProcesses) {
        $parentId = [string]$process.ParentProcessId
        if (-not $byParent.ContainsKey($parentId)) {
            $byParent[$parentId] = @()
        }
        $byParent[$parentId] += $process
    }

    $root = $allProcesses | Where-Object { [int]$_.ProcessId -eq $RootProcessId } | Select-Object -First 1
    if (-not $root) {
        return @()
    }

    $rootCreated = ([datetime]$root.CreationDate).ToUniversalTime().Ticks
    $queue = New-Object 'System.Collections.Queue'
    $queue.Enqueue([pscustomobject]@{ Process = $root; Depth = 0 })
    $result = @()
    while ($queue.Count -gt 0) {
        $item = $queue.Dequeue()
        $process = $item.Process
        $created = ([datetime]$process.CreationDate).ToUniversalTime().Ticks
        if ($created -lt $rootCreated) {
            continue
        }

        $result += [pscustomobject]@{
            ProcessId = [int]$process.ProcessId
            ParentProcessId = [int]$process.ParentProcessId
            CreationTicks = [string]$created
            ExecutablePath = [string]$process.ExecutablePath
            CommandLine = [string]$process.CommandLine
            Depth = [int]$item.Depth
        }

        $childKey = [string]$process.ProcessId
        if ($byParent.ContainsKey($childKey)) {
            foreach ($child in $byParent[$childKey]) {
                $queue.Enqueue([pscustomobject]@{ Process = $child; Depth = [int]$item.Depth + 1 })
            }
        }
    }
    return $result
}

function Stop-VerifiedProcess {
    param(
        [object]$Expected,
        [string]$Description
    )

    $actual = Get-ProcessSnapshot -ProcessId ([int]$Expected.ProcessId)
    if (-not (Test-ProcessMatches -Expected $Expected -Actual $actual)) {
        return $false
    }

    try {
        Stop-Process -Id ([int]$Expected.ProcessId) -ErrorAction Stop
        Write-Host "Detenido: $Description (PID $($Expected.ProcessId))." -ForegroundColor Green
        return $true
    }
    catch {
        Write-Host "No se pudo detener $Description (PID $($Expected.ProcessId)): $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

if (-not (Test-Path -LiteralPath $statePath)) {
    Write-Host 'No hay procesos de este proyecto registrados para detener.'
    return
}

try {
    $state = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json -ErrorAction Stop
}
catch {
    throw "No se pudo leer el registro de procesos; no se detendrá ningún proceso. $($_.Exception.Message)"
}

if ([string]$state.ProjectRoot -ine $projectRoot) {
    throw 'El registro de procesos no corresponde a esta raíz de proyecto; no se detendrá ningún proceso.'
}

$remainingEntries = @()
foreach ($entry in @($state.Services)) {
    $terminal = Get-ProcessSnapshot -ProcessId ([int]$entry.Terminal.ProcessId)
    $terminalIsOurs = Test-ProcessMatches -Expected $entry.Terminal -Actual $terminal
    $liveTree = @()
    if ($terminalIsOurs) {
        $liveTree = @(Get-ProcessTree -RootProcessId ([int]$entry.Terminal.ProcessId))
    }

    $candidates = @()
    foreach ($saved in @($entry.OwnedProcesses)) {
        $snapshot = Get-ProcessSnapshot -ProcessId ([int]$saved.ProcessId)
        if (Test-ProcessMatches -Expected $saved -Actual $snapshot) {
            $candidates += [pscustomobject]@{
                ProcessId = [int]$saved.ProcessId
                CreationTicks = [string]$saved.CreationTicks
                ExecutablePath = [string]$saved.ExecutablePath
                CommandLine = [string]$saved.CommandLine
                Depth = [int]$saved.Depth
            }
        }
    }
    foreach ($process in $liveTree) {
        if ($process.ProcessId -ne [int]$entry.Terminal.ProcessId) {
            $alreadySaved = $candidates | Where-Object { $_.ProcessId -eq $process.ProcessId }
            if (-not $alreadySaved) {
                $candidates += $process
            }
        }
    }
    $entry.OwnedProcesses = @($candidates)

    if ($terminalIsOurs) {
        try {
            $terminalProcess = Get-Process -Id ([int]$entry.Terminal.ProcessId) -ErrorAction Stop
            if ($terminalProcess.CloseMainWindow()) {
                Write-Host "Solicitado cierre normal de la terminal de $($entry.Name)."
                for ($attempt = 0; $attempt -lt 30; $attempt++) {
                    Start-Sleep -Milliseconds 100
                    if (-not (Get-ProcessSnapshot -ProcessId ([int]$entry.Terminal.ProcessId))) {
                        break
                    }
                }
            }
        }
        catch {
            Write-Verbose "No se pudo solicitar el cierre normal de $($entry.Name): $($_.Exception.Message)"
        }
    }

    foreach ($candidate in @($candidates | Sort-Object -Property Depth -Descending)) {
        $null = Stop-VerifiedProcess -Expected $candidate -Description "$($entry.Name), proceso hijo"
    }
    if ($terminalIsOurs) {
        $null = Stop-VerifiedProcess -Expected $entry.Terminal -Description "$($entry.Name), terminal"
    }

    $stillRunning = $false
    if (Test-ProcessMatches -Expected $entry.Terminal -Actual (Get-ProcessSnapshot -ProcessId ([int]$entry.Terminal.ProcessId))) {
        $stillRunning = $true
    }
    foreach ($owned in @($entry.OwnedProcesses)) {
        if (Test-ProcessMatches -Expected $owned -Actual (Get-ProcessSnapshot -ProcessId ([int]$owned.ProcessId))) {
            $stillRunning = $true
        }
    }
    if ($stillRunning) {
        $remainingEntries += $entry
        Write-Host "Quedaron procesos verificados de $($entry.Name); vuelve a ejecutar detener_proyecto.ps1." -ForegroundColor Yellow
    }
}

if ($remainingEntries.Count -gt 0) {
    $state.Services = @($remainingEntries)
    $state.UpdatedAtUtc = [datetime]::UtcNow.ToString('o')
    ConvertTo-Json -InputObject $state -Depth 10 | Set-Content -LiteralPath $statePath -Encoding UTF8
}
else {
    Remove-Item -LiteralPath $statePath -Force
    Write-Host 'No quedan procesos con identidad registrada activos; los PID no verificados no fueron detenidos.'
}
