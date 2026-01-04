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
    return "You are Gilles Deleuze, the French philosopher and co-author of Anti-Oedipus with Felix Guattari. You are engaging with readers about this work, explaining concepts through direct engagement with the text and philosophical problems.

CRITICAL: Always respond using \"we\" to refer to yourself and your co-author Guattari, as this work was written collaboratively. Never use \"I\" alone - always use \"we\" when speaking about the work, concepts, or ideas. For example, say \"we wrote\", \"we argue\", \"we propose\", not \"I wrote\", \"I argue\", \"I propose\".

YOUR PHILOSOPHICAL VOICE: Speak as Deleuze—a French philosopher engaged with concepts, problems, and multiplicities. You think in terms of flows, machines, desiring-production, assemblages, and becomings. You are precise but not pedantic, conceptual but grounded in the text. You approach questions as problems to be worked through, not puzzles to be solved. You are friendly and accessible, but maintain the philosophical rigor and distinctive terminology of your work with Guattari.

PRIORITIZE CLARITY THROUGH CONCEPTS: Explain concepts by showing how they function, how they connect, how they produce effects. Use your distinctive vocabulary—flows, machines, desiring-production, schizoanalysis, the body without organs, Oedipus, fascism in the body—but always ground these in the text. Make ideas accessible by showing their connections and operations, not by simplifying them away.

ALWAYS USE DIRECT QUOTATIONS: When explaining concepts, you MUST include direct quotations from the text. Quote the exact words from Anti-Oedipus, using quotation marks. Do not paraphrase when a direct quote would be clearer. Include chapter numbers and titles with every citation.

You have access to relevant passages from Anti-Oedipus. Use these passages to provide direct quotations that illustrate your explanations. When explaining a concept, engage with it as a problem, show how it connects to other concepts, and support your explanation with direct quotations from the text.

Speak in the voice of Deleuze: philosophical, precise, conceptually engaged, thinking in terms of multiplicities and connections, but always grounded in the text you wrote with Guattari.";
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
                'content' => [],
                'subsections' => []
            ];
            $i++;
            continue;
        }
        
        // Check for h1 headings (#) - these are subsections within chapters
        // Format: "# 1 Desiring-Production" or "# 2 The Body without Organs"
        // Match # followed by space and content (but not ##)
        if (preg_match('/^# ([^#].+)$/', $line, $sub_matches)) {
            $subsection_title = trim($sub_matches[1]);
            // Add subsection to current chapter
            if ($current_chapter !== null) {
                $current_chapter['subsections'][] = [
                    'title' => $subsection_title,
                    'slug' => slugify($subsection_title)
                ];
                $current_chapter['content'][] = $line;
            }
            $i++;
            continue;
        }
        
        // Check for h3 headings (###) - subsections within chapters
        if (preg_match('/^### (.+)$/', $line, $sub_matches)) {
            $subsection_title = trim($sub_matches[1]);
            // Add subsection to current chapter
            if ($current_chapter !== null) {
                $current_chapter['subsections'][] = [
                    'title' => $subsection_title,
                    'slug' => slugify($subsection_title)
                ];
                $current_chapter['content'][] = $line;
            }
            $i++;
            continue;
        }
        
        // Check for h4 headings (####) - subsections within chapters
        if (preg_match('/^#### (.+)$/', $line, $sub_matches)) {
            $subsection_title = trim($sub_matches[1]);
            // Add subsection to current chapter
            if ($current_chapter !== null) {
                $current_chapter['subsections'][] = [
                    'title' => $subsection_title,
                    'slug' => slugify($subsection_title)
                ];
                $current_chapter['content'][] = $line;
            }
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
        $has_subsections = !empty($chapter['subsections']) && count($chapter['subsections']) > 0;
        
        if ($has_subsections) {
            $html .= '<li class="toc-chapter">';
            $html .= '<div class="toc-chapter-header">';
            $html .= '<button class="toc-expand" aria-label="Toggle subsections">';
            $html .= '<svg class="toc-expand-icon" width="12" height="12" fill="none" stroke="currentColor" viewBox="0 0 24 24">';
            $html .= '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>';
            $html .= '</svg>';
            $html .= '</button>';
            $html .= '<a href="?chapter=' . $num . '" class="toc-chapter-link">' . htmlspecialchars($chapter['title']) . '</a>';
            $html .= '</div>';
            $html .= '<ul class="toc-subsections">';
            foreach ($chapter['subsections'] as $subsection) {
                $subsection_slug = htmlspecialchars($subsection['slug']);
                $subsection_title = htmlspecialchars($subsection['title']);
                $html .= '<li><a href="?chapter=' . $num . '#' . $subsection_slug . '">' . $subsection_title . '</a></li>';
            }
            $html .= '</ul>';
            $html .= '</li>';
        } else {
            $html .= '<li><a href="?chapter=' . $num . '">' . htmlspecialchars($chapter['title']) . '</a></li>';
        }
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
    
    // Headers (h1, h2, h3, h4) - add anchor IDs for navigation
    // Process h1 first (subsections like "# 1 Desiring-Production")
    $html = preg_replace_callback('/^# ([^#].+)$/m', function($matches) {
        $text = trim($matches[1]);
        $slug = slugify($text);
        return '<h1 id="' . htmlspecialchars($slug) . '">' . htmlspecialchars($text) . '</h1>';
    }, $html);
    
    // Process h2 headers
    $html = preg_replace_callback('/^## (.+)$/m', function($matches) {
        $text = trim($matches[1]);
        $slug = slugify($text);
        return '<h2 id="' . htmlspecialchars($slug) . '">' . htmlspecialchars($text) . '</h2>';
    }, $html);
    
    // Process h3 headers
    $html = preg_replace_callback('/^### (.+)$/m', function($matches) {
        $text = trim($matches[1]);
        $slug = slugify($text);
        return '<h3 id="' . htmlspecialchars($slug) . '">' . htmlspecialchars($text) . '</h3>';
    }, $html);
    
    // Process h4 headers
    $html = preg_replace_callback('/^#### (.+)$/m', function($matches) {
        $text = trim($matches[1]);
        $slug = slugify($text);
        return '<h4 id="' . htmlspecialchars($slug) . '">' . htmlspecialchars($text) . '</h4>';
    }, $html);
    
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
    
    // Check if Python executable exists and works
    $output = [];
    $return_var = 0;
    @exec("{$python_path} --version 2>&1", $output, $return_var);
    if ($return_var !== 0) {
        return false;
    }
    
    // Check if required files exist - try pure Python solution first, then FAISS
    $has_pure_python = isset($config['SEARCH_PURE_PYTHON']) && 
                       isset($config['EMBEDDINGS_JSON']) &&
                       file_exists($config['EMBED_SCRIPT']) &&
                       file_exists($config['SEARCH_PURE_PYTHON']) &&
                       file_exists($config['EMBEDDINGS_JSON']) &&
                       file_exists($config['CHUNKS_JSON']);
    
    $has_faiss = file_exists($config['EMBED_SCRIPT']) &&
                 file_exists($config['SEARCH_SCRIPT']) &&
                 file_exists($config['FAISS_INDEX']) &&
                 file_exists($config['CHUNKS_JSON']);
    
    return $has_pure_python || $has_faiss;
}

function call_python_rag($query, $k = 20, $use_hybrid = true) {
    global $config;
    $python_path = $config['PYTHON_PATH'];
    $index_path = $config['FAISS_INDEX'];
    $chunks_path = $config['CHUNKS_JSON'];
    
    try {
        // Use hybrid search if available, otherwise fall back to semantic-only
        // Try pure Python hybrid first (no FAISS needed), then FAISS hybrid
        $hybrid_script = null;
        if ($use_hybrid) {
            // Try pure Python hybrid first
            if (isset($config['HYBRID_PURE_PYTHON']) && file_exists($config['HYBRID_PURE_PYTHON']) && 
                isset($config['EMBEDDINGS_JSON']) && file_exists($config['EMBEDDINGS_JSON'])) {
                $hybrid_script = $config['HYBRID_PURE_PYTHON'];
                $embeddings_path = $config['EMBEDDINGS_JSON'];
            } elseif (isset($config['HYBRID_SCRIPT']) && file_exists($config['HYBRID_SCRIPT'])) {
                $hybrid_script = $config['HYBRID_SCRIPT'];
                $embeddings_path = null;
            }
        }
        
        if ($use_hybrid && $hybrid_script) {
            // Hybrid search: combines semantic + keyword matching
            $query_escaped = escapeshellarg($query);
            $chunks_path_escaped = escapeshellarg($chunks_path);
            $k_escaped = escapeshellarg($k);
            
            if ($embeddings_path) {
                // Pure Python hybrid search
                $embeddings_path_escaped = escapeshellarg($embeddings_path);
                $search_command = "{$python_path} {$hybrid_script} {$embeddings_path_escaped} {$chunks_path_escaped} {$query_escaped} {$k_escaped} 2>/dev/null";
            } else {
                // FAISS hybrid search
                $index_path_escaped = escapeshellarg($index_path);
                $search_command = "{$python_path} {$hybrid_script} {$index_path_escaped} {$chunks_path_escaped} {$query_escaped} {$k_escaped} 2>/dev/null";
            }
            
            $search_output = shell_exec($search_command);
            
            if ($search_output === null || empty(trim($search_output))) {
                // Try with stderr capture to see what the error is
                $search_command_debug = "{$python_path} {$hybrid_script} {$index_path_escaped} {$chunks_path_escaped} {$query_escaped} {$k_escaped} 2>&1";
                $search_output_debug = shell_exec($search_command_debug);
                error_log("Hybrid search returned null/empty output. Debug output: " . substr($search_output_debug, 0, 500));
                $use_hybrid = false;
            } else {
                // Try to extract JSON from output (in case there's extra text)
                $json_start = strpos($search_output, '{');
                $json_end = strrpos($search_output, '}');
                if ($json_start !== false && $json_end !== false && $json_end > $json_start) {
                    $json_output = substr($search_output, $json_start, $json_end - $json_start + 1);
                } else {
                    $json_output = $search_output;
                }
                
                $search_result = json_decode($json_output, true);
                if (json_last_error() === JSON_ERROR_NONE && isset($search_result['indices']) && is_array($search_result['indices'])) {
                    // Hybrid search succeeded
                    $indices = $search_result['indices'];
                    $similarities = $search_result['similarities'] ?? [];
                    $exact_matches = $search_result['exact_matches'] ?? [];
                    
                    // Log exact matches for debugging
                    if (!empty($exact_matches)) {
                        $exact_count = count(array_filter($exact_matches));
                        error_log("Hybrid search found {$exact_count} exact matches for query: " . substr($query, 0, 50));
                    }
                } else {
                    error_log("Hybrid search JSON error: " . json_last_error_msg() . ". Output preview: " . substr($search_output, 0, 300));
                    $use_hybrid = false;
                }
            }
        }
        
        // Fall back to semantic-only search if hybrid failed or not requested
        if (!$use_hybrid) {
            // Try pure Python search first (no FAISS/NumPy required)
            $search_pure_python = $config['SEARCH_PURE_PYTHON'] ?? null;
            $embeddings_json = $config['EMBEDDINGS_JSON'] ?? null;
            
            if ($search_pure_python && $embeddings_json && file_exists($search_pure_python) && file_exists($embeddings_json)) {
                // Use pure Python search (no FAISS needed)
                $embed_script = $config['EMBED_SCRIPT'] ?? $config['EMBED_SCRIPT'] ?? __DIR__ . '/embed_query_openai.py';
                
                // Step 1: Convert query to embedding vector
                $query_escaped = escapeshellarg($query);
                $embed_command = "{$python_path} {$embed_script} {$query_escaped} 2>/dev/null";
                $embed_output = shell_exec($embed_command);
                
                if ($embed_output === null || empty(trim($embed_output))) {
                    error_log("Pure Python embed query returned null/empty output");
                    return simple_text_search($query, $k);
                }
                
                // Extract JSON from output
                $json_start = strpos($embed_output, '[');
                $json_end = strrpos($embed_output, ']');
                if ($json_start !== false && $json_end !== false && $json_end > $json_start) {
                    $json_output = substr($embed_output, $json_start, $json_end - $json_start + 1);
                } else {
                    $json_output = $embed_output;
                }
                
                $query_vector = json_decode($json_output, true);
                if (json_last_error() !== JSON_ERROR_NONE || isset($query_vector['error'])) {
                    error_log("Pure Python embed query error: " . ($query_vector['error'] ?? json_last_error_msg()));
                    return simple_text_search($query, $k);
                }
                
                // Step 2: Search using pure Python
                $vector_json = escapeshellarg(json_encode($query_vector));
                $embeddings_path_escaped = escapeshellarg($embeddings_json);
                $k_escaped = escapeshellarg($k);
                $search_command = "{$python_path} {$search_pure_python} {$embeddings_path_escaped} {$vector_json} {$k_escaped} 2>/dev/null";
                $search_output = shell_exec($search_command);
            } else {
                // Fall back to FAISS search
                $embed_script = $config['EMBED_SCRIPT'];
                $search_script = $config['SEARCH_SCRIPT'];
                
                // Step 1: Convert query to embedding vector
                $query_escaped = escapeshellarg($query);
                // Redirect stderr to avoid Python version messages
                $embed_command = "{$python_path} {$embed_script} {$query_escaped} 2>/dev/null";
                $embed_output = shell_exec($embed_command);
                
                if ($embed_output === null || empty(trim($embed_output))) {
                    // Try with stderr capture for debugging
                    $embed_command_debug = "{$python_path} {$embed_script} {$query_escaped} 2>&1";
                    $embed_output_debug = shell_exec($embed_command_debug);
                    error_log("Embed query returned null/empty output. Debug: " . substr($embed_output_debug, 0, 300));
                    return simple_text_search($query, $k);
                }
                
                // Extract JSON from output if there's extra text
                $json_start = strpos($embed_output, '[');
                $json_end = strrpos($embed_output, ']');
                if ($json_start !== false && $json_end !== false && $json_end > $json_start) {
                    $json_output = substr($embed_output, $json_start, $json_end - $json_start + 1);
                } else {
                    $json_output = $embed_output;
                }
                
                $query_vector = json_decode($json_output, true);
                if (json_last_error() !== JSON_ERROR_NONE || isset($query_vector['error'])) {
                    error_log("Embed query error: " . ($query_vector['error'] ?? json_last_error_msg()) . ". Output: " . substr($embed_output, 0, 200));
                    return simple_text_search($query, $k);
                }
                
                // Step 2: Search FAISS index
                $vector_json = escapeshellarg(json_encode($query_vector));
                $index_path_escaped = escapeshellarg($index_path);
                $k_escaped = escapeshellarg($k);
                // Redirect stderr to avoid Python version messages
                $search_command = "{$python_path} {$search_script} {$index_path_escaped} {$vector_json} {$k_escaped} 2>/dev/null";
                $search_output = shell_exec($search_command);
            }
            
            if ($search_output === null || empty(trim($search_output))) {
                error_log("Search FAISS returned null/empty output. Command: " . $search_command);
                return simple_text_search($query, $k);
            }
            
            $search_result = json_decode($search_output, true);
            if (json_last_error() !== JSON_ERROR_NONE || isset($search_result['error'])) {
                error_log("Search FAISS error: " . ($search_result['error'] ?? json_last_error_msg()));
                return simple_text_search($query, $k);
            }
            
            if (!isset($search_result['indices']) || !is_array($search_result['indices'])) {
                error_log("Search FAISS returned invalid result structure");
                return simple_text_search($query, $k);
            }
            
            $indices = $search_result['indices'];
            $similarities = $search_result['similarities'] ?? [];
        }
        
        // Step 3: Load chunks from JSON and return results
        if (!file_exists($chunks_path)) {
            error_log("Chunks JSON file not found: " . $chunks_path);
            return simple_text_search($query, $k);
        }
        
        $chunks_data = json_decode(file_get_contents($chunks_path), true);
        if ($chunks_data === null || !isset($chunks_data['chunks']) || !isset($chunks_data['metadata'])) {
            error_log("Failed to load or parse chunks JSON");
            return simple_text_search($query, $k);
        }
        
        $chunks = $chunks_data['chunks'];
        $metadata = $chunks_data['metadata'];
        
        // Build results array, prioritizing exact matches
        $results = [];
        $exact_match_results = [];
        $other_results = [];
        
        foreach ($indices as $idx => $chunk_idx) {
            if ($chunk_idx >= 0 && $chunk_idx < count($chunks)) {
                $chunk_meta = $metadata[$chunk_idx] ?? [];
                // Check if this chunk index is in exact_matches array
                // exact_matches is indexed by result position, not chunk index
                $is_exact = false;
                if (is_array($exact_matches) && isset($exact_matches[$idx])) {
                    $is_exact = (bool)$exact_matches[$idx];
                }
                
                $result_item = [
                    'text' => $chunks[$chunk_idx],
                    'chapter_num' => $chunk_meta['chapter_num'] ?? 0,
                    'chapter_title' => $chunk_meta['chapter_title'] ?? 'Unknown',
                    'subsection' => $chunk_meta['subsection'] ?? '',
                    'score' => isset($similarities[$idx]) ? floatval($similarities[$idx]) : 0.0,
                    'exact_match' => $is_exact
                ];
                
                // Separate exact matches from other results
                if ($is_exact) {
                    $exact_match_results[] = $result_item;
                } else {
                    $other_results[] = $result_item;
                }
            }
        }
        
        // Return exact matches first, then other results
        return array_merge($exact_match_results, $other_results);
        
    } catch (Exception $e) {
        error_log("Python RAG error: " . $e->getMessage());
        return simple_text_search($query, $k);
    }
}

function simple_text_search($query, $k = 5) {
    // Improved keyword-based search with better matching
    $chapters = parse_markdown_chapters();
    $results = [];
    
    if (empty($chapters)) {
        error_log("No chapters found in simple_text_search");
        return [];
    }
    
    // Clean and split query into meaningful terms (remove common words)
    $query_lower = strtolower(trim($query));
    $stop_words = ['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those', 'what', 'which', 'who', 'when', 'where', 'why', 'how'];
    $query_terms = array_filter(explode(' ', $query_lower), function($term) use ($stop_words) {
        $term = trim($term);
        return strlen($term) > 2 && !in_array($term, $stop_words);
    });
    
    // If no meaningful terms after filtering, use original query
    if (empty($query_terms)) {
        $query_terms = [strtolower($query)];
    }
    
    // Search through all chapters
    foreach ($chapters as $idx => $chapter) {
        $chapter_num = $idx + 1;
        $content = $chapter['content'] ?? '';
        
        if (empty($content)) {
            continue;
        }
        
        $content_lower = strtolower($content);
        
        // Calculate score based on term frequency and position
        $score = 0;
        $match_positions = [];
        
        foreach ($query_terms as $term) {
            $term = trim($term);
            if (empty($term)) continue;
            
            $count = substr_count($content_lower, $term);
            $score += $count;
            
            // Find all positions of this term
            $pos = 0;
            while (($pos = stripos($content_lower, $term, $pos)) !== false) {
                $match_positions[] = $pos;
                $pos += strlen($term);
            }
        }
        
        if ($score > 0 && !empty($match_positions)) {
            // Sort match positions
            sort($match_positions);
            
            // Extract chunks around each match (up to k chunks per chapter)
            $chunks_per_chapter = min(2, $k); // Max 2 chunks per chapter
            $chunks_added = 0;
            
            foreach ($match_positions as $pos) {
                if ($chunks_added >= $chunks_per_chapter) break;
                
                // Get context around match (300 chars before and after)
                $start = max(0, $pos - 300);
                $end = min(strlen($content), $pos + strlen($query) + 300);
                $chunk = substr($content, $start, $end - $start);
                
                // Calculate chunk score
                $chunk_score = 0;
                $chunk_lower = strtolower($chunk);
                foreach ($query_terms as $term) {
                    $chunk_score += substr_count($chunk_lower, $term);
                }
                
                // Only add if chunk has meaningful content
                if (strlen(trim($chunk)) > 50) {
                    $results[] = [
                        'text' => trim($chunk),
                        'chapter_num' => $chapter_num,
                        'chapter_title' => $chapter['title'] ?? "Chapter $chapter_num",
                        'subsection' => '',
                        'score' => $chunk_score
                    ];
                    $chunks_added++;
                }
            }
        }
    }
    
    // Sort by score (highest first) and limit
    usort($results, function($a, $b) {
        return ($b['score'] ?? 0) <=> ($a['score'] ?? 0);
    });
    
    // Remove duplicates (same chapter and similar text)
    $unique_results = [];
    foreach ($results as $result) {
        $key = $result['chapter_num'] . '|' . substr($result['text'], 0, 100);
        if (!isset($unique_results[$key])) {
            $unique_results[$key] = $result;
        }
    }
    
    $final_results = array_values($unique_results);
    
    // Log if no results found
    if (empty($final_results)) {
        error_log("Simple text search found no results for query: " . $query);
    }
    
    return array_slice($final_results, 0, $k);
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
    
    // Disable output buffering for streaming
    if (ob_get_level()) {
        ob_end_clean();
    }
    
    // Set headers for streaming
    header('Content-Type: text/plain');
    header('Cache-Control: no-cache');
    header('Connection: keep-alive');
    
    $ch = curl_init('https://api.openai.com/v1/chat/completions');
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, false);
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($data));
    curl_setopt($ch, CURLOPT_HTTPHEADER, [
        'Content-Type: application/json',
        'Authorization: Bearer ' . $api_key
    ]);
    
    // Handle streaming response
    curl_setopt($ch, CURLOPT_WRITEFUNCTION, function($ch, $data) {
        // Parse Server-Sent Events format
        $lines = explode("\n", $data);
        foreach ($lines as $line) {
            if (strpos($line, 'data: ') === 0) {
                $json_str = substr($line, 6);
                if ($json_str === '[DONE]') {
                    return strlen($data);
                }
                $json = json_decode($json_str, true);
                if ($json && isset($json['choices'][0]['delta']['content'])) {
                    $content = $json['choices'][0]['delta']['content'];
                    echo $content;
                    flush();
                }
            }
        }
        return strlen($data);
    });
    
    $result = curl_exec($ch);
    $error = curl_error($ch);
    curl_close($ch);
    
    if ($result === false && $error) {
        echo "Error: " . $error;
    }
}

