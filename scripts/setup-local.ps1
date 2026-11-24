$ErrorActionPreference = "Stop"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " DABERUSA - Instalador y Arranque Local (Docker Compose)" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Error "Git no está instalado. Instálalo desde https://git-scm.com/"
    exit 1
}
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Error "Docker Desktop no está instalado o no está en el PATH."
    exit 1
}

docker compose version | Out-Null

if (-not (Test-Path ".env")) {
    Write-Host "[1/4] Creando archivo .env desde .env.example..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
} else {
    Write-Host "[1/4] Archivo .env ya existe (se conserva configuración actual)." -ForegroundColor Green
}

Write-Host "[2/4] Construyendo e iniciando los 4 contenedores (db, backend, scraper, frontend)..." -ForegroundColor Yellow
docker compose up --build -d

Write-Host "[3/4] Esperando disponibilidad del backend..." -ForegroundColor Yellow
$ready = $false
for ($i = 0; $i -lt 30; $i++) {
    try {
        $resp = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 2
        if ($resp.StatusCode -eq 200) {
            $ready = $true
            break
        }
    } catch {
        Start-Sleep -Seconds 2
    }
}

Write-Host "[4/4] Estado actual de los contenedores:" -ForegroundColor Yellow
docker compose ps

Write-Host ""
if ($ready) {
    Write-Host "Listo! Servicios disponibles:" -ForegroundColor Green
} else {
    Write-Host "Contenedores iniciados (revisa logs con 'docker compose logs -f'):" -ForegroundColor Yellow
}
Write-Host "  - Portal Web Angular : http://localhost:8080"
Write-Host "  - API Swagger        : http://localhost:8000/docs"
Write-Host "  - Scraper Health     : http://localhost:8001/health"
Write-Host ""
Write-Host "Accesos demo: admin@daberusa.cl / Admin123! | cobranza@daberusa.cl / Cobranza123! | vendedor@daberusa.cl / Vendedor123!"
