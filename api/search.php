<?php
/**
 * Search API endpoint
 */

// Load configuration FIRST (before session_start) so session ini settings can be set
require_once __DIR__ . '/../config.php';
require_once __DIR__ . '/../php_utils.php';

// Now start session (after config has set ini settings)
session_start();

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['error' => 'Method not allowed']);
    exit;
}

if (!isset($_SESSION['logged_in'])) {
    http_response_code(401);
    echo json_encode(['error' => 'Not authenticated']);
    exit;
}

$input = json_decode(file_get_contents('php://input'), true);
api_search($input);

