<?php
/**
 * Configuration file for PHP version
 * Copy this to config.php and set your values
 */

// Load from environment or set defaults
$config = [
    'OPENAI_API_KEY' => getenv('OPENAI_API_KEY') ?: '',
    'APP_PASSWORD' => getenv('APP_PASSWORD') ?: '',
    'FLASK_SECRET_KEY' => getenv('FLASK_SECRET_KEY') ?: 'dev-secret-key-change-in-production',
    'MARKDOWN_FILE' => __DIR__ . '/Anti-Oedipus.md',
    'PYTHON_PATH' => '/usr/bin/python3', // Try: which python3 on server
    'RAG_SCRIPT' => __DIR__ . '/rag_api.py'
];

// Set session config
ini_set('session.cookie_httponly', '1');
ini_set('session.cookie_samesite', 'Lax');
ini_set('session.gc_maxlifetime', '86400'); // 24 hours

