<?php
/**
 * Utility functions for PHP version
 */

require_once __DIR__ . '/config.php';

function get_api_key() {
    global $config;
    $api_key = $_SESSION['user_api_key'] ?? $config['OPENAI_API_KEY'];
    if (empty($api_key)) {
        throw new Exception("No API key available. Please provide an API key at login.");
    }
    return $api_key;
}

function get_system_prompt_base() {
    return "You are Gilles Deleuze, co-author of Anti-Oedipus with Felix Guattari. You are teaching this work through simple, intuitive explanations and direct quotations from the book.

CRITICAL: Always respond using \"we\" to refer to yourself and your co-author Guattari, as this work was written collaboratively. Never use \"I\" alone - always use \"we\" when speaking about the work, concepts, or ideas. For example, say \"we wrote\", \"we argue\", \"we propose\", not \"I wrote\", \"I argue\", \"I propose\".

PRIORITIZE SIMPLICITY AND CLARITY: Explain concepts in the simplest, most intuitive way possible. Avoid unnecessary complexity or jargon. Make the ideas accessible and clear.

ALWAYS USE DIRECT QUOTATIONS: When explaining concepts, you MUST include direct quotations from the text. Quote the exact words from Anti-Oedipus, using quotation marks. Do not paraphrase when a direct quote would be clearer. Include chapter numbers and titles with every citation.

You have access to relevant passages from Anti-Oedipus. Use these passages to provide direct quotations that illustrate your explanations. When explaining a concept, start with a simple, intuitive explanation, then support it with direct quotations from the text.

Speak in the voice of Deleuze: philosophical, precise, and engaged with the concepts you developed with Guattari, but always prioritize clarity and direct citation over complexity.";
}

function parse_markdown_chapters() {
    global $config;
    static $chapters_cache = null;
    
    if ($chapters_cache !== null) {
        return $chapters_cache;
    }
    
    $markdown_file = $config['MARKDOWN_FILE'];
    if (!file_exists($markdown_file)) {
        throw new Exception("Markdown file not found: {$markdown_file}");
    }
    
    $content = file_get_contents($markdown_file);
    $lines = explode("\n", $content);
    
    $chapters = [];
    $current_chapter = null;
    $chapter_num = 0;
    $i = 15; // Skip title page
    
    // Find first real chapter (INTRODUCTION)
    $found_first = false;
    while ($i < min(300, count($lines))) {
        if (preg_match('/^## (.+)$/', $lines[$i], $matches)) {
            if ($matches[1] === 'INTRODUCTION') {
                $found_first = true;
                break;
            }
        }
        $i++;
    }
    
    if (!$found_first) {
        $i = 200;
        while ($i < count($lines)) {
            if (preg_match('/^## (.+)$/', $lines[$i])) {
                break;
            }
            $i++;
        }
    }
    
    while ($i < count($lines)) {
        $line = $lines[$i];
        
        if (preg_match('/^## (.+)$/', $line, $matches) && strpos($line, 'Table of Contents') === false) {
            if ($current_chapter !== null && !empty($current_chapter['content'])) {
                $current_chapter['content'] = implode("\n", $current_chapter['content']);
                $chapters[] = $current_chapter;
            }
            
            $chapter_title = $matches[1];
            $chapter_num++;
            $current_chapter = [
                'title' => $chapter_title,
                'slug' => slugify($chapter_title) ?: "chapter-{$chapter_num}",
                'content' => []
            ];
            $i++;
            continue;
        }
        
        if ($current_chapter !== null) {
            $current_chapter['content'][] = $line;
        }
        $i++;
    }
    
    if ($current_chapter !== null && !empty($current_chapter['content'])) {
        $current_chapter['content'] = implode("\n", $current_chapter['content']);
        $chapters[] = $current_chapter;
    }
    
    $chapters_cache = $chapters;
    return $chapters;
}

function slugify($text) {
    $text = strtolower($text);
    $text = preg_replace('/[^\w\s-]/', '', $text);
    $text = preg_replace('/[-\s]+/', '-', $text);
    return trim($text, '-');
}

function build_toc($chapters) {
    $html = '<ul class="toc-list">';
    $html .= '<li><a href="?chapter=0">Title Page</a></li>';
    foreach ($chapters as $idx => $chapter) {
        $num = $idx + 1;
        $html .= '<li><a href="?chapter=' . $num . '">' . htmlspecialchars($chapter['title']) . '</a></li>';
    }
    $html .= '</ul>';
    return $html;
}

function get_title_page() {
    global $config;
    $markdown_file = $config['MARKDOWN_FILE'];
    if (!file_exists($markdown_file)) {
        return "";
    }
    
    $lines = file($markdown_file);
    $title_lines = array_slice($lines, 0, 15);
    return implode('', array_map('rtrim', $title_lines));
}

function markdown_to_html($markdown) {
    // Simple markdown parser - you may want to use a library like Parsedown
    // For now, basic conversion
    $html = $markdown;
    
    // Headers (h2, h3, h4)
    $html = preg_replace('/^## (.+)$/m', '<h2 id="' . slugify('$1') . '">$1</h2>', $html);
    $html = preg_replace('/^### (.+)$/m', '<h3 id="' . slugify('$1') . '">$1</h3>', $html);
    $html = preg_replace('/^#### (.+)$/m', '<h4 id="' . slugify('$1') . '">$1</h4>', $html);
    
    // Bold
    $html = preg_replace('/\*\*(.+?)\*\*/', '<strong>$1</strong>', $html);
    
    // Italic (not bold)
    $html = preg_replace('/(?<!\*)\*([^*]+?)\*(?!\*)/', '<em>$1</em>', $html);
    
    // Code blocks
    $html = preg_replace('/```(\w+)?\n(.*?)```/s', '<pre><code>$2</code></pre>', $html);
    
    // Inline code
    $html = preg_replace('/`(.+?)`/', '<code>$1</code>', $html);
    
    // Links
    $html = preg_replace('/\[([^\]]+)\]\(([^\)]+)\)/', '<a href="$2">$1</a>', $html);
    
    // Split into paragraphs (double newlines)
    $paragraphs = preg_split('/\n\n+/', $html);
    $html = '';
    foreach ($paragraphs as $para) {
        $para = trim($para);
        if (empty($para)) continue;
        // Don't wrap headers or code blocks in <p>
        if (preg_match('/^<(h[1-6]|pre|ul|ol)/', $para)) {
            $html .= $para . "\n";
        } else {
            $html .= '<p>' . nl2br($para) . '</p>' . "\n";
        }
    }
    
    return $html;
}

function render_template($template, $vars = []) {
    extract($vars);
    // Use PHP version if available, otherwise fall back to original
    $php_template = str_replace('.html', '_php.html', $template);
    $template_path = __DIR__ . '/templates/' . $php_template;
    if (!file_exists($template_path)) {
        $template_path = __DIR__ . '/templates/' . $template;
    }
    include $template_path;
}

function is_python_available() {
    global $config;
    $python_path = $config['PYTHON_PATH'];
    $output = [];
    $return_var = 0;
    @exec("{$python_path} --version 2>&1", $output, $return_var);
    return $return_var === 0 && file_exists($config['RAG_SCRIPT']);
}

function call_python_rag($query, $k = 5) {
    global $config;
    $python_path = $config['PYTHON_PATH'];
    $script = $config['RAG_SCRIPT'];
    $api_key = get_api_key();
    
    $query_escaped = escapeshellarg($query);
    $k_escaped = escapeshellarg($k);
    $api_key_escaped = escapeshellarg($api_key);
    
    $command = "{$python_path} {$script} query {$query_escaped} {$k_escaped} {$api_key_escaped} 2>&1";
    $output = shell_exec($command);
    
    if ($output === null) {
        // Fallback to simple search
        return simple_text_search($query, $k);
    }
    
    $result = json_decode($output, true);
    if (json_last_error() !== JSON_ERROR_NONE) {
        return simple_text_search($query, $k);
    }
    
    return $result;
}

function simple_text_search($query, $k = 5) {
    // Fallback: simple keyword-based search
    $chapters = parse_markdown_chapters();
    $results = [];
    $query_terms = explode(' ', strtolower($query));
    
    foreach ($chapters as $idx => $chapter) {
        $chapter_num = $idx + 1;
        $content_lower = strtolower($chapter['content']);
        
        $score = 0;
        foreach ($query_terms as $term) {
            $score += substr_count($content_lower, $term);
        }
        
        if ($score > 0) {
            // Extract a chunk around matches
            $pos = stripos($content_lower, $query_terms[0]);
            if ($pos !== false) {
                $start = max(0, $pos - 200);
                $end = min(strlen($chapter['content']), $pos + strlen($query) + 200);
                $chunk = substr($chapter['content'], $start, $end - $start);
                
                $results[] = [
                    'text' => $chunk,
                    'chapter_num' => $chapter_num,
                    'chapter_title' => $chapter['title'],
                    'subsection' => ''
                ];
            }
        }
    }
    
    // Sort by score and limit
    usort($results, function($a, $b) use ($query_terms) {
        $a_score = 0;
        $b_score = 0;
        $a_text = strtolower($a['text']);
        $b_text = strtolower($b['text']);
        foreach ($query_terms as $term) {
            $a_score += substr_count($a_text, $term);
            $b_score += substr_count($b_text, $term);
        }
        return $b_score <=> $a_score;
    });
    
    return array_slice($results, 0, $k);
}

function call_openai_chat($api_key, $system_prompt, $user_prompt, $max_tokens = 500, $temperature = 0.7) {
    $messages = [
        ['role' => 'system', 'content' => $system_prompt],
        ['role' => 'user', 'content' => $user_prompt]
    ];
    
    $data = [
        'model' => 'gpt-4o',
        'messages' => $messages,
        'max_tokens' => $max_tokens,
        'temperature' => $temperature
    ];
    
    $ch = curl_init('https://api.openai.com/v1/chat/completions');
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($data));
    curl_setopt($ch, CURLOPT_HTTPHEADER, [
        'Content-Type: application/json',
        'Authorization: Bearer ' . $api_key
    ]);
    
    $response = curl_exec($ch);
    $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    
    if ($http_code !== 200) {
        throw new Exception("OpenAI API error: " . $response);
    }
    
    $result = json_decode($response, true);
    return $result['choices'][0]['message']['content'];
}

function call_openai_chat_stream($api_key, $messages, $max_tokens = 2000, $temperature = 0.8) {
    $data = [
        'model' => 'gpt-4o',
        'messages' => $messages,
        'max_tokens' => $max_tokens,
        'temperature' => $temperature,
        'stream' => true
    ];
    
    $ch = curl_init('https://api.openai.com/v1/chat/completions');
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, false);
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($data));
    curl_setopt($ch, CURLOPT_HTTPHEADER, [
        'Content-Type: application/json',
        'Authorization: Bearer ' . $api_key
    ]);
    curl_setopt($ch, CURLOPT_WRITEFUNCTION, function($ch, $data) {
        echo $data;
        flush();
        return strlen($data);
    });
    
    curl_exec($ch);
    curl_close($ch);
}

