param(
    [switch]$CheckOnly
)

$ErrorActionPreference = 'Stop'

$script:ProjectRoot = [System.IO.Path]::GetFullPath((Split-Path -Parent $MyInvocation.MyCommand.Path)).TrimEnd('\')
$script:BackendPath = Join-Path $script:ProjectRoot 'backend'
$script:FrontendPath = Join-Path $script:ProjectRoot 'frontend'
$script:PythonPath = Join-Path $script:BackendPath '.venv\Scripts\python.exe'
$script:StateServices = @()

$apiServices = @(
    [pscustomobject]@{ Name = 'Identidad'; Module = 'app.services.identidad.main:app'; Port = 8001 },
    [pscustomobject]@{ Name = 'Catálogo'; Module = 'app.services.catalogo.main:app'; Port = 8002 },
    [pscustomobject]@{ Name = 'Organización'; Module = 'app.services.organizacion.main:app'; Port = 8003 },
    [pscustomobject]@{ Name = 'Compras'; Module = 'app.services.compras.main:app'; Port = 8004 },
    [pscustomobject]@{ Name = 'Inventarios'; Module = 'app.services.inventarios.main:app'; Port = 8005 },
    [pscustomobject]@{ Name = 'Ventas'; Module = 'app.services.ventas.main:app'; Port = 8006 },
    [pscustomobject]@{ Name = 'Reportes'; Module = 'app.services.reportes.main:app'; Port = 8007 }
)
$frontendService = [pscustomobject]@{ Name = 'Frontend'; Port = 5173 }

function Get-StateFilePath {
    $basePath = [Environment]::GetFolderPath('LocalApplicationData')
    if ([string]::IsNullOrWhiteSpace($basePath)) {
        $basePath = [System.IO.Path]::GetTempPath()
    }

    $bytes = [System.Text.Encoding]::UTF8.GetBytes($script:ProjectRoot.ToLowerInvariant())
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $hash = [BitConverter]::ToString($sha.ComputeHash($bytes)).Replace('-', '').Substring(0, 16)
    }
    finally {
        $sha.Dispose()
    }

    $directory = Join-Path $basePath 'GestorComercioAlPorMenor'
    if (-not (Test-Path -LiteralPath $directory)) {
        New-Item -ItemType Directory -Path $directory -Force | Out-Null
    }
    return Join-Path $directory "$hash.json"
}

$script:StatePath = Get-StateFilePath

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

function Stop-JustStartedTerminal {
    param([object]$TerminalSnapshot)

    $currentRoot = Get-ProcessSnapshot -ProcessId ([int]$TerminalSnapshot.ProcessId)
    if (-not (Test-ProcessMatches -Expected $TerminalSnapshot -Actual $currentRoot)) {
        return
    }

    $tree = @(Get-ProcessTree -RootProcessId ([int]$TerminalSnapshot.ProcessId))
    try {
        $terminalProcess = Get-Process -Id ([int]$TerminalSnapshot.ProcessId) -ErrorAction Stop
        $null = $terminalProcess.CloseMainWindow()
        Start-Sleep -Milliseconds 500
    }
    catch {
        Write-Verbose "No se pudo cerrar normalmente la terminal recién iniciada: $($_.Exception.Message)"
    }

    foreach ($process in @($tree | Where-Object { $_.ProcessId -ne [int]$TerminalSnapshot.ProcessId } |
        Sort-Object -Property Depth -Descending)) {
        $null = Stop-ExactProcess -Expected $process -Description 'proceso hijo recién iniciado'
    }
    $null = Stop-ExactProcess -Expected $TerminalSnapshot -Description 'terminal recién iniciada'
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

function Stop-ExactProcess {
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
        Write-Host "Detenido: $Description (PID $($Expected.ProcessId))." -ForegroundColor Yellow
        return $true
    }
    catch {
        Write-Host "No se pudo detener $Description (PID $($Expected.ProcessId)): $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

function Write-State {
    $document = [pscustomobject]@{
        ProjectRoot = $script:ProjectRoot
        UpdatedAtUtc = [datetime]::UtcNow.ToString('o')
        Services = @($script:StateServices)
    }
    $temporaryPath = "$($script:StatePath).$PID.tmp"
    ConvertTo-Json -InputObject $document -Depth 10 |
        Set-Content -LiteralPath $temporaryPath -Encoding UTF8
    Move-Item -LiteralPath $temporaryPath -Destination $script:StatePath -Force
}

function Test-PortOccupancy {
    param([int]$Port)

    $ownerId = $null
    try {
        $connection = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue |
            Select-Object -First 1
        if ($connection) {
            $ownerId = [int]$connection.OwningProcess
            return [pscustomobject]@{ InUse = $true; OwnerId = $ownerId }
        }
    }
    catch {
        Write-Verbose "No fue posible consultar Get-NetTCPConnection para el puerto ${Port}: $($_.Exception.Message)"
    }

    $listener = $null
    try {
        $listener = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Loopback, $Port)
        $listener.Start()
        return [pscustomobject]@{ InUse = $false; OwnerId = $null }
    }
    catch {
        return [pscustomobject]@{ InUse = $true; OwnerId = $null }
    }
    finally {
        if ($listener) {
            try { $listener.Stop() } catch { }
        }
    }
}

function Get-PortOwnerId {
    param([int]$Port)

    try {
        $connection = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue |
            Select-Object -First 1
        if ($connection) {
            return [int]$connection.OwningProcess
        }
    }
    catch {
        Write-Verbose "No fue posible consultar el proceso del puerto ${Port}: $($_.Exception.Message)"
    }
    return $null
}

function ConvertTo-PowerShellLiteral {
    param([string]$Value)
    return "'" + $Value.Replace("'", "''") + "'"
}

function Get-PowerShellHostPath {
    $command = Get-Command powershell.exe -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }
    $command = Get-Command pwsh.exe -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }
    return $null
}

function Start-VisibleTerminal {
    param(
        [string]$Name,
        [string]$WorkingDirectory,
        [string]$Title,
        [string]$Command
    )

    $lines = @(
        "`$Host.UI.RawUI.WindowTitle = $(ConvertTo-PowerShellLiteral $Title)",
        "Set-Location -LiteralPath $(ConvertTo-PowerShellLiteral $WorkingDirectory)",
        $Command,
        "if (`$LASTEXITCODE -ne 0) { Write-Host 'El proceso terminó con código' `$LASTEXITCODE -ForegroundColor Red }"
    )
    $encoded = [Convert]::ToBase64String([System.Text.Encoding]::Unicode.GetBytes(($lines -join "`r`n")))
    $terminal = Start-Process -FilePath $script:PowerShellHostPath `
        -ArgumentList @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-NoExit', '-EncodedCommand', $encoded) `
        -PassThru

    $snapshot = $null
    for ($attempt = 0; $attempt -lt 20 -and -not $snapshot; $attempt++) {
        Start-Sleep -Milliseconds 100
        $snapshot = Get-ProcessSnapshot -ProcessId $terminal.Id
    }
    if (-not $snapshot) {
        $unverifiedTerminal = Get-ProcessSnapshot -ProcessId $terminal.Id
        if ($unverifiedTerminal) {
            Stop-JustStartedTerminal -TerminalSnapshot $unverifiedTerminal
        }
        throw "No se pudo identificar la terminal creada para $Name (PID $($terminal.Id))."
    }

    return $snapshot
}

function Get-ServiceProcessRecord {
    param([object]$Entry)

    $root = Get-ProcessSnapshot -ProcessId ([int]$Entry.Terminal.ProcessId)
    if (Test-ProcessMatches -Expected $Entry.Terminal -Actual $root) {
        return $root
    }
    return $null
}

function Get-HttpResult {
    param(
        [string]$Uri,
        [int]$TimeoutSeconds = 6
    )

    try {
        $response = Invoke-WebRequest -Uri $Uri -Method Get -TimeoutSec $TimeoutSeconds -UseBasicParsing
        return [pscustomobject]@{
            Success = ([int]$response.StatusCode -ge 200 -and [int]$response.StatusCode -lt 300)
            StatusCode = [int]$response.StatusCode
            Body = [string]$response.Content
            Error = ''
        }
    }
    catch {
        $statusCode = $null
        $body = ''
        $response = $_.Exception.Response
        if ($response) {
            try { $statusCode = [int]$response.StatusCode } catch { }
            try {
                $reader = New-Object System.IO.StreamReader($response.GetResponseStream())
                $body = $reader.ReadToEnd()
                $reader.Dispose()
            }
            catch {
                Write-Verbose "No se pudo leer el detalle HTTP de ${Uri}: $($_.Exception.Message)"
            }
        }
        return [pscustomobject]@{
            Success = $false
            StatusCode = $statusCode
            Body = $body
            Error = $_.Exception.Message
        }
    }
}

function Get-DatabaseFailureText {
    param([object]$Result)

    if (-not [string]::IsNullOrWhiteSpace($Result.Body)) {
        try {
            $payload = $Result.Body | ConvertFrom-Json -ErrorAction Stop
            if ($payload.detail.error) {
                return [string]$payload.detail.error
            }
            if ($payload.detail -is [string]) {
                return [string]$payload.detail
            }
        }
        catch {
            Write-Verbose "El servicio devolvió un detalle de base de datos no JSON."
        }
    }
    if ($Result.StatusCode) {
        return "HTTP $($Result.StatusCode): $($Result.Error)"
    }
    return [string]$Result.Error
}

function Get-OwnerDescription {
    param([int]$ProcessId)

    if (-not $ProcessId) {
        return 'proceso no identificado'
    }
    $process = Get-CimInstance -ClassName Win32_Process -Filter "ProcessId = $ProcessId" -ErrorAction SilentlyContinue
    if ($process) {
        return "$($process.Name) (PID $ProcessId)"
    }
    return "PID $ProcessId"
}

Write-Host 'Gestor de Comercio al por Menor — inicio centralizado' -ForegroundColor Cyan
Write-Host "Raíz detectada: $script:ProjectRoot"
if (-not (Test-Path -LiteralPath $script:ProjectRoot)) {
    throw 'No se encontró la raíz del proyecto.'
}

$script:PowerShellHostPath = Get-PowerShellHostPath
if (-not $script:PowerShellHostPath) {
    throw 'No se encontró powershell.exe ni pwsh.exe para abrir las terminales de servicio.'
}

if (Test-Path -LiteralPath $script:StatePath) {
    try {
        $oldState = Get-Content -LiteralPath $script:StatePath -Raw | ConvertFrom-Json -ErrorAction Stop
        if ([string]$oldState.ProjectRoot -ine $script:ProjectRoot) {
            throw 'El archivo de estado pertenece a otra raíz de proyecto.'
        }
        $script:StateServices = @($oldState.Services)
    }
    catch {
        throw "No se pudo leer el registro de procesos; no se iniciará nada para evitar perder su rastreo. $($_.Exception.Message)"
    }
}

$pythonReady = Test-Path -LiteralPath $script:PythonPath
if (-not $pythonReady) {
    Write-Host "Backend omitido: no existe $script:PythonPath" -ForegroundColor Yellow
    Write-Host 'Crea backend\.venv e instala backend\requirements.txt (ver README).'
}
$uvicornReady = $false
if ($pythonReady) {
    $uvicornOutput = & $script:PythonPath -m uvicorn --version 2>&1
    $uvicornReady = ($LASTEXITCODE -eq 0)
    if (-not $uvicornReady) {
        Write-Host 'Backend omitido: uvicorn no está instalado en backend\.venv.' -ForegroundColor Red
        foreach ($line in $uvicornOutput) { Write-Host $line }
    }
}

$frontendReady = Test-Path -LiteralPath (Join-Path $script:FrontendPath 'node_modules\vite\bin\vite.js')
$npmCommand = Get-Command npm.cmd -ErrorAction SilentlyContinue
if (-not $npmCommand) {
    Write-Host 'No se encontró npm.cmd; el frontend no se podrá iniciar.' -ForegroundColor Red
    $frontendReady = $false
}
if (-not $frontendReady) {
    if ($npmCommand) {
        Write-Host 'Faltan node_modules o Vite en frontend.' -ForegroundColor Yellow
    }
    if ($CheckOnly) {
        Write-Host 'Preflight: no se instaló nada. Ejecuta npm install en frontend o inicia sin -CheckOnly para elegir instalar.'
    }
    elseif (-not $npmCommand) {
        Write-Host 'No se encontró npm.cmd; frontend omitido. Instala Node.js/npm y ejecuta npm install.' -ForegroundColor Red
    }
    else {
        $answer = Read-Host '¿Deseas ejecutar npm install en frontend ahora? (S/N)'
        if ($answer -match '^(s|si|sí|y|yes)$') {
            Push-Location $script:FrontendPath
            try {
                try {
                    & $npmCommand.Source install
                    if ($LASTEXITCODE -ne 0) {
                        Write-Host "npm install falló con código $LASTEXITCODE; frontend omitido." -ForegroundColor Red
                    }
                    else {
                        $frontendReady = Test-Path -LiteralPath (Join-Path $script:FrontendPath 'node_modules\vite\bin\vite.js')
                    }
                }
                catch {
                    Write-Host "npm install no se pudo ejecutar: $($_.Exception.Message); frontend omitido." -ForegroundColor Red
                }
            }
            finally {
                Pop-Location
            }
        }
        else {
            Write-Host 'Frontend omitido. Ejecuta npm install en frontend antes de volver a iniciarlo.'
        }
    }
}

$moduleReady = @{}
if ($pythonReady -and $uvicornReady) {
    foreach ($service in $apiServices) {
        $relativeMain = "app\services\$($service.Module.Split('.')[2])\main.py"
        $mainPath = Join-Path $script:BackendPath $relativeMain
        if (-not (Test-Path -LiteralPath $mainPath)) {
            $moduleReady[$service.Module] = $false
            Write-Host "$($service.Name) omitido: no se encontró $mainPath" -ForegroundColor Red
            continue
        }

        $importOutput = @()
        $importExitCode = 1
        try {
            Push-Location $script:BackendPath
            try {
                $importOutput = & $script:PythonPath -c "import importlib; importlib.import_module('$($service.Module.Replace(':app', ''))')" 2>&1
                $importExitCode = $LASTEXITCODE
            }
            finally {
                Pop-Location
            }
        }
        catch {
            Write-Host "$($service.Name) omitido: falló la comprobación del módulo: $($_.Exception.Message)" -ForegroundColor Red
        }

        $moduleReady[$service.Module] = ($importExitCode -eq 0)
        if ($importExitCode -ne 0) {
            Write-Host "$($service.Name) omitido: no se pudo importar $($service.Module)." -ForegroundColor Red
            foreach ($line in $importOutput) { Write-Host $line }
        }
    }
}

$allPorts = @($apiServices | ForEach-Object { $_.Port }) + $frontendService.Port
if ($CheckOnly) {
    Write-Host "`nComprobación de puertos (sin iniciar procesos):" -ForegroundColor Cyan
    foreach ($port in $allPorts) {
        $occupancy = Test-PortOccupancy -Port $port
        if ($occupancy.InUse) {
            $owner = if ($occupancy.OwnerId) { Get-OwnerDescription -ProcessId $occupancy.OwnerId } else { 'proceso no identificado' }
            Write-Host "Puerto $port ocupado por $owner."
        }
        else {
            Write-Host "Puerto $port disponible."
        }
    }
    Write-Host "`nPreflight completado. No se inició ni detuvo ningún proceso."
    return
}

Write-State

$results = @()
foreach ($service in $apiServices) {
    if (-not $pythonReady -or -not $uvicornReady -or -not $moduleReady[$service.Module]) {
        $results += [pscustomobject]@{
            Name = $service.Name; Port = $service.Port; Terminal = 'No iniciada'
            Api = 'No comprobada'; Database = 'No comprobada'; Detail = 'Falta el entorno o el módulo.'
        }
        continue
    }

    $occupancy = Test-PortOccupancy -Port $service.Port
    if ($occupancy.InUse) {
        $owner = Get-OwnerDescription -ProcessId $occupancy.OwnerId
        Write-Host "$($service.Name): puerto $($service.Port) ocupado por $owner; no se iniciará otra instancia." -ForegroundColor Yellow
        $results += [pscustomobject]@{
            Name = $service.Name; Port = $service.Port; Terminal = 'No iniciada'
            Api = 'No comprobada'; Database = 'No comprobada'; Detail = "Puerto ocupado por $owner."
        }
        continue
    }

    $terminal = $null
    $entry = $null
    try {
        $module = $service.Module
        $pythonLiteral = ConvertTo-PowerShellLiteral $script:PythonPath
        $command = "& $pythonLiteral -m uvicorn $module --host 127.0.0.1 --port $($service.Port); if (`$LASTEXITCODE -ne 0) { Write-Host 'Uvicorn terminó con código' `$LASTEXITCODE -ForegroundColor Red }"
        $terminal = Start-VisibleTerminal -Name $service.Name -WorkingDirectory $script:BackendPath `
            -Title "Gestor - $($service.Name) :$($service.Port)" -Command $command
        $entry = [pscustomobject]@{
            Name = $service.Name
            Port = $service.Port
            Terminal = $terminal
            OwnedProcesses = @()
        }
        $script:StateServices += $entry
        Write-State
        Write-Host "$($service.Name): terminal abierta para el puerto $($service.Port)." -ForegroundColor Green
        $results += [pscustomobject]@{
            Name = $service.Name; Port = $service.Port; Terminal = 'Abierta'
            Api = 'Verificando'; Database = 'Pendiente'; Detail = ''
        }
    }
    catch {
        $launchError = $_.Exception.Message
        if ($terminal) {
            Stop-JustStartedTerminal -TerminalSnapshot $terminal
            if ($entry) {
                $script:StateServices = @($script:StateServices | Where-Object {
                    [int]$_.Terminal.ProcessId -ne [int]$terminal.ProcessId
                })
                try { Write-State } catch { Write-Host "No se pudo guardar el registro de procesos: $($_.Exception.Message)" -ForegroundColor Red }
            }
        }
        Write-Host "$($service.Name): no se pudo iniciar: $launchError" -ForegroundColor Red
        $results += [pscustomobject]@{
            Name = $service.Name; Port = $service.Port; Terminal = 'Falló'
            Api = 'No disponible'; Database = 'No comprobada'; Detail = $launchError
        }
    }
}

if ($frontendReady) {
    $occupancy = Test-PortOccupancy -Port $frontendService.Port
    if ($occupancy.InUse) {
        $owner = Get-OwnerDescription -ProcessId $occupancy.OwnerId
        Write-Host "Frontend: puerto $($frontendService.Port) ocupado por $owner; no se iniciará otra instancia." -ForegroundColor Yellow
        $results += [pscustomobject]@{
            Name = 'Frontend'; Port = $frontendService.Port; Terminal = 'No iniciada'
            Api = 'No comprobada'; Database = 'No aplica'; Detail = "Puerto ocupado por $owner."
        }
    }
    else {
        $terminal = $null
        $entry = $null
        try {
            $npmLiteral = ConvertTo-PowerShellLiteral $npmCommand.Source
            $command = "& $npmLiteral run dev -- --host 127.0.0.1 --port 5173 --strictPort; if (`$LASTEXITCODE -ne 0) { Write-Host 'npm run dev terminó con código' `$LASTEXITCODE -ForegroundColor Red }"
            $terminal = Start-VisibleTerminal -Name 'Frontend' -WorkingDirectory $script:FrontendPath `
                -Title 'Gestor - Frontend :5173' -Command $command
            $entry = [pscustomobject]@{
                Name = 'Frontend'
                Port = 5173
                Terminal = $terminal
                OwnedProcesses = @()
            }
            $script:StateServices += $entry
            Write-State
            Write-Host 'Frontend: terminal abierta para el puerto 5173.' -ForegroundColor Green
            $results += [pscustomobject]@{
                Name = 'Frontend'; Port = 5173; Terminal = 'Abierta'
                Api = 'Verificando'; Database = 'No aplica'; Detail = ''
            }
        }
        catch {
            $launchError = $_.Exception.Message
            if ($terminal) {
                Stop-JustStartedTerminal -TerminalSnapshot $terminal
                if ($entry) {
                    $script:StateServices = @($script:StateServices | Where-Object {
                        [int]$_.Terminal.ProcessId -ne [int]$terminal.ProcessId
                    })
                    try { Write-State } catch { Write-Host "No se pudo guardar el registro de procesos: $($_.Exception.Message)" -ForegroundColor Red }
                }
            }
            Write-Host "Frontend: no se pudo iniciar: $launchError" -ForegroundColor Red
            $results += [pscustomobject]@{
                Name = 'Frontend'; Port = 5173; Terminal = 'Falló'
                Api = 'No disponible'; Database = 'No aplica'; Detail = $launchError
            }
        }
    }
}
else {
    $results += [pscustomobject]@{
        Name = 'Frontend'; Port = 5173; Terminal = 'No iniciada'
        Api = 'No disponible'; Database = 'No aplica'; Detail = 'Instala las dependencias en frontend.'
    }
}

Write-Host "`nEsperando 4 segundos para comprobar procesos y servicios..." -ForegroundColor Cyan
Start-Sleep -Seconds 4

foreach ($entry in $script:StateServices) {
    if (Get-ServiceProcessRecord -Entry $entry) {
        $tree = @(Get-ProcessTree -RootProcessId ([int]$entry.Terminal.ProcessId))
        $entry.OwnedProcesses = @($tree | Where-Object { $_.ProcessId -ne [int]$entry.Terminal.ProcessId } |
            ForEach-Object {
                [pscustomobject]@{
                    ProcessId = $_.ProcessId
                    ParentProcessId = $_.ParentProcessId
                    CreationTicks = $_.CreationTicks
                    ExecutablePath = $_.ExecutablePath
                    CommandLine = $_.CommandLine
                    Depth = $_.Depth
                }
            })
    }
}
Write-State

foreach ($result in $results) {
    if ($result.Terminal -ne 'Abierta') {
        continue
    }
    $entry = $script:StateServices | Where-Object {
        $_.Name -eq $result.Name -and [int]$_.Port -eq [int]$result.Port
    } | Select-Object -Last 1
    $terminalProcess = Get-ServiceProcessRecord -Entry $entry
    if (-not $terminalProcess) {
        $result.Terminal = 'Terminada'
        $result.Api = 'No disponible'
        $result.Detail = 'La terminal de servicio terminó antes de responder.'
        continue
    }

    $treeIds = @(Get-ProcessTree -RootProcessId ([int]$entry.Terminal.ProcessId) |
        ForEach-Object { [int]$_.ProcessId })
    $ownerId = Get-PortOwnerId -Port ([int]$result.Port)
    if (-not $ownerId -or $treeIds -notcontains [int]$ownerId) {
        $result.Api = 'No disponible'
        $result.Detail = 'El proceso no abrió su puerto; revisa la terminal del servicio.'
        continue
    }

    if ($result.Name -eq 'Frontend') {
        $http = Get-HttpResult -Uri 'http://127.0.0.1:5173/'
        if ($http.Success) {
            $result.Api = 'Disponible'
        }
        else {
            $result.Api = 'No disponible'
            $result.Detail = "HTTP del frontend no respondió: $($http.Error)"
        }
        continue
    }

    $health = Get-HttpResult -Uri "http://127.0.0.1:$($result.Port)/health"
    if (-not $health.Success) {
        $result.Api = 'No disponible'
        $result.Detail = "GET /health falló: $($health.Error)"
        continue
    }
    $result.Api = 'Disponible'

    $database = Get-HttpResult -Uri "http://127.0.0.1:$($result.Port)/health/database"
    if ($database.Success) {
        $result.Database = 'Conectada'
    }
    else {
        $result.Database = 'No disponible'
        $databaseError = Get-DatabaseFailureText -Result $database
        $result.Detail = "La API responde, pero PostgreSQL no: $databaseError"
    }
}

Write-Host "`nResumen de inicio" -ForegroundColor Cyan
foreach ($result in $results) {
    $color = if ($result.Api -eq 'Disponible') { 'Green' } else { 'Yellow' }
    $suffix = ''
    if ($result.Detail) {
        $suffix = ' - ' + [string]$result.Detail
    }
    if ($result.Name -eq 'Frontend') {
        Write-Host ("{0}: puerto {1}; terminal {2}; frontend {3}{4}" -f $result.Name, $result.Port, $result.Terminal, $result.Api, $suffix) -ForegroundColor $color
    }
    else {
        Write-Host ("{0}: puerto {1}; terminal {2}; API {3}; PostgreSQL {4}{5}" -f $result.Name, $result.Port, $result.Terminal, $result.Api, $result.Database, $suffix) -ForegroundColor $color
        Write-Host "  Swagger: http://127.0.0.1:$($result.Port)/docs"
    }
}
Write-Host "`nFrontend: http://127.0.0.1:5173/"
Write-Host 'Para detener únicamente los procesos registrados por este proyecto: .\detener_proyecto.ps1'
Write-Host 'Las APIs responden independientemente de PostgreSQL; revisa las terminales si una API no inició o una base no está disponible.'
