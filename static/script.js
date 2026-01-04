console.log('Script.js loading...');

document.addEventListener('DOMContentLoaded', () => {
    console.log('DOMContentLoaded fired');
    
    // State
    const state = {
        theme: localStorage.getItem('theme') || 'light',
        fontSize: parseInt(localStorage.getItem('fontSize') || '100'),
        fontFamily: localStorage.getItem('fontFamily') || "'Merriweather', serif",
        isChatOpen: false,
        chatHistory: []
    };

    // Elements
    const body = document.body;
    const content = document.getElementById('content');
    const themeToggle = document.getElementById('theme-toggle');
    const fontToggle = document.getElementById('font-toggle');
    const chatToggle = document.getElementById('chat-toggle');
    const chatSidebar = document.getElementById('chat-sidebar');
    const fontMenu = document.getElementById('font-menu');
    const searchToggle = document.getElementById('search-toggle');
    const searchBar = document.getElementById('search-bar');
    const tocToggle = document.getElementById('toc-toggle');
    const tocSidebar = document.getElementById('toc-sidebar');
    const closeToc = document.getElementById('close-toc');
    
    // Debug: Log all elements
    console.log('Elements found:');
    console.log('  chatToggle:', chatToggle);
    console.log('  chatSidebar:', chatSidebar);
    console.log('  content:', content);
    
    if (!chatToggle) {
        console.error('CRITICAL: chat-toggle element not found!');
    }
    if (!chatSidebar) {
        console.error('CRITICAL: chat-sidebar element not found!');
    }
    
    // Initialize Theme
    const applyTheme = () => {
        document.documentElement.setAttribute('data-theme', state.theme);
        themeToggle.querySelector('.sun').style.display = state.theme === 'light' ? 'block' : 'none';
        themeToggle.querySelector('.moon').style.display = state.theme === 'dark' ? 'block' : 'none';
    };
    applyTheme();

    // Initialize Fonts
    const applyFonts = () => {
        // Set CSS variable for font size
        document.documentElement.style.setProperty('--font-size-multiplier', `${state.fontSize / 100}`);
        
        // Apply font family to text container
        const textContainer = content.querySelector('.text-container');
        if (textContainer) {
            textContainer.style.fontFamily = state.fontFamily;
        } else {
            content.style.fontFamily = state.fontFamily;
        }
        
        const fontSizeDisplay = document.getElementById('font-size-display');
        const fontFamilySelect = document.getElementById('font-family-select');
        if (fontSizeDisplay) {
            fontSizeDisplay.textContent = `${state.fontSize}%`;
        }
        if (fontFamilySelect) {
            fontFamilySelect.value = state.fontFamily;
        }
    };
    applyFonts();

    // Event Listeners: Theme
    themeToggle.addEventListener('click', () => {
        state.theme = state.theme === 'light' ? 'dark' : 'light';
        localStorage.setItem('theme', state.theme);
        applyTheme();
    });

    // Event Listeners: TOC Sidebar
    if (tocToggle && tocSidebar) {
        tocToggle.addEventListener('click', () => {
            tocSidebar.classList.toggle('open');
        });
        
        if (closeToc) {
            closeToc.addEventListener('click', () => {
                tocSidebar.classList.remove('open');
            });
        }
        
        // Close TOC when clicking outside
        document.addEventListener('click', (e) => {
            if (tocSidebar.classList.contains('open') && 
                !tocSidebar.contains(e.target) && 
                !tocToggle.contains(e.target)) {
                tocSidebar.classList.remove('open');
            }
        });
        
        // Expand/collapse TOC chapters
        const tocExpandButtons = tocSidebar.querySelectorAll('.toc-expand');
        tocExpandButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                const chapterItem = button.closest('.toc-chapter');
                if (chapterItem) {
                    chapterItem.classList.toggle('expanded');
                }
            });
        });
        
        // Prevent chapter link clicks from toggling expand/collapse
        const tocChapterLinks = tocSidebar.querySelectorAll('.toc-chapter-link');
        tocChapterLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                e.stopPropagation();
            });
        });
        
        // Expand chapter if it contains the active link
        const expandActiveChapter = () => {
            const activeLink = tocSidebar.querySelector('.toc-list a.active');
            if (activeLink) {
                // Find the parent chapter (works for both chapter links and subsection links)
                const chapterItem = activeLink.closest('.toc-chapter');
                if (chapterItem && !chapterItem.classList.contains('expanded')) {
                    chapterItem.classList.add('expanded');
                }
            }
        };
        
        // Highlight active TOC link
        const updateActiveTOCLink = () => {
            const urlParams = new URLSearchParams(window.location.search);
            const currentChapter = urlParams.get('chapter');
            // Default to '0' (title page) if no chapter parameter
            const chapterToHighlight = currentChapter !== null ? currentChapter : '0';
            const tocLinks = tocSidebar.querySelectorAll('.toc-list a');
            tocLinks.forEach(link => {
                link.classList.remove('active');
                const href = link.getAttribute('href');
                // Check for title page (chapter=0) or specific chapter
                if (chapterToHighlight === '0' && href.includes('chapter=0')) {
                    link.classList.add('active');
                } else if (chapterToHighlight && chapterToHighlight !== '0' && href.includes(`chapter=${chapterToHighlight}`)) {
                    link.classList.add('active');
                }
            });
            // Expand chapter containing active link
            expandActiveChapter();
        };
        updateActiveTOCLink();
    }
    
    // Make chapter title clickable
    const chapterTitle = document.querySelector('.chapter-title.clickable');
    if (chapterTitle) {
        const chapterNum = chapterTitle.getAttribute('data-chapter');
        if (chapterNum) {
            chapterTitle.addEventListener('click', () => {
                window.location.href = `?chapter=${chapterNum}`;
            });
        }
    }

    // Event Listeners: Chat Sidebar
    // Initialize sidebar - remove collapsed class and ensure it starts hidden
    if (chatSidebar) {
        chatSidebar.classList.remove('collapsed');
        chatSidebar.classList.remove('open');
        chatSidebar.style.right = '-350px';
        chatSidebar.style.width = '350px';
        console.log('Sidebar initialized, classes:', chatSidebar.className);
    } else {
        console.error('Sidebar element not found during initialization!');
    }
    
    if (chatToggle) {
        console.log('Attaching click listener to chat toggle');
        
        // Test if button is clickable
        chatToggle.style.cursor = 'pointer';
        chatToggle.style.pointerEvents = 'auto';
        
        // Add multiple event listeners to debug
        chatToggle.onclick = function(e) {
            console.log('ONCLICK HANDLER FIRED!', e);
            e.stopPropagation();
            e.preventDefault();
            
            state.isChatOpen = !state.isChatOpen;
            console.log('isChatOpen set to:', state.isChatOpen);
            
            if (!chatSidebar) {
                console.error('ERROR: Chat sidebar element not found!');
                return;
            }
            
            // Remove collapsed class if present
            chatSidebar.classList.remove('collapsed');
            
            if (state.isChatOpen) {
                chatSidebar.classList.add('open');
                // Use right positioning instead of transform
                chatSidebar.style.right = '0';
                chatSidebar.style.width = '350px';
                chatSidebar.style.minWidth = '350px';
                chatSidebar.style.maxWidth = '350px';
                chatSidebar.style.display = 'flex';
                chatSidebar.style.visibility = 'visible';
                chatSidebar.style.opacity = '1';
                chatSidebar.style.zIndex = '9999';
                console.log('Added "open" class, sidebar classes:', chatSidebar.className);
                
                // Force reflow
                void chatSidebar.offsetWidth;
                
                // Check after a brief delay
                setTimeout(() => {
                    const computed = window.getComputedStyle(chatSidebar);
                    const rect = chatSidebar.getBoundingClientRect();
                    console.log('AFTER DELAY - Computed right:', computed.right);
                    console.log('AFTER DELAY - Computed width:', computed.width);
                    console.log('AFTER DELAY - Sidebar rect:', rect);
                    console.log('AFTER DELAY - Window width:', window.innerWidth);
                    console.log('AFTER DELAY - Sidebar parent:', chatSidebar.parentElement);
                }, 100);
            } else {
                chatSidebar.classList.remove('open');
                chatSidebar.style.right = '-350px';
                console.log('Removed "open" class, sidebar classes:', chatSidebar.className);
            }
            
            // Check computed styles immediately
            const computed = window.getComputedStyle(chatSidebar);
            const rect = chatSidebar.getBoundingClientRect();
            console.log('IMMEDIATE - Computed right:', computed.right);
            console.log('IMMEDIATE - Computed display:', computed.display);
            console.log('IMMEDIATE - Computed visibility:', computed.visibility);
            console.log('IMMEDIATE - Computed width:', computed.width);
            console.log('IMMEDIATE - Computed z-index:', computed.zIndex);
            console.log('IMMEDIATE - Sidebar rect:', rect);
            console.log('IMMEDIATE - Window innerWidth:', window.innerWidth);
            console.log('IMMEDIATE - Sidebar offsetWidth:', chatSidebar.offsetWidth);
            console.log('IMMEDIATE - Sidebar scrollWidth:', chatSidebar.scrollWidth);
        };
        
        chatToggle.addEventListener('click', (e) => {
            console.log('ADD EVENT LISTENER HANDLER FIRED!', e);
        });
        
        chatToggle.addEventListener('mousedown', (e) => {
            console.log('MOUSEDOWN on chat toggle!', e);
        });
    } else {
        console.error('Cannot attach click listener - chatToggle is null!');
    }

    const closeChatBtn = document.getElementById('close-chat');
    if (closeChatBtn) {
        closeChatBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            state.isChatOpen = false;
            chatSidebar.classList.remove('open');
            chatSidebar.classList.remove('collapsed');
            chatSidebar.style.right = '-350px';
        });
    }
    
    // Close chat when clicking outside (but not on toggle or inside sidebar)
    document.addEventListener('click', (e) => {
        // Check if click is on toggle button or inside sidebar
        const clickedOnToggle = chatToggle.contains(e.target) || e.target.closest('#chat-toggle');
        const clickedInSidebar = chatSidebar.contains(e.target);
        const clickedOnCloseBtn = e.target.closest('#close-chat');
        
        if (clickedOnToggle || clickedOnCloseBtn) {
            return;
        }
        
        // Defer the close check to ensure toggle handler has run
        setTimeout(() => {
            if (state.isChatOpen && !clickedInSidebar) {
                state.isChatOpen = false;
                chatSidebar.classList.remove('open');
                chatSidebar.classList.remove('collapsed');
                chatSidebar.style.right = '-350px';
            }
        }, 10);
    });

    // Event Listeners: Font Menu
    fontToggle.addEventListener('click', (e) => {
        e.stopPropagation();
        fontMenu.classList.toggle('hidden');
    });
    
    // Close font menu when clicking outside
    document.addEventListener('click', (e) => {
        if (!fontMenu.classList.contains('hidden') &&
            !fontMenu.contains(e.target) &&
            !fontToggle.contains(e.target)) {
            fontMenu.classList.add('hidden');
        }
    });
    
    const fontIncrease = document.getElementById('font-increase');
    const fontDecrease = document.getElementById('font-decrease');
    const fontFamilySelect = document.getElementById('font-family-select');
    
    if (fontIncrease) {
        fontIncrease.addEventListener('click', (e) => {
            e.stopPropagation();
            state.fontSize += 10;
            localStorage.setItem('fontSize', state.fontSize);
            applyFonts();
        });
    }
    
    if (fontDecrease) {
        fontDecrease.addEventListener('click', (e) => {
            e.stopPropagation();
            if (state.fontSize > 50) {
                state.fontSize -= 10;
                localStorage.setItem('fontSize', state.fontSize);
                applyFonts();
            }
        });
    }
    
    if (fontFamilySelect) {
        fontFamilySelect.addEventListener('change', (e) => {
            state.fontFamily = e.target.value;
            localStorage.setItem('fontFamily', state.fontFamily);
            applyFonts();
        });
    }

    // Search functionality
    const searchInput = document.getElementById('search-input');
    const searchNextBtn = document.getElementById('search-next');
    const searchPrevBtn = document.getElementById('search-prev');
    const searchStats = document.getElementById('search-stats');
    const searchCloseBtn = document.getElementById('search-close');
    
    // Check if search elements exist
    if (!searchInput || !searchBar || !searchToggle) {
        console.warn('Search elements not found - search functionality disabled');
    }
    
    let searchResults = [];
    let currentSearchIndex = -1;
    let currentSearchQuery = '';
    
    // Clear highlights when search is closed
    const clearHighlights = () => {
        const highlights = document.querySelectorAll('.search-highlight');
        highlights.forEach(hl => {
            const parent = hl.parentNode;
            parent.replaceChild(document.createTextNode(hl.textContent), hl);
            parent.normalize();
        });
    };
    
    // Escape special regex characters - more robust version
    const escapeRegex = (string) => {
        if (!string) return '';
        // Escape all special regex characters
        return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    };
    
    // Highlight search term in content
    const highlightSearchTerm = (query) => {
        if (!query) return;
        
        const content = document.getElementById('content');
        if (!content) return;
        
        // Clear existing highlights
        clearHighlights();
        
        // Escape the query for regex
        const escapedQuery = escapeRegex(query);
        
        // Walk through text nodes and highlight
        const walker = document.createTreeWalker(
            content,
            NodeFilter.SHOW_TEXT,
            null,
            false
        );
        
        const textNodes = [];
        let node;
        while (node = walker.nextNode()) {
            // Skip script and style tags
            if (node.parentElement && (node.parentElement.tagName === 'SCRIPT' || node.parentElement.tagName === 'STYLE')) {
                continue;
            }
            // Check if text contains the query (case-insensitive)
            if (node.textContent.toLowerCase().includes(query.toLowerCase())) {
                textNodes.push(node);
            }
        }
        
        // Highlight matches
        textNodes.forEach(textNode => {
            const parent = textNode.parentNode;
            if (!parent) return;
            
            const text = textNode.textContent;
            const queryLower = query.toLowerCase();
            const textLower = text.toLowerCase();
            
            // Use simple string matching as fallback if regex fails
            let matches = [];
            try {
                const nodeRegex = new RegExp(`(${escapedQuery})`, 'gi');
                matches = [...text.matchAll(nodeRegex)];
            } catch (e) {
                console.error('Regex failed, using simple string matching:', e);
                // Fallback to simple string matching
                let index = 0;
                while ((index = textLower.indexOf(queryLower, index)) !== -1) {
                    matches.push({
                        index: index,
                        0: text.substring(index, index + query.length)
                    });
                    index += query.length;
                }
            }
            
            if (matches.length === 0) return;
            
            const fragment = document.createDocumentFragment();
            let lastIndex = 0;
            
            matches.forEach(match => {
                // Add text before match
                if (match.index > lastIndex) {
                    fragment.appendChild(document.createTextNode(text.substring(lastIndex, match.index)));
                }
                
                // Add highlighted match
                const highlight = document.createElement('mark');
                highlight.className = 'search-highlight';
                highlight.textContent = match[0];
                fragment.appendChild(highlight);
                
                lastIndex = match.index + match[0].length;
            });
            
            // Add remaining text
            if (lastIndex < text.length) {
                fragment.appendChild(document.createTextNode(text.substring(lastIndex)));
            }
            
            parent.replaceChild(fragment, textNode);
        });
        
        // Scroll to first highlight
        const firstHighlight = document.querySelector('.search-highlight');
        if (firstHighlight) {
            firstHighlight.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    };
    
    // Perform search
    const performSearch = async (query, autoNavigate = true) => {
        if (!query.trim()) {
            searchResults = [];
            currentSearchIndex = -1;
            if (searchStats) {
                searchStats.textContent = '';
            }
            clearHighlights();
            return;
        }
        
        try {
            // Use relative path for PHP version compatibility
            const apiPath = window.location.pathname.includes('index.php') 
                ? 'api/search.php' 
                : '/api/search';
            const response = await fetch(apiPath, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query })
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                const errorMsg = data.error || `HTTP error! status: ${response.status}`;
                throw new Error(errorMsg);
            }
            
            if (data.error) {
                throw new Error(data.error);
            }
            
            searchResults = data.results || [];
            currentSearchQuery = query;
            
            if (searchResults.length > 0) {
                if (searchStats) {
                    searchStats.textContent = `${searchResults.length} result${searchResults.length > 1 ? 's' : ''}`;
                }
                if (autoNavigate) {
                    currentSearchIndex = -1;
                    navigateToSearchResult(0);
                }
            } else {
                if (searchStats) {
                    searchStats.textContent = 'No results';
                }
                clearHighlights();
            }
        } catch (error) {
            console.error('Search error:', error);
            if (searchStats) {
                searchStats.textContent = `Error: ${error.message}`;
            }
        }
    };
    
    // Navigate to search result
    const navigateToSearchResult = (index) => {
        if (searchResults.length === 0 || index < 0 || index >= searchResults.length) {
            return;
        }
        
        const result = searchResults[index];
        currentSearchIndex = index;
        if (searchStats) {
            searchStats.textContent = `${index + 1} / ${searchResults.length}`;
        }
        
        // Navigate to chapter if not already there
        const urlParams = new URLSearchParams(window.location.search);
        const currentChapter = parseInt(urlParams.get('chapter') || '0');
        
        if (currentChapter !== result.chapter_num) {
            // Navigate to chapter with search query in URL
            window.location.href = `?chapter=${result.chapter_num}&search=${encodeURIComponent(currentSearchQuery)}&index=${index}`;
        } else {
            // Already on correct chapter, just highlight and scroll
            setTimeout(() => {
                highlightSearchTerm(currentSearchQuery);
                // Scroll to the specific match
                const highlights = document.querySelectorAll('.search-highlight');
                if (highlights.length > 0) {
                    // Find the highlight that corresponds to this result
                    // We'll scroll to the first one for now, or we could use the match position
                    highlights[0].scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
            }, 100);
        }
    };
    
    // Search input handler (only if elements exist)
    if (searchInput) {
        let searchTimeout;
        searchInput.addEventListener('input', (e) => {
            clearTimeout(searchTimeout);
            const query = e.target.value.trim();
            
            searchTimeout = setTimeout(() => {
                performSearch(query);
            }, 300); // Debounce search
        });
        
        // Enter key to search immediately
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                clearTimeout(searchTimeout);
                performSearch(e.target.value.trim());
            }
        });
    }
    
    // Next/Prev buttons
    if (searchNextBtn) {
        searchNextBtn.addEventListener('click', () => {
            if (searchResults.length > 0) {
                const nextIndex = (currentSearchIndex + 1) % searchResults.length;
                navigateToSearchResult(nextIndex);
            }
        });
    }
    
    if (searchPrevBtn) {
        searchPrevBtn.addEventListener('click', () => {
            if (searchResults.length > 0) {
                const prevIndex = currentSearchIndex <= 0 ? searchResults.length - 1 : currentSearchIndex - 1;
                navigateToSearchResult(prevIndex);
            }
        });
    }
    
    // Handle hash navigation (scroll to anchor on page load)
    const handleHashNavigation = () => {
        if (window.location.hash) {
            const hash = window.location.hash.substring(1); // Remove the #
            const targetElement = document.getElementById(hash);
            if (targetElement) {
                // Wait for content to render, then scroll
                setTimeout(() => {
                    targetElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    // Add a small offset for fixed toolbar
                    window.scrollBy(0, -80);
                }, 100);
            }
        }
    };
    
    // Run on page load
    handleHashNavigation();
    
    // Also handle hash changes (e.g., when clicking TOC links)
    window.addEventListener('hashchange', handleHashNavigation);
    
    // Check for search query in URL on page load
    const urlParams = new URLSearchParams(window.location.search);
    const urlSearchQuery = urlParams.get('search');
    const urlSearchIndex = parseInt(urlParams.get('index') || '0');
    
    if (urlSearchQuery && searchInput && searchBar) {
        // Set search input value and show search bar
        searchInput.value = urlSearchQuery;
        searchBar.classList.remove('hidden');
        
        // Perform search and navigate to result
        setTimeout(async () => {
            await performSearch(urlSearchQuery, false);
            if (searchResults.length > 0 && urlSearchIndex >= 0 && urlSearchIndex < searchResults.length) {
                currentSearchIndex = urlSearchIndex;
                if (searchStats) {
                    searchStats.textContent = `${urlSearchIndex + 1} / ${searchResults.length}`;
                }
                // Wait a bit for content to render, then highlight
                setTimeout(() => {
                    highlightSearchTerm(urlSearchQuery);
                    // Scroll to the specific highlight
                    const highlights = document.querySelectorAll('.search-highlight');
                    if (highlights.length > 0) {
                        // Try to find the highlight at the correct index
                        const targetHighlight = highlights[Math.min(urlSearchIndex, highlights.length - 1)];
                        if (targetHighlight) {
                            targetHighlight.scrollIntoView({ behavior: 'smooth', block: 'center' });
                        }
                    }
                }, 300);
            }
        }, 500);
    }
    
    // Search toggle (only if elements exist)
    if (searchToggle && searchBar) {
        searchToggle.addEventListener('click', (e) => {
            e.stopPropagation();
            searchBar.classList.toggle('hidden');
            if (!searchBar.classList.contains('hidden') && searchInput) {
                searchInput.focus();
            }
        });
    }
    
    if (searchCloseBtn && searchBar) {
        searchCloseBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            searchBar.classList.add('hidden');
            clearHighlights();
            searchResults = [];
            currentSearchIndex = -1;
            if (searchStats) {
                searchStats.textContent = '';
            }
            // Remove search params from URL
            const url = new URL(window.location);
            url.searchParams.delete('search');
            url.searchParams.delete('index');
            window.history.replaceState({}, '', url);
        });
    }
    
    // Close search bar when clicking outside
    document.addEventListener('click', (e) => {
        if (!searchBar.classList.contains('hidden') &&
            !searchBar.contains(e.target) &&
            !searchToggle.contains(e.target)) {
            // Don't close if clicking on highlights
            if (!e.target.closest('.search-highlight')) {
                searchBar.classList.add('hidden');
            }
        }
    });

    // Define Feature
    const defineBtn = document.getElementById('define-btn');
    const definePopover = document.getElementById('define-popover');
    const popoverContent = document.getElementById('definition-content');
    const closePopover = document.getElementById('close-popover');

    document.addEventListener('mouseup', (e) => {
        const selection = window.getSelection();
        if (selection.toString().length > 0 && !definePopover.contains(e.target) && !chatSidebar.contains(e.target)) {
            const range = selection.getRangeAt(0);
            const rect = range.getBoundingClientRect();
            
            defineBtn.style.top = `${window.scrollY + rect.top - 40}px`;
            defineBtn.style.left = `${window.scrollX + rect.left + (rect.width / 2) - 30}px`;
            defineBtn.classList.remove('hidden');
            
            // Store selection context
            defineBtn.dataset.term = selection.toString();
            defineBtn.dataset.context = selection.anchorNode.textContent.substring(Math.max(0, selection.anchorOffset - 100), Math.min(selection.anchorNode.textContent.length, selection.focusOffset + 100));
        } else if (!defineBtn.contains(e.target)) {
            defineBtn.classList.add('hidden');
        }
    });

    closePopover.addEventListener('click', () => {
        definePopover.classList.add('hidden');
    });

    // Chat Implementation
    const chatInput = document.getElementById('chat-input');
    const chatMessages = document.getElementById('chat-messages');
    const sendChat = document.getElementById('send-chat');

    const addMessage = (role, text) => {
        const div = document.createElement('div');
        div.className = `message ${role}`;
        div.innerHTML = marked.parse(text);
        chatMessages.appendChild(div);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    };

    const handleChat = async () => {
        const message = chatInput.value.trim();
        if (!message) return;

        addMessage('user', message);
        chatInput.value = '';
        
        // Add loading state or stream
        const systemDiv = document.createElement('div');
        systemDiv.className = 'message system';
        systemDiv.textContent = '...';
        chatMessages.appendChild(systemDiv);
        
        try {
            // Use relative path for PHP version compatibility
            const chatPath = window.location.pathname.includes('index.php') 
                ? 'api/chat.php' 
                : '/api/chat';
            const response = await fetch(chatPath, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message,
                    history: state.chatHistory
                })
            });

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let responseText = '';
            
            systemDiv.textContent = '';
            
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                const chunk = decoder.decode(value);
                responseText += chunk;
                systemDiv.innerHTML = marked.parse(responseText);
                chatMessages.scrollTop = chatMessages.scrollHeight;
            }
            
            state.chatHistory.push({ role: 'user', content: message });
            state.chatHistory.push({ role: 'assistant', content: responseText });

        } catch (e) {
            systemDiv.textContent = "Error connecting to Deleuze.";
        }
    };

    sendChat.addEventListener('click', handleChat);
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleChat();
        }
    });
    
    // Define button handler - opens chat sidebar with definition
    defineBtn.addEventListener('click', async () => {
        const term = defineBtn.dataset.term;
        const context = defineBtn.dataset.context;
        
        defineBtn.classList.add('hidden');
        
        // Open chat sidebar
        if (chatSidebar) {
            chatSidebar.classList.add('open');
            chatSidebar.style.right = '0';
            chatSidebar.style.width = '350px';
            chatSidebar.style.minWidth = '350px';
            chatSidebar.style.maxWidth = '350px';
        }
        
        // Add user message asking about the term
        const question = `What does "${term}" mean?`;
        addMessage('user', question);
        
        // Add loading message
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'message system';
        loadingDiv.textContent = 'Asking Deleuze...';
        chatMessages.appendChild(loadingDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        
        try {
            // Use relative path for PHP version compatibility
            const definePath = window.location.pathname.includes('index.php') 
                ? 'api/define.php' 
                : '/api/define';
            const res = await fetch(definePath, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ term, context })
            });
            const data = await res.json();
            
            // Replace loading message with actual response
            loadingDiv.className = 'message system';
            loadingDiv.innerHTML = marked.parse(data.definition);
            chatMessages.scrollTop = chatMessages.scrollHeight;
            
            // Update chat history
            state.chatHistory.push({ role: 'user', content: question });
            state.chatHistory.push({ role: 'assistant', content: data.definition });
        } catch (e) {
            loadingDiv.textContent = "Error fetching definition.";
        }
    });
});
