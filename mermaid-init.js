// Mermaid diagram support for mdBook
// Loads mermaid.js from CDN and initializes rendering

(function() {
    // Load mermaid from CDN
    var script = document.createElement('script');
    script.src = 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js';
    script.onload = function() {
        mermaid.initialize({
            startOnLoad: true,
            theme: 'default',
            securityLevel: 'loose',
            logLevel: 'error',
            flowchart: {
                useMaxWidth: true,
                htmlLabels: true,
                curve: 'basis'
            },
            sequence: {
                useMaxWidth: true,
                wrap: true
            },
            gantt: {
                useMaxWidth: true
            }
        });
        // Re-render on page navigation (mdBook uses pushState)
        var observer = new MutationObserver(function() {
            var mermaidBlocks = document.querySelectorAll('code.language-mermaid');
            if (mermaidBlocks.length > 0) {
                mermaid.run();
            }
        });
        observer.observe(document.getElementById('content'), {
            childList: true,
            subtree: true
        });
    };
    document.head.appendChild(script);

    // Also handle inline mermaid divs that mdBook might generate
    document.addEventListener('DOMContentLoaded', function() {
        // Convert ```mermaid code blocks to div.mermaid for rendering
        var blocks = document.querySelectorAll('code.language-mermaid');
        blocks.forEach(function(block) {
            var div = document.createElement('div');
            div.className = 'mermaid';
            div.textContent = block.textContent;
            block.parentNode.replaceChild(div, block);
        });
    });
})();
