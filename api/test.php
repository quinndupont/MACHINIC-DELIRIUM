<?php
/**
 * Simple test endpoint to verify API routing works
 */
header('Content-Type: application/json');
echo json_encode([
    'status' => 'ok',
    'message' => 'API endpoint is accessible',
    'method' => $_SERVER['REQUEST_METHOD'],
    'uri' => $_SERVER['REQUEST_URI'],
    'path' => parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH)
]);

