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
    header('Content-Type: application/json');
    echo json_encode(['error' => 'Method not allowed']);
    exit;
}

if (!isset($_SESSION['logged_in'])) {
    http_response_code(401);
    header('Content-Type: application/json');
    echo json_encode(['error' => 'Not authenticated']);
    exit;
}

$input = json_decode(file_get_contents('php://input'), true);

// api_search function - moved here from index.php
function api_search($data) {
    $query = trim($data['query'] ?? '');
    
    if (empty($query)) {
        header('Content-Type: application/json');
        echo json_encode(['results' => [], 'total' => 0]);
        return;
    }
    
    try {
        $chapters = parse_markdown_chapters();
        $results = [];
        
        foreach ($chapters as $idx => $chapter) {
            $chapter_num = $idx + 1;
            $content = $chapter['content'];
            
            // Case-insensitive search
            $pattern = '/' . preg_quote($query, '/') . '/i';
            preg_match_all($pattern, $content, $matches, PREG_OFFSET_CAPTURE);
            
            foreach ($matches[0] as $match) {
                $start_pos = $match[1];
                $end_pos = $start_pos + strlen($match[0]);
                
                // Get context
                $context_start = max(0, $start_pos - 100);
                $context_end = min(strlen($content), $end_pos + 100);
                $context = substr($content, $context_start, $context_end - $context_start);
                
                // Count lines
                $lines_before = substr_count(substr($content, 0, $start_pos), "\n");
                
                $results[] = [
                    'chapter_num' => $chapter_num,
                    'chapter_title' => $chapter['title'],
                    'chapter_slug' => $chapter['slug'],
                    'match_start' => $start_pos,
                    'match_end' => $end_pos,
                    'context' => $context,
                    'line_number' => $lines_before,
                    'match_text' => $match[0]
                ];
            }
        }
        
        header('Content-Type: application/json');
        echo json_encode([
            'results' => $results,
            'total' => count($results),
            'query' => $query
        ]);
    } catch (Exception $e) {
        error_log("Search API error: " . $e->getMessage());
        http_response_code(500);
        header('Content-Type: application/json');
        echo json_encode([
            'error' => $e->getMessage(),
            'results' => [],
            'total' => 0
        ]);
    }
}

api_search($input);

