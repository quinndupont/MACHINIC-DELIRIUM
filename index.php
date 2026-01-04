<?php
/**
 * PHP version for NearlyFreeSpeech hosting
 * Main entry point - handles routing and sessions
 */

// Enable error reporting for debugging (remove in production)
error_reporting(E_ALL);
ini_set('display_errors', 0); // Don't display errors, but log them
ini_set('log_errors', 1);

// Load configuration FIRST (before session_start) so session ini settings can be set
try {
    require_once __DIR__ . '/config.php';
    require_once __DIR__ . '/php_utils.php';
} catch (Exception $e) {
    error_log("Error loading config: " . $e->getMessage());
    http_response_code(500);
    die("Configuration error. Please check server logs.");
}

// Now start session (after config has set ini settings)
session_start();

// Check if user is logged in (except for login page)
$current_page = basename($_SERVER['PHP_SELF']);
$allowed_pages = ['login.php', 'test.php', 'ui-test.php'];

if (!in_array($current_page, $allowed_pages) && !isset($_SESSION['logged_in'])) {
    header('Location: login.php');
    exit;
}

// Check if this is an API request (fallback if .htaccess rewrite doesn't work)
$request_uri = $_SERVER['REQUEST_URI'];
$path_info = parse_url($request_uri, PHP_URL_PATH);

// Handle API routes directly
if (preg_match('#^/api/(chat|define|search)$#', $path_info, $matches)) {
    $endpoint = $matches[1];
    $api_file = __DIR__ . '/api/' . $endpoint . '.php';
    if (file_exists($api_file)) {
        require $api_file;
        exit;
    }
}

// Check if this is an API request via query parameter
if (isset($_GET['action']) && $_GET['action'] === 'api') {
    handle_api();
    exit;
}

// Check if this is a login request
if (isset($_GET['action']) && $_GET['action'] === 'login') {
    header('Location: login.php');
    exit;
}

// Default: render main page
render_index();

function render_index() {
    global $config;
    
    // Parse markdown chapters
    $chapters = parse_markdown_chapters();
    $toc = build_toc($chapters);
    
    // Get current chapter
    $chapter_num = isset($_GET['chapter']) ? (int)$_GET['chapter'] : 0;
    
    if ($chapter_num == 0) {
        // Title page
        $title_page = get_title_page();
        render_template('index.html', [
            'is_title_page' => true,
            'title_page_content' => $title_page,
            'toc' => $toc,
            'chapter' => 0,
            'total_chapters' => count($chapters),
            'chapter_title' => 'Title Page',
            'prev_chapter' => null,
            'next_chapter' => count($chapters) > 0 ? 1 : null,
            'content' => '' // Not used for title page
        ]);
    } else {
        // Regular chapter
        if ($chapter_num < 1 || $chapter_num > count($chapters)) {
            $chapter_num = 1;
        }
        
        $chapter = $chapters[$chapter_num - 1];
        $html_content = markdown_to_html($chapter['content']);
        
        render_template('index.html', [
            'is_title_page' => false,
            'content' => $html_content,
            'toc' => $toc,
            'chapter' => $chapter_num,
            'total_chapters' => count($chapters),
            'chapter_title' => $chapter['title'],
            'prev_chapter' => $chapter_num > 1 ? $chapter_num - 1 : 0,
            'next_chapter' => $chapter_num < count($chapters) ? $chapter_num + 1 : null
        ]);
    }
}

function handle_api() {
    // Support both /api/define.php and ?action=api&endpoint=define
    $request_uri = $_SERVER['REQUEST_URI'];
    $path_info = parse_url($request_uri, PHP_URL_PATH);
    
    // Check if it's a direct API file request (e.g., /api/define.php)
    if (preg_match('#/api/(\w+)\.php#', $path_info, $matches)) {
        $endpoint = $matches[1];
    } else {
        // Check query parameter
        $endpoint = $_GET['endpoint'] ?? '';
    }
    
    $method = $_SERVER['REQUEST_METHOD'];
    
    header('Content-Type: application/json');
    
    if ($method !== 'POST') {
        http_response_code(405);
        echo json_encode(['error' => 'Method not allowed']);
        exit;
    }
    
    $input = json_decode(file_get_contents('php://input'), true);
    
    switch ($endpoint) {
        case 'define':
            api_define($input);
            break;
        case 'chat':
            api_chat($input);
            break;
        case 'search':
            api_search($input);
            break;
        default:
            http_response_code(404);
            echo json_encode(['error' => 'Endpoint not found']);
            break;
    }
}

function api_define($data) {
    $term = $data['term'] ?? '';
    $context = $data['context'] ?? '';
    
    if (empty($term)) {
        http_response_code(400);
        echo json_encode(['error' => 'Term is required']);
        return;
    }
    
    // Check if Python RAG is available
    if (is_python_available()) {
        $rag_results = call_python_rag($term . ' ' . $context, 30); // Increased for better context
    } else {
        // Fallback to simple text search
        $rag_results = simple_text_search($term . ' ' . $context, 30);
    }
    
    // Build context from results
    $context_parts = [];
    foreach ($rag_results as $result) {
        $chapter_info = "Chapter {$result['chapter_num']}: {$result['chapter_title']}";
        if (!empty($result['subsection'])) {
            $chapter_info .= " - {$result['subsection']}";
        }
        $context_parts[] = "[{$chapter_info}]\n{$result['text']}\n";
    }
    
    $context_text = implode("\n---\n\n", $context_parts);
    
    // Call OpenAI
    $api_key = get_api_key();
    $system_prompt = get_system_prompt_base() . "\n\nYou have access to relevant passages from Anti-Oedipus that mention the term. When citing the text, always include the chapter number and title. Here are the relevant passages:\n\n{$context_text}\n\nProvide a comprehensive definition based on how this term is used in these passages.";
    $user_prompt = "Define the term '{$term}' as it is used in Anti-Oedipus.";
    if ($context) {
        $user_prompt .= " The user has selected this text for context: \"{$context}\".";
    }
    
    $response = call_openai_chat($api_key, $system_prompt, $user_prompt, 1000, 0.7); // Increased max_tokens
    
    echo json_encode(['definition' => $response]);
}

function api_chat($data) {
    $message = $data['message'] ?? '';
    $history = $data['history'] ?? [];
    
    if (empty($message)) {
        http_response_code(400);
        echo json_encode(['error' => 'Message is required']);
        return;
    }
    
    // Check if Python RAG is available
    if (is_python_available()) {
        $rag_results = call_python_rag($message, 40); // Increased for better context
    } else {
        $rag_results = simple_text_search($message, 40);
    }
    
    // Build context
    $context_parts = [];
    foreach ($rag_results as $result) {
        $chapter_info = "Chapter {$result['chapter_num']}: {$result['chapter_title']}";
        if (!empty($result['subsection'])) {
            $chapter_info .= " - {$result['subsection']}";
        }
        $context_parts[] = "[{$chapter_info}]\n{$result['text']}\n";
    }
    
    $context_text = implode("\n---\n\n", $context_parts);
    
    $api_key = get_api_key();
    $system_prompt = get_system_prompt_base() . "\n\nYou have access to relevant passages from Anti-Oedipus. When citing the text, always include the chapter number and title. Here are the relevant passages:\n\n{$context_text}\n\nWhen answering questions, cite specific chapters and passages. If the user asks about something not covered in the provided passages, acknowledge this and provide your best answer based on your understanding of the work you wrote with Guattari.";
    
    // Build messages array
    $messages = [['role' => 'system', 'content' => $system_prompt]];
    foreach ($history as $msg) {
        if ($msg['role'] !== 'system') {
            $messages[] = $msg;
        }
    }
    $messages[] = ['role' => 'user', 'content' => $message];
    
    // Stream response
    header('Content-Type: text/plain');
    call_openai_chat_stream($api_key, $messages, 4000, 0.8); // Increased max_tokens
}

function api_search($data) {
    $query = trim($data['query'] ?? '');
    
    if (empty($query)) {
        echo json_encode(['results' => [], 'total' => 0]);
        return;
    }
    
    $chapters = parse_markdown_chapters();
    $results = [];
    
    // Normalize query
    $query_original = $query;
    $query_lower = mb_strtolower($query);
    
    foreach ($chapters as $idx => $chapter) {
        $chapter_num = $idx + 1;
        $content = $chapter['content'];
        $content_lower = mb_strtolower($content);
        
        // Try exact phrase match first (case-sensitive)
        $exact_matches = [];
        $offset = 0;
        while (($pos = mb_strpos($content, $query_original, $offset)) !== false) {
            $exact_matches[] = [
                'start' => $pos,
                'end' => $pos + mb_strlen($query_original),
                'text' => mb_substr($content, $pos, mb_strlen($query_original)),
                'exact' => true
            ];
            $offset = $pos + 1;
        }
        
        // Try case-insensitive exact phrase match
        $offset = 0;
        while (($pos = mb_strpos($content_lower, $query_lower, $offset)) !== false) {
            // Check if this match was already found in case-sensitive search
            $already_found = false;
            foreach ($exact_matches as $em) {
                if ($em['start'] === $pos) {
                    $already_found = true;
                    break;
                }
            }
            if (!$already_found) {
                $exact_matches[] = [
                    'start' => $pos,
                    'end' => $pos + mb_strlen($query_lower),
                    'text' => mb_substr($content, $pos, mb_strlen($query_lower)),
                    'exact' => false
                ];
            }
            $offset = $pos + 1;
        }
        
        // Process matches
        foreach ($exact_matches as $match) {
            $start_pos = $match['start'];
            $end_pos = $match['end'];
            
            // Get context (200 chars before/after)
            $context_start = max(0, $start_pos - 200);
            $context_end = min(mb_strlen($content), $end_pos + 200);
            $context = mb_substr($content, $context_start, $context_end - $context_start);
            
            // Count lines
            $lines_before = mb_substr_count(mb_substr($content, 0, $start_pos), "\n");
            
            $results[] = [
                'chapter_num' => $chapter_num,
                'chapter_title' => $chapter['title'],
                'chapter_slug' => $chapter['slug'] ?? '',
                'match_start' => $start_pos,
                'match_end' => $end_pos,
                'context' => $context,
                'line_number' => $lines_before,
                'match_text' => $match['text'],
                'exact_match' => $match['exact']
            ];
        }
    }
    
    // Sort results: exact matches first, then by chapter number
    usort($results, function($a, $b) {
        // Exact matches first
        if (isset($a['exact_match']) && isset($b['exact_match'])) {
            if ($a['exact_match'] && !$b['exact_match']) return -1;
            if (!$a['exact_match'] && $b['exact_match']) return 1;
        }
        // Then by chapter number
        if ($a['chapter_num'] !== $b['chapter_num']) {
            return $a['chapter_num'] - $b['chapter_num'];
        }
        // Then by position in chapter
        return $a['match_start'] - $b['match_start'];
    });
    
    echo json_encode([
        'results' => $results,
        'total' => count($results),
        'query' => $query
    ]);
}

