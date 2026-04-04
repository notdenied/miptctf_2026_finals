<?php
/**
 * Resheto — SCP Foundation Containment System
 * Front Controller
 */

session_start();
header('Content-Type: application/json; charset=utf-8');

// Autoload Composer packages (mPDF, Parsedown)
require_once __DIR__ . '/../vendor/autoload.php';

// Core
require_once __DIR__ . '/../src/Database.php';
require_once __DIR__ . '/../src/Router.php';
require_once __DIR__ . '/../src/Session.php';

// Controllers
require_once __DIR__ . '/../src/controllers/AuthController.php';
require_once __DIR__ . '/../src/controllers/AnomalyController.php';
require_once __DIR__ . '/../src/controllers/ReportController.php';
require_once __DIR__ . '/../src/controllers/ResearchController.php';
require_once __DIR__ . '/../src/controllers/IncidentController.php';
require_once __DIR__ . '/../src/controllers/InternalController.php';

$router = new Router();

// ── Auth ────────────────────────────────────────────────────────────────
$router->post('/api/auth/register', [AuthController::class, 'register']);
$router->post('/api/auth/login',    [AuthController::class, 'login']);
$router->get('/api/auth/me',        [AuthController::class, 'me']);
$router->post('/api/auth/logout',   [AuthController::class, 'logout']);

// ── Anomalies ───────────────────────────────────────────────────────────
$router->post('/api/anomalies',         [AnomalyController::class, 'create']);
$router->get('/api/anomalies',          [AnomalyController::class, 'list']);
$router->post('/api/anomalies/search',  [AnomalyController::class, 'search']);
$router->get('/api/anomalies/{id}',     [AnomalyController::class, 'get']);

// ── Reports ─────────────────────────────────────────────────────────────
$router->post('/api/reports',             [ReportController::class, 'create']);
$router->get('/api/reports',              [ReportController::class, 'list']);
$router->get('/api/reports/{uuid}',       [ReportController::class, 'get']);
$router->get('/api/reports/{uuid}/pdf',   [ReportController::class, 'downloadPdf']);

// ── Research ────────────────────────────────────────────────────────────
$router->post('/api/research',        [ResearchController::class, 'submit']);
$router->get('/api/research',         [ResearchController::class, 'list']);
$router->get('/api/research/{uuid}',  [ResearchController::class, 'get']);

// ── Incidents ───────────────────────────────────────────────────────────
$router->post('/api/incidents',        [IncidentController::class, 'create']);
$router->get('/api/incidents',         [IncidentController::class, 'list']);
$router->get('/api/incidents/{uuid}',  [IncidentController::class, 'get']);

// ── Internal
$router->get('/api/internal/health',                      [InternalController::class, 'health']);
$router->get('/api/internal/research/get_anomaly_by_id/{id}', [InternalController::class, 'getAnomalyInfo']);
$router->get('/api/internal/research/pending/{uuid}',     [InternalController::class, 'pendingResearch']);
$router->post('/api/internal/research/{uuid}/complete',   [InternalController::class, 'completeResearch']);
$router->get('/api/internal/research/{uuid}/result',      [InternalController::class, 'getResearchResult']);

// ── /api/internal/blocked
$uri = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);
if (str_starts_with($uri, '/api/internal/blocked')) {
    http_response_code(403);
    $originalPath = substr($uri, strlen('/api/internal/blocked')) ?: '/';
    echo json_encode([
        'error'         => 'BLOCKED',
        'message'       => '[ДОСТУП ЗАПРЕЩЁН] Маршрут засекречен',
        'original_path' => $originalPath,
    ]);
    exit;
}

$router->dispatch();
