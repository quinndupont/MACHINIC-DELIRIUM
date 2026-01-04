// Simple Annotation System using Selection API and SVG
// No Fabric.js dependency - lightweight and reliable

(function() {
    'use strict';

    // Get current chapter/file identifier for localStorage
    const getFileId = () => {
        const urlParams = new URLSearchParams(window.location.search);
        const chapter = urlParams.get('chapter') || '0';
        return `annotations_chapter_${chapter}`;
    };

    // Annotation data structure: { id, type: 'highlight'|'draw', text, note, selectors, color, paths, timestamp }
    let annotations = [];
    let currentAnnotationId = null;
    let isDrawing = false;
    let drawPath = [];
    let annotationMode = 'highlight'; // 'highlight', 'draw', 'none'
    let isAnnotationActive = false;

    // DOM Elements
    const annotationToolbar = document.getElementById('annotation-toolbar');
    const annotationToggleToolbar = document.getElementById('annotation-toggle-toolbar');
    const annotationToggle = document.getElementById('annotation-toggle');
    const highlightBtn = document.getElementById('annotation-highlight');
    const drawBtn = document.getElementById('annotation-draw');
    const viewBtn = document.getElementById('annotation-view');
    const clearBtn = document.getElementById('annotation-clear');
    const colorPicker = document.getElementById('annotation-color');
    const notePopup = document.getElementById('annotation-note-popup');
    const noteText = document.getElementById('annotation-note-text');
    const noteSave = document.getElementById('annotation-note-save');
    const noteDelete = document.getElementById('annotation-note-delete');
    const noteClose = document.getElementById('annotation-note-close');
    const annotationSidebar = document.getElementById('annotation-sidebar');
    const annotationList = document.getElementById('annotation-list');
    const sidebarClose = document.getElementById('annotation-sidebar-close');
    const svgOverlay = document.getElementById('annotation-svg-overlay');
    const content = document.getElementById('content');

    if (!content) {
        console.error('[ANNOTATIONS] Content element not found');
        return;
    }

    // Initialize SVG overlay
    const initSVGOverlay = () => {
        if (!svgOverlay || !content) return;
        const contentStyle = window.getComputedStyle(content);
        const paddingLeft = parseInt(contentStyle.paddingLeft) || 0;
        const paddingTop = parseInt(contentStyle.paddingTop) || 0;
        const contentWidth = content.offsetWidth - paddingLeft * 2;
        
        svgOverlay.style.position = 'absolute';
        svgOverlay.style.top = `${paddingTop}px`;
        svgOverlay.style.left = `${paddingLeft}px`;
        svgOverlay.style.width = `${contentWidth}px`;
        svgOverlay.style.height = `${content.scrollHeight - paddingTop * 2}px`;
        svgOverlay.style.pointerEvents = annotationMode === 'draw' ? 'auto' : 'none';
        svgOverlay.setAttribute('width', contentWidth);
        svgOverlay.setAttribute('height', content.scrollHeight - paddingTop * 2);
    };

    // Save annotations to localStorage
    const saveAnnotations = () => {
        const fileId = getFileId();
        localStorage.setItem(fileId, JSON.stringify(annotations));
    };

    // Load annotations from localStorage
    const loadAnnotations = () => {
        const fileId = getFileId();
        const saved = localStorage.getItem(fileId);
        if (saved) {
            try {
                annotations = JSON.parse(saved);
                renderAnnotations();
            } catch (e) {
                console.error('[ANNOTATIONS] Error loading annotations:', e);
                annotations = [];
            }
        } else {
            annotations = [];
        }
    };

    // Create text selector from Range
    const createTextSelector = (range) => {
        const startContainer = range.startContainer;
        const endContainer = range.endContainer;
        const startOffset = range.startOffset;
        const endOffset = range.endOffset;
        
        // Get text content
        const text = range.toString().trim();
        
        // Get surrounding context from the actual text nodes
        const getTextNodeContent = (node) => {
            if (node.nodeType === Node.TEXT_NODE) {
                return node.textContent || '';
            }
            // If element, get first text node
            const walker = document.createTreeWalker(node, NodeFilter.SHOW_TEXT);
            const textNode = walker.nextNode();
            return textNode ? textNode.textContent || '' : '';
        };
        
        const startText = getTextNodeContent(startContainer);
        const endText = getTextNodeContent(endContainer);
        
        // Get more context - look at parent element's text
        const getParentText = (node) => {
            let parent = node.parentElement;
            while (parent && parent !== content) {
                const parentText = parent.textContent || '';
                if (parentText.length > 0 && parentText.length < 500) {
                    return parentText;
                }
                parent = parent.parentElement;
            }
            return '';
        };
        
        const beforeContext = startText.substring(Math.max(0, startOffset - 30), startOffset).trim();
        const afterContext = endText.substring(endOffset, Math.min(endText.length, endOffset + 30)).trim();
        const parentText = getParentText(startContainer);
        
        // Store element tag and class for better matching
        const getElementInfo = (node) => {
            const element = node.nodeType === Node.TEXT_NODE ? node.parentElement : node;
            if (!element) return null;
            return {
                tag: element.tagName,
                className: element.className || '',
                id: element.id || ''
            };
        };
        
        return {
            type: 'TextPositionSelector',
            text: text,
            beforeContext: beforeContext,
            afterContext: afterContext,
            parentText: parentText.substring(0, 200), // Limit size
            startElement: getElementInfo(startContainer),
            endElement: getElementInfo(endContainer),
            // Keep offsets for reference but don't rely on them
            start: startOffset,
            end: endOffset
        };
    };

    // Find text by selector
    const findTextBySelector = (selector) => {
        try {
            if (!selector || !selector.text) {
                return null;
            }
            
            const searchText = selector.text.trim();
            if (searchText.length === 0) {
                return null;
            }
            
            const searchLower = searchText.toLowerCase();
            const beforeContext = selector.beforeContext ? selector.beforeContext.trim().toLowerCase() : '';
            const afterContext = selector.afterContext ? selector.afterContext.trim().toLowerCase() : '';
            const parentText = selector.parentText ? selector.parentText.toLowerCase() : '';
            
            // Search through all text nodes
            const walker = document.createTreeWalker(content, NodeFilter.SHOW_TEXT);
            let node;
            const candidates = [];
            
            while (node = walker.nextNode()) {
                const text = node.textContent || '';
                const textLower = text.toLowerCase();
                
                // Find all occurrences of the search text
                let idx = textLower.indexOf(searchLower);
                while (idx !== -1) {
                    candidates.push({ node, offset: idx });
                    idx = textLower.indexOf(searchLower, idx + 1);
                }
            }
            
            // Score candidates by context match
            let bestMatch = null;
            let bestScore = 0;
            
            for (const candidate of candidates) {
                const { node, offset } = candidate;
                const text = node.textContent || '';
                const textLower = text.toLowerCase();
                const endOffset = offset + searchText.length;
                
                // Validate offsets
                if (endOffset > text.length) continue;
                
                let score = 0;
                
                // Check before context
                if (beforeContext) {
                    const beforeText = textLower.substring(Math.max(0, offset - beforeContext.length), offset);
                    if (beforeText.includes(beforeContext)) {
                        score += 2;
                    } else if (beforeText.length > 0) {
                        score += 1;
                    }
                } else {
                    score += 1; // No context to match, but still valid
                }
                
                // Check after context
                if (afterContext) {
                    const afterText = textLower.substring(endOffset, Math.min(text.length, endOffset + afterContext.length));
                    if (afterText.includes(afterContext)) {
                        score += 2;
                    } else if (afterText.length > 0) {
                        score += 1;
                    }
                } else {
                    score += 1;
                }
                
                // Check parent text
                if (parentText && node.parentElement) {
                    const parentTextContent = (node.parentElement.textContent || '').toLowerCase();
                    if (parentTextContent.includes(parentText)) {
                        score += 1;
                    }
                }
                
                // Verify exact text match
                const actualText = text.substring(offset, endOffset);
                if (actualText.toLowerCase() === searchLower || actualText === searchText) {
                    score += 5; // Strong match
                } else {
                    continue; // Text doesn't match, skip
                }
                
                if (score > bestScore) {
                    bestScore = score;
                    bestMatch = { startNode: node, startOffset: offset, endNode: node, endOffset: endOffset };
                }
            }
            
            // If we found a good match, return it
            if (bestMatch && bestScore >= 5) {
                return bestMatch;
            }
            
            // Fallback: if no context match but we have text match, use first occurrence
            if (candidates.length > 0) {
                const first = candidates[0];
                const text = first.node.textContent || '';
                const endOffset = first.offset + searchText.length;
                if (endOffset <= text.length) {
                    return { startNode: first.node, startOffset: first.offset, endNode: first.node, endOffset: endOffset };
                }
            }
            
            return null;
        } catch (e) {
            console.error('[ANNOTATIONS] Error finding text:', e);
            return null;
        }
    };

    // Highlight text selection
    const highlightSelection = (range, color) => {
        const text = range.toString();
        if (!text.trim()) return null;

        const selector = createTextSelector(range);
        const id = `annotation_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        
        // Wrap selection in mark element
        const mark = document.createElement('mark');
        mark.className = 'annotation-highlight';
        mark.dataset.annotationId = id;
        mark.style.backgroundColor = color;
        mark.style.opacity = '0.3';
        mark.style.cursor = 'pointer';
        
        try {
            range.surroundContents(mark);
        } catch (e) {
            // If surroundContents fails, extract and wrap manually
            const contents = range.extractContents();
            mark.appendChild(contents);
            range.insertNode(mark);
        }

        const annotation = {
            id: id,
            type: 'highlight',
            text: text,
            note: '',
            selector: selector,
            color: color,
            timestamp: new Date().toISOString()
        };

        annotations.push(annotation);
        saveAnnotations();
        
        // Add click handler to show note popup
        mark.addEventListener('click', (e) => {
            e.stopPropagation();
            showNotePopup(annotation, mark);
        });

        return annotation;
    };

    // Render all annotations
    const renderAnnotations = () => {
        // Clear existing highlights
        document.querySelectorAll('.annotation-highlight').forEach(mark => {
            const parent = mark.parentNode;
            parent.replaceChild(document.createTextNode(mark.textContent), mark);
            parent.normalize();
        });

        // Clear SVG drawings
        if (svgOverlay) {
            svgOverlay.innerHTML = '';
        }

        // Re-render highlights
        annotations.forEach(annotation => {
            if (annotation.type === 'highlight') {
                const result = findTextBySelector(annotation.selector);
                if (result && result.startNode && result.endNode) {
                    try {
                        // Validate offsets before creating range
                        const startMax = result.startNode.textContent ? result.startNode.textContent.length : 0;
                        const endMax = result.endNode.textContent ? result.endNode.textContent.length : 0;
                        
                        if (result.startOffset < 0 || result.startOffset > startMax ||
                            result.endOffset < 0 || result.endOffset > endMax ||
                            result.startOffset > result.endOffset) {
                            console.warn('[ANNOTATIONS] Invalid offsets for annotation:', annotation.id, {
                                startOffset: result.startOffset,
                                startMax,
                                endOffset: result.endOffset,
                                endMax
                            });
                            return; // Skip this annotation
                        }
                        
                        const range = document.createRange();
                        range.setStart(result.startNode, result.startOffset);
                        range.setEnd(result.endNode, result.endOffset);
                        
                        // Check if range is valid
                        if (range.collapsed) {
                            console.warn('[ANNOTATIONS] Range is collapsed for annotation:', annotation.id);
                            return; // Skip collapsed ranges
                        }
                        
                        const mark = document.createElement('mark');
                        mark.className = 'annotation-highlight';
                        mark.dataset.annotationId = annotation.id;
                        mark.style.backgroundColor = annotation.color || '#ffff00';
                        mark.style.opacity = '0.3';
                        mark.style.cursor = 'pointer';
                        
                        const contents = range.extractContents();
                        mark.appendChild(contents);
                        range.insertNode(mark);
                        
                        mark.addEventListener('click', (e) => {
                            e.stopPropagation();
                            showNotePopup(annotation, mark);
                        });
                    } catch (e) {
                        console.error('[ANNOTATIONS] Error rendering highlight:', e, annotation);
                    }
                } else {
                    console.warn('[ANNOTATIONS] Could not find text for annotation:', annotation.id, annotation.text);
                }
            } else if (annotation.type === 'draw' && svgOverlay && annotation.paths) {
                // Render SVG paths
                const pathElement = document.createElementNS('http://www.w3.org/2000/svg', 'path');
                pathElement.setAttribute('d', annotation.paths.join(' '));
                pathElement.setAttribute('stroke', annotation.color || '#000000');
                pathElement.setAttribute('stroke-width', '2');
                pathElement.setAttribute('fill', 'none');
                pathElement.setAttribute('data-annotation-id', annotation.id);
                pathElement.style.cursor = 'pointer';
                svgOverlay.appendChild(pathElement);
                
                pathElement.addEventListener('click', (e) => {
                    e.stopPropagation();
                    showNotePopup(annotation, pathElement);
                });
            }
        });
    };

    // Show note popup
    const showNotePopup = (annotation, element) => {
        currentAnnotationId = annotation.id;
        noteText.value = annotation.note || '';
        
        const rect = element.getBoundingClientRect();
        notePopup.style.top = `${rect.bottom + 5}px`;
        notePopup.style.left = `${rect.left}px`;
        notePopup.classList.remove('hidden');
        noteText.focus();
    };

    // Hide note popup
    const hideNotePopup = () => {
        notePopup.classList.add('hidden');
        currentAnnotationId = null;
    };

    // Set annotation mode
    const setAnnotationMode = (mode) => {
        annotationMode = mode;
        
        // Update button states
        [highlightBtn, drawBtn].forEach(btn => btn && btn.classList.remove('active'));
        
        if (mode === 'highlight') {
            if (highlightBtn) highlightBtn.classList.add('active');
            if (svgOverlay) {
                svgOverlay.style.pointerEvents = 'none';
                svgOverlay.style.display = 'none';
            }
            document.body.style.cursor = 'text';
        } else if (mode === 'draw') {
            if (drawBtn) drawBtn.classList.add('active');
            if (svgOverlay) {
                svgOverlay.style.pointerEvents = 'auto';
                svgOverlay.style.display = 'block';
                initSVGOverlay(); // Reinitialize to ensure proper positioning
            }
            document.body.style.cursor = 'crosshair';
        } else {
            if (svgOverlay) {
                svgOverlay.style.pointerEvents = 'none';
                svgOverlay.style.display = 'none';
            }
            document.body.style.cursor = 'default';
        }
    };

    // Handle text selection for highlighting
    document.addEventListener('mouseup', (e) => {
        // Don't interfere with drawing mode or if clicking on SVG overlay
        if (annotationMode === 'draw' || e.target.closest('#annotation-svg-overlay')) {
            return;
        }
        if (annotationMode === 'highlight' && isAnnotationActive && !annotationToolbar.contains(e.target) && !notePopup.contains(e.target)) {
            const selection = window.getSelection();
            if (selection.rangeCount > 0) {
                const range = selection.getRangeAt(0);
                const text = range.toString().trim();
                if (text && range.intersectsNode(content)) {
                    const color = colorPicker ? colorPicker.value : '#ffff00';
                    highlightSelection(range, color);
                    selection.removeAllRanges();
                }
            }
        }
    });

    // Handle drawing with SVG
    if (svgOverlay) {
        svgOverlay.addEventListener('mousedown', (e) => {
            if (annotationMode === 'draw' && isAnnotationActive) {
                e.preventDefault();
                e.stopPropagation();
                isDrawing = true;
                drawPath = [];
                const rect = svgOverlay.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const y = e.clientY - rect.top;
                drawPath.push(`M ${x} ${y}`);
            }
        });

        svgOverlay.addEventListener('mousemove', (e) => {
            if (isDrawing && annotationMode === 'draw') {
                e.preventDefault();
                const rect = svgOverlay.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const y = e.clientY - rect.top;
                drawPath.push(`L ${x} ${y}`);
                
                // Draw temporary path for visual feedback
                const tempPath = svgOverlay.querySelector('.temp-draw-path');
                if (tempPath) {
                    tempPath.setAttribute('d', drawPath.join(' '));
                } else {
                    const tempPathElement = document.createElementNS('http://www.w3.org/2000/svg', 'path');
                    tempPathElement.setAttribute('class', 'temp-draw-path');
                    tempPathElement.setAttribute('d', drawPath.join(' '));
                    tempPathElement.setAttribute('stroke', colorPicker ? colorPicker.value : '#000000');
                    tempPathElement.setAttribute('stroke-width', '2');
                    tempPathElement.setAttribute('fill', 'none');
                    tempPathElement.style.opacity = '0.5';
                    svgOverlay.appendChild(tempPathElement);
                }
            }
        });

        svgOverlay.addEventListener('mouseup', (e) => {
            if (isDrawing && annotationMode === 'draw') {
                e.preventDefault();
                e.stopPropagation();
                isDrawing = false;
                
                // Remove temporary path
                const tempPath = svgOverlay.querySelector('.temp-draw-path');
                if (tempPath) {
                    tempPath.remove();
                }
                
                if (drawPath.length > 1) {
                    const id = `annotation_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
                    const color = colorPicker ? colorPicker.value : '#000000';
                    
                    const pathElement = document.createElementNS('http://www.w3.org/2000/svg', 'path');
                    pathElement.setAttribute('d', drawPath.join(' '));
                    pathElement.setAttribute('stroke', color);
                    pathElement.setAttribute('stroke-width', '2');
                    pathElement.setAttribute('fill', 'none');
                    pathElement.setAttribute('data-annotation-id', id);
                    pathElement.style.cursor = 'pointer';
                    svgOverlay.appendChild(pathElement);
                    
                    const annotation = {
                        id: id,
                        type: 'draw',
                        note: '',
                        paths: drawPath,
                        color: color,
                        timestamp: new Date().toISOString()
                    };
                    
                    annotations.push(annotation);
                    saveAnnotations();
                    
                    pathElement.addEventListener('click', (e) => {
                        e.stopPropagation();
                        showNotePopup(annotation, pathElement);
                    });
                }
                drawPath = [];
            }
        });
        
        // Handle mouse leave to stop drawing
        svgOverlay.addEventListener('mouseleave', (e) => {
            if (isDrawing) {
                isDrawing = false;
                const tempPath = svgOverlay.querySelector('.temp-draw-path');
                if (tempPath) {
                    tempPath.remove();
                }
                drawPath = [];
            }
        });
    }

    // Event Listeners
    if (annotationToggleToolbar) {
        annotationToggleToolbar.addEventListener('click', (e) => {
            e.stopPropagation();
            isAnnotationActive = !isAnnotationActive;
            annotationToolbar.classList.toggle('hidden');
            
            if (isAnnotationActive) {
                initSVGOverlay();
                setAnnotationMode('highlight');
                loadAnnotations();
            } else {
                setAnnotationMode('none');
            }
            localStorage.setItem('annotations_active', isAnnotationActive.toString());
        });
    }

    if (annotationToggle) {
        annotationToggle.addEventListener('click', (e) => {
            e.stopPropagation();
            isAnnotationActive = !isAnnotationActive;
            annotationToolbar.classList.toggle('hidden');
            
            if (isAnnotationActive) {
                // Initialize SVG overlay first
                if (svgOverlay) {
                    svgOverlay.style.display = 'block';
                    initSVGOverlay();
                }
                setAnnotationMode('highlight');
                loadAnnotations();
            } else {
                setAnnotationMode('none');
                if (svgOverlay) {
                    svgOverlay.style.display = 'none';
                }
            }
            localStorage.setItem('annotations_active', isAnnotationActive.toString());
        });
    }

    if (highlightBtn) {
        highlightBtn.addEventListener('click', () => {
            setAnnotationMode('highlight');
        });
    }

    if (drawBtn) {
        drawBtn.addEventListener('click', () => {
            setAnnotationMode('draw');
        });
    }

    if (viewBtn) {
        viewBtn.addEventListener('click', () => {
            annotationSidebar.classList.toggle('hidden');
            updateAnnotationList();
        });
    }

    if (clearBtn) {
        clearBtn.addEventListener('click', () => {
            if (confirm('Clear all annotations for this chapter?')) {
                annotations = [];
                saveAnnotations();
                renderAnnotations();
                updateAnnotationList();
            }
        });
    }

    if (noteSave) {
        noteSave.addEventListener('click', () => {
            if (currentAnnotationId) {
                const annotation = annotations.find(a => a.id === currentAnnotationId);
                if (annotation) {
                    annotation.note = noteText.value;
                    saveAnnotations();
                    updateAnnotationList();
                }
            }
            hideNotePopup();
        });
    }

    if (noteDelete) {
        noteDelete.addEventListener('click', () => {
            if (currentAnnotationId) {
                annotations = annotations.filter(a => a.id !== currentAnnotationId);
                saveAnnotations();
                renderAnnotations();
                updateAnnotationList();
            }
            hideNotePopup();
        });
    }

    if (noteClose) {
        noteClose.addEventListener('click', () => {
            hideNotePopup();
        });
    }

    if (sidebarClose) {
        sidebarClose.addEventListener('click', () => {
            annotationSidebar.classList.add('hidden');
        });
    }

    // Update annotation list in sidebar
    const updateAnnotationList = () => {
        if (!annotationList) return;
        annotationList.innerHTML = '';
        
        if (annotations.length === 0) {
            annotationList.innerHTML = '<p style="padding: 1rem; color: var(--text-color); opacity: 0.7;">No annotations yet</p>';
            return;
        }
        
        annotations.forEach(annotation => {
            const item = document.createElement('div');
            item.className = 'annotation-item';
            item.innerHTML = `
                <div class="annotation-item-header">
                    <span class="annotation-type">${annotation.type === 'highlight' ? '📝' : '✏️'}</span>
                    <button class="annotation-item-delete" data-id="${annotation.id}">×</button>
                </div>
                <div class="annotation-item-text">${annotation.text || 'Drawing'}</div>
                ${annotation.note ? `<div class="annotation-item-note">${annotation.note}</div>` : ''}
            `;
            
            item.querySelector('.annotation-item-delete').addEventListener('click', (e) => {
                e.stopPropagation();
                annotations = annotations.filter(a => a.id !== annotation.id);
                saveAnnotations();
                renderAnnotations();
                updateAnnotationList();
            });
            
            item.addEventListener('click', () => {
                // Scroll to annotation
                if (annotation.type === 'highlight') {
                    const mark = document.querySelector(`[data-annotation-id="${annotation.id}"]`);
                    if (mark) {
                        mark.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    }
                }
            });
            
            annotationList.appendChild(item);
        });
    };

    // Initialize on page load
    const savedActive = localStorage.getItem('annotations_active');
    if (savedActive === 'true' && annotationToolbar) {
        isAnnotationActive = true;
        annotationToolbar.classList.remove('hidden');
        if (svgOverlay) {
            svgOverlay.style.display = 'block';
            initSVGOverlay();
        }
        setAnnotationMode('highlight');
        loadAnnotations();
    } else if (svgOverlay) {
        // Ensure SVG overlay is hidden initially
        svgOverlay.style.display = 'none';
    }

    // Reload annotations when chapter changes
    const originalPushState = history.pushState;
    history.pushState = function() {
        originalPushState.apply(history, arguments);
        if (isAnnotationActive) {
            setTimeout(() => {
                loadAnnotations();
                initSVGOverlay();
            }, 100);
        }
    };

    window.addEventListener('popstate', () => {
        if (isAnnotationActive) {
            setTimeout(() => {
                loadAnnotations();
                initSVGOverlay();
            }, 100);
        }
    });

    // Update SVG overlay on resize
    window.addEventListener('resize', () => {
        if (isAnnotationActive) {
            initSVGOverlay();
        }
    });

})();

