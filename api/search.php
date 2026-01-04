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

