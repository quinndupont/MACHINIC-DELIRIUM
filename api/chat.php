<?php
/**
 * Chat API endpoint
 */

// Load configuration FIRST (before session_start) so session ini settings can be set
require_once __DIR__ . '/../config.php';
require_once __DIR__ . '/../php_utils.php';

// Now start session (after config has set ini settings)
session_start();

// Debug: Check if this file is being accessed
error_log("Chat API accessed: " . $_SERVER['REQUEST_METHOD'] . " " . $_SERVER['REQUEST_URI']);

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    header('Content-Type: application/json');
    echo json_encode(['error' => 'Method not allowed', 'method' => $_SERVER['REQUEST_METHOD']]);
    exit;
}

if (!isset($_SESSION['logged_in'])) {
    http_response_code(401);
    header('Content-Type: application/json');
    echo json_encode(['error' => 'Not authenticated']);
    exit;
}

$input = json_decode(file_get_contents('php://input'), true);

// api_chat function - moved here from index.php
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
        $rag_results = call_python_rag($message, 20); // Increased from 8 to 20 for better coverage
    } else {
        $rag_results = simple_text_search($message, 20);
    }
    
    // Log if no results found
    if (empty($rag_results)) {
        error_log("No RAG results found for query: " . $message);
    }
    
    // Build context
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
        $context_text = "[Note: No relevant passages found in the text for this query.]";
        error_log("Warning: Empty context text for query: " . $message);
    }
    
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
    call_openai_chat_stream($api_key, $messages, 2000, 0.8);
}

api_chat($input);

