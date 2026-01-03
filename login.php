<?php
/**
 * Login page for PHP version
 */

// Load configuration FIRST (before session_start) so session ini settings can be set
require_once __DIR__ . '/config.php';
require_once __DIR__ . '/php_utils.php';

// Now start session (after config has set ini settings)
session_start();

$error = '';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $input = trim($_POST['password'] ?? '');
    
    if (empty($input)) {
        $error = "Please enter a password or API key";
    } else {
        global $config;
        
        // Check if it's the server password
        if (!empty($config['APP_PASSWORD']) && $input === $config['APP_PASSWORD']) {
            $_SESSION['logged_in'] = true;
            unset($_SESSION['user_api_key']); // Use server key
            header('Location: index.php');
            exit;
        }
        
        // Check if it's an OpenAI API key
        if (strpos($input, 'sk-') === 0 && strlen($input) >= 20) {
            // Validate format (basic check)
            $_SESSION['logged_in'] = true;
            $_SESSION['user_api_key'] = $input;
            header('Location: index.php');
            exit;
        }
        
        // Invalid
        if (!empty($config['APP_PASSWORD'])) {
            $error = "Invalid Password or API Key";
        } else {
            $error = "Invalid API Key. Please provide a valid OpenAI API key.";
        }
    }
}

?>
<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - Anti-Oedipus Reader</title>
    <link rel="stylesheet" href="static/style.css?v=6">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Merriweather:ital,wght@0,300;0,400;0,700;1,300;1,400&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
</head>
<body>
    <div class="login-page">
        <div class="login-container">
            <div class="login-header">
                <div class="version-badge">
                    <span class="version-label">AI-Enhanced Edition</span>
                </div>
                <h1 class="login-title">Anti-Oedipus</h1>
                <p class="login-subtitle">CAPITALISM AND SCHIZOPHRENIA</p>
                <p class="login-authors">by Gilles Deleuze and Felix Guattari</p>
            </div>
            
            <div class="login-form-container">
                <form method="POST" action="login.php" class="login-form">
                    <?php if ($error): ?>
                        <div class="login-error">
                            <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                            </svg>
                            <span><?php echo htmlspecialchars($error); ?></span>
                        </div>
                    <?php endif; ?>
                    
                    <div class="form-group">
                        <label for="password">Password or OpenAI API Key</label>
                        <input 
                            type="password" 
                            id="password" 
                            name="password" 
                            required 
                            autofocus
                            placeholder="Enter password or API key"
                            class="form-input"
                        >
                    </div>
                    
                    <button type="submit" class="login-button">
                        <span>Login</span>
                        <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7l5 5m0 0l-5 5m5-5H6"></path>
                        </svg>
                    </button>
                </form>
                
                <div class="login-help">
                    <p>
                        Enter the server password (if configured) or your own OpenAI API key.
                        Your API key is stored securely in your session and never saved on the server.
                    </p>
                </div>
            </div>
        </div>
    </div>
</body>
</html>

