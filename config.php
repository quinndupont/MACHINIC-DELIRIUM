<?php
/**
 * Configuration file for PHP version
 * Copy this to config.php and set your values
 */

// Load .env file if it exists
function load_dotenv($filepath) {
    if (!file_exists($filepath) || !is_readable($filepath)) {
        return;
    }
    
    $lines = @file($filepath, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);
    if ($lines === false) {
        // File couldn't be read (permission denied, etc.)
        return;
    }
    
    foreach ($lines as $line) {
        // Skip comments
        if (strpos(trim($line), '#') === 0) {
            continue;
        }
        
        // Parse KEY=VALUE format
        if (strpos($line, '=') !== false) {
            list($key, $value) = explode('=', $line, 2);
            $key = trim($key);
            $value = trim($value);
            
            // Remove quotes if present
            if ((substr($value, 0, 1) === '"' && substr($value, -1) === '"') ||
                (substr($value, 0, 1) === "'" && substr($value, -1) === "'")) {
                $value = substr($value, 1, -1);
            }
            
            // Only set if not already in environment
            if (!getenv($key)) {
                putenv("$key=$value");
            }
        }
    }
}

// Load .env file
$env_file = __DIR__ . '/.env';
if (file_exists($env_file)) {
    load_dotenv($env_file);
}

// Load from environment or set defaults
$config = [
    'OPENAI_API_KEY' => getenv('OPENAI_API_KEY') ?: '',
    'APP_PASSWORD' => getenv('APP_PASSWORD') ?: '',
    'FLASK_SECRET_KEY' => getenv('FLASK_SECRET_KEY') ?: 'dev-secret-key-change-in-production',
    'MARKDOWN_FILE' => __DIR__ . '/Anti-Oedipus.md',
    'PYTHON_PATH' => '/usr/local/bin/python', // Default system Python - update to your server's path (use: which python)
    'EMBED_SCRIPT' => __DIR__ . '/embed_query.py', // Convert query to vector
    'SEARCH_SCRIPT' => __DIR__ . '/search_faiss.py', // Search FAISS index
    'HYBRID_SCRIPT' => __DIR__ . '/search_hybrid.py', // Hybrid semantic + keyword search
    'FAISS_INDEX' => __DIR__ . '/faiss_index.bin',
    'CHUNKS_JSON' => __DIR__ . '/chunks.json' // Text chunks and metadata
];

// Set session config
ini_set('session.cookie_httponly', '1');
ini_set('session.cookie_samesite', 'Lax');
ini_set('session.gc_maxlifetime', '86400'); // 24 hours

