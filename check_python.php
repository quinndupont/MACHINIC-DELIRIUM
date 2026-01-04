<?php
/**
 * Check Python installation and required modules
 * Usage: php check_python.php
 */

$python_candidates = [
    __DIR__ . '/venv/bin/python3',
    __DIR__ . '/venv/bin/python',
    '/home/public/venv/bin/python3',
    '/home/public/venv/bin/python',
    '/usr/local/bin/python3.11',
    '/usr/local/bin/python3',
    '/usr/local/bin/python',
    '/usr/bin/python3.11',
    '/usr/bin/python3',
    '/usr/bin/python',
];

echo "Checking Python installations...\n";
echo str_repeat('=', 60) . "\n\n";

$found_working = false;

foreach ($python_candidates as $python_path) {
    if (!file_exists($python_path) && strpos($python_path, '/') === 0) {
        continue; // Skip absolute paths that don't exist
    }
    
    echo "Testing: $python_path\n";
    
    // Check if Python exists and works
    $output = [];
    $return_var = 0;
    @exec("$python_path --version 2>&1", $output, $return_var);
    
    if ($return_var !== 0) {
        echo "  ❌ Not found or not executable\n\n";
        continue;
    }
    
    $version = implode(' ', $output);
    echo "  ✓ Version: $version\n";
    
    // Check for required modules
    $modules = ['faiss', 'sentence_transformers', 'numpy'];
    $missing = [];
    
    foreach ($modules as $module) {
        $output = [];
        $return_var = 0;
        @exec("$python_path -c 'import $module' 2>&1", $output, $return_var);
        if ($return_var !== 0) {
            $missing[] = $module;
        }
    }
    
    if (empty($missing)) {
        echo "  ✅ All required modules installed!\n";
        echo "  🎯 RECOMMENDED: Use this Python in config.php:\n";
        echo "     'PYTHON_PATH' => '$python_path',\n\n";
        $found_working = true;
    } else {
        echo "  ⚠️  Missing modules: " . implode(', ', $missing) . "\n";
        echo "     Install with: $python_path -m pip install " . implode(' ', $missing) . " torch\n\n";
    }
}

if (!$found_working) {
    echo "\n" . str_repeat('=', 60) . "\n";
    echo "No Python installation found with all required modules.\n";
    echo "\nTo fix:\n";
    echo "1. Create a virtual environment:\n";
    echo "   python3 -m venv venv\n";
    echo "2. Activate it:\n";
    echo "   source venv/bin/activate\n";
    echo "3. Install requirements:\n";
    echo "   pip install -r requirements.txt\n";
    echo "4. Update config.php with the venv Python path\n";
}

