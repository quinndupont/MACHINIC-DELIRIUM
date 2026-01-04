<?php
/**
 * Define API endpoint
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

// api_define function - moved here from index.php
function api_define($data) {
    $term = $data['term'] ?? '';
    $context = $data['context'] ?? '';
    
    if (empty($term)) {
        http_response_code(400);
        header('Content-Type: application/json');
        echo json_encode(['error' => 'Term is required']);
        return;
    }
    
    // Check if Python RAG is available
    if (is_python_available()) {
        $rag_results = call_python_rag($term . ' ' . $context, 15); // Increased from 6 to 15 for better coverage
    } else {
        // Fallback to simple text search
        $rag_results = simple_text_search($term . ' ' . $context, 6);
    }
    
    // Log if no results found
    if (empty($rag_results)) {
        error_log("No RAG results found for define query: " . $term);
    }
    
    // Build context from results
    $context_parts = [];
    foreach ($rag_results as $result) {
        if (empty($result['text'])) {
            continue; // Skip empty results
        }
        
        $chapter_info = "Chapter {$result['chapter_num']}: {$result['chapter_title']}";
        if (!empty($result['subsection'])) {
            $chapter_info .= " - {$result['subsection']}";
        }
        $context_parts[] = "[{$chapter_info}]\n{$result['text']}\n";
    }
    
    $context_text = implode("\n---\n\n", $context_parts);
    
    // If no context found, add a note
    if (empty($context_text)) {
        $context_text = "[Note: No relevant passages found in the text for this term.]";
        error_log("Warning: Empty context text for define query: " . $term);
    }
    
    // Call OpenAI
    try {
        $api_key = get_api_key();
        $system_prompt = get_system_prompt_base() . "\n\nYou have access to relevant passages from Anti-Oedipus that mention the term. When citing the text, always include the chapter number and title. Here are the relevant passages:\n\n{$context_text}\n\nProvide a comprehensive definition based on how this term is used in these passages.";
        $user_prompt = "Define the term '{$term}' as it is used in Anti-Oedipus.";
        if ($context) {
            $user_prompt .= " The user has selected this text for context: \"{$context}\".";
        }
        
        $response = call_openai_chat($api_key, $system_prompt, $user_prompt, 500, 0.7);
        
        header('Content-Type: application/json');
        echo json_encode(['definition' => $response]);
    } catch (Exception $e) {
        error_log("Define API error: " . $e->getMessage());
        http_response_code(500);
        header('Content-Type: application/json');
        echo json_encode(['error' => 'Failed to get definition: ' . $e->getMessage()]);
    }
}

api_define($input);

