<?php
/**
 * Test script for RAG search
 * Usage: php test_rag.php "query text"
 */

require_once __DIR__ . '/config.php';
require_once __DIR__ . '/php_utils.php';

$query = $argv[1] ?? 'Jean-Francois Lyotard';

echo "Testing RAG search for: '$query'\n";
echo str_repeat('=', 60) . "\n\n";

// Check if Python is available
if (!is_python_available()) {
    echo "ERROR: Python RAG not available!\n";
    echo "Check:\n";
    echo "  - Python path: " . $config['PYTHON_PATH'] . "\n";
    echo "  - FAISS index: " . $config['FAISS_INDEX'] . " (" . (file_exists($config['FAISS_INDEX']) ? 'EXISTS' : 'MISSING') . ")\n";
    echo "  - Chunks JSON: " . $config['CHUNKS_JSON'] . " (" . (file_exists($config['CHUNKS_JSON']) ? 'EXISTS' : 'MISSING') . ")\n";
    echo "  - Hybrid script: " . $config['HYBRID_SCRIPT'] . " (" . (file_exists($config['HYBRID_SCRIPT']) ? 'EXISTS' : 'MISSING') . ")\n";
    exit(1);
}

echo "Python RAG is available.\n\n";

// Test the search
$results = call_python_rag($query, 10);

echo "Found " . count($results) . " results:\n\n";

foreach ($results as $i => $result) {
    $exact = isset($result['exact_match']) && $result['exact_match'] ? ' [EXACT MATCH]' : '';
    echo ($i + 1) . ". Chapter {$result['chapter_num']}: {$result['chapter_title']}{$exact}\n";
    echo "   Score: " . ($result['score'] ?? 'N/A') . "\n";
    echo "   Text: " . substr($result['text'], 0, 200) . "...\n\n";
}

// Check if exact matches were found
$exact_count = 0;
foreach ($results as $result) {
    if (isset($result['exact_match']) && $result['exact_match']) {
        $exact_count++;
    }
}

echo "\n" . str_repeat('=', 60) . "\n";
echo "Summary: {$exact_count} exact match(es) found\n";

