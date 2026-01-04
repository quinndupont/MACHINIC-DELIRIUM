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
    echo "  - Python path: " . $config['PYTHON_PATH'] . " (" . (file_exists($config['PYTHON_PATH']) ? 'EXISTS' : 'MISSING') . ")\n";
    
    // Try to find Python automatically - check for venv first, then system Python
    $project_dir = __DIR__;
    $python_candidates = [
        $project_dir . '/venv/bin/python3',  // Local venv
        $project_dir . '/venv/bin/python',   // Local venv (alternative)
        '/home/public/venv/bin/python3',      // Common venv location
        '/home/public/venv/bin/python',       // Common venv location (alternative)
        '/usr/local/bin/python3.11',
        '/usr/local/bin/python3',
        '/usr/local/bin/python',
        '/usr/bin/python3.11',
        '/usr/bin/python3',
        '/usr/bin/python',
        'python3.11',
        'python3',
        'python'
    ];
    $found_python = null;
    foreach ($python_candidates as $candidate) {
        $output = [];
        $return_var = 0;
        // Test if Python can actually run and has required modules
        @exec("$candidate -c 'import faiss, sentence_transformers; print(\"OK\")' 2>&1", $output, $return_var);
        if ($return_var === 0 && implode('', $output) === 'OK') {
            $found_python = $candidate;
            echo "  - Found working Python with required modules at: $candidate\n";
            break;
        }
    }
    
    // If no Python with modules found, try to find any working Python
    if (!$found_python) {
        foreach ($python_candidates as $candidate) {
            $output = [];
            $return_var = 0;
            @exec("$candidate -c 'import sys; print(\"OK\")' 2>&1", $output, $return_var);
            if ($return_var === 0 && implode('', $output) === 'OK') {
                $found_python = $candidate;
                echo "  - Found Python (but missing modules) at: $candidate\n";
                echo "    Missing modules: faiss, sentence_transformers\n";
                echo "    Install with: $candidate -m pip install faiss-cpu sentence-transformers torch\n";
                break;
            }
        }
    }
    
    echo "  - FAISS index: " . $config['FAISS_INDEX'] . " (" . (file_exists($config['FAISS_INDEX']) ? 'EXISTS' : 'MISSING') . ")\n";
    echo "  - Chunks JSON: " . $config['CHUNKS_JSON'] . " (" . (file_exists($config['CHUNKS_JSON']) ? 'EXISTS' : 'MISSING') . ")\n";
    echo "  - Hybrid script: " . $config['HYBRID_SCRIPT'] . " (" . (file_exists($config['HYBRID_SCRIPT']) ? 'EXISTS' : 'MISSING') . ")\n";
    
    if ($found_python) {
        echo "\nSUGGESTION: Update config.php with:\n";
        echo "  'PYTHON_PATH' => '$found_python',\n";
    }
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

