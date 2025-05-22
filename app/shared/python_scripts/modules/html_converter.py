"""
HTML Converter Module

This module converts Markdown reports to interactive HTML with zoomable Mermaid diagrams.
It's designed to be a minimal addition to the existing report generation process.
"""

import re
import os
from pathlib import Path

def convert_markdown_to_html(markdown_content, title="Stored Procedure Analysis Report"):
    """
    Convert Markdown report to HTML with interactive features.
    
    Args:
        markdown_content (str): The complete markdown report
        title (str, optional): The title for the HTML page
        
    Returns:
        str: HTML report with interactive features
    """
    # Create HTML template with necessary libraries
    html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    
    <!-- Bootstrap for basic styling -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/css/bootstrap.min.css" rel="stylesheet">
    
    <!-- Newer version of Mermaid for better compatibility -->
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10.6.1/dist/mermaid.min.js"></script>
    
    <!-- svg-pan-zoom for interactive diagrams -->
    <script src="https://cdn.jsdelivr.net/npm/svg-pan-zoom@3.6.1/dist/svg-pan-zoom.min.js"></script>
    
    <!-- Highlight.js for SQL syntax highlighting -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/highlight.js@11.7.0/styles/github.min.css">
    <script src="https://cdn.jsdelivr.net/npm/highlight.js@11.7.0/lib/highlight.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/highlight.js@11.7.0/lib/languages/sql.min.js"></script>
    
    <style>
        body {{
            padding: 20px;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }}
        .container {{
            max-width: 1200px;
        }}
        h1 {{
            padding-bottom: 10px;
            border-bottom: 2px solid #dee2e6;
            margin-bottom: 20px;
        }}
        h2 {{
            padding-bottom: 5px;
            border-bottom: 1px solid #dee2e6;
            margin-top: 30px;
        }}
        .mermaid-container {{
            position: relative;
            margin-bottom: 20px;
            border: 1px solid #dee2e6;
            border-radius: 4px;
            overflow: auto;
            padding: 10px;
        }}
        .zoom-controls {{
            position: absolute;
            top: 10px;
            right: 10px;
            z-index: 100;
            background: rgba(255, 255, 255, 0.7);
            border-radius: 4px;
            padding: 5px;
        }}
        pre {{
            padding: 15px;
            background-color: #f8f9fa;
            border-radius: 4px;
        }}
        .table {{
            font-size: 0.9rem;
            table-layout: fixed;
            width: 100%;
        }}
        
        /* Specific column widths for Process Steps table */
        .table.process-steps th:nth-child(1) {{ width: 10%; }} /* Step ID */
        .table.process-steps th:nth-child(2) {{ width: 10%; }} /* Step Type */
        .table.process-steps th:nth-child(3) {{ width: 15%; }} /* Business Function ID */
        .table.process-steps th:nth-child(4) {{ width: 20%; }} /* Business Function Name */
        .table.process-steps th:nth-child(5) {{ width: 45%; }} /* Business Function Description */
        
        /* Specific column widths for Test Scenarios table */
        .table.test-scenarios th:nth-child(1) {{ width: 15%; }} /* ID/Type */
        .table.test-scenarios th:nth-child(2) {{ width: 40%; }} /* Description */
        .table.test-scenarios th:nth-child(3) {{ width: 45%; }} /* Considerations */
        
        /* Apply word wrap to table cells */
        .table td, .table th {{
            word-wrap: break-word;
            overflow-wrap: break-word;
        }}
        button.zoom-btn {{
            margin: 0 5px;
            cursor: pointer;
        }}
        .mermaid {{
            width: 100%;
            overflow: auto;
        }}
        .diagram-container {{
            margin-top: 20px;
            min-height: 400px;
        }}
        .mermaid-fallback {{
            display: none;
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 4px;
            margin-top: 10px;
            white-space: pre-wrap;
            font-family: monospace;
            max-height: 400px;
            overflow: auto;
        }}
        .show-code-btn {{
            margin-top: 10px;
        }}
        /* For very large diagrams */
        .large-diagram {{
            max-height: 800px;
            overflow: auto;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div id="content">
            <!-- Markdown content will be inserted here -->
        </div>
    </div>
    
    <script>
        // Set up event handlers when document is loaded
        document.addEventListener('DOMContentLoaded', function() {{
            // Check if diagrams are very large
            const mermaidContainers = document.querySelectorAll('.mermaid-fallback');
            mermaidContainers.forEach(function(container) {{
                if (container.textContent.length > 10000) {{
                    container.style.display = 'block';
                    const btn = container.parentElement.querySelector('.show-code-btn');
                    if (btn) btn.textContent = 'Hide Source Code';
                    
                    const status = container.parentElement.querySelector('.mermaid-render-status');
                    if (status) {{
                        status.textContent = 'This diagram is very large. Source code is shown below, rendering may take time.';
                    }}
                }}
            }});
            
            // Apply syntax highlighting to regular code blocks
            document.querySelectorAll('pre code').forEach(function(block) {{
                hljs.highlightBlock(block);
            }});
        }});
        
        // Configure Mermaid with optimal settings for large diagrams
        mermaid.initialize({{
            startOnLoad: true,
            theme: 'default',
            logLevel: 'error',
            securityLevel: 'loose',
            flowchart: {{
                useMaxWidth: false,
                htmlLabels: true,
                curve: 'basis'
            }},
            fontSize: 12,
            fontFamily: 'arial',
            themeVariables: {{
                lineColor: '#999',
                primaryColor: '#326ce5',
                primaryTextColor: '#fff',
                primaryBorderColor: '#326ce5',
                secondaryColor: '#f9f9f9',
                secondaryTextColor: '#666',
                secondaryBorderColor: '#f9f9f9'
            }}
        }});
        
        function toggleCodeView(buttonElement) {{
            const fallback = buttonElement.parentElement.querySelector('.mermaid-fallback');
            if (fallback.style.display === 'none' || !fallback.style.display) {{
                fallback.style.display = 'block';
                buttonElement.textContent = 'Hide Source Code';
            }} else {{
                fallback.style.display = 'none';
                buttonElement.textContent = 'Show Source Code';
            }}
        }}
        
        // Setup zoom after Mermaid has rendered diagrams
        function setupZoom() {{
            document.querySelectorAll('.mermaid svg').forEach(function(svg, index) {{
                if (!svg) return;
                
                try {{
                    // Get the container
                    const container = svg.closest('.mermaid-container');
                    
                    // Set a reasonable size for the SVG if it's too small or not specified
                    const viewBox = svg.getAttribute('viewBox');
                    if (viewBox) {{
                        const vbParts = viewBox.split(' ').map(Number);
                        const vbWidth = vbParts[2];
                        const vbHeight = vbParts[3];
                        
                        if (vbWidth > 1000 || vbHeight > 1000) {{
                            // For very large diagrams, add the large-diagram class
                            svg.closest('.diagram-container').classList.add('large-diagram');
                        }}
                    }}
                    
                    // Initialize svg-pan-zoom
                    const panZoomInstance = svgPanZoom(svg, {{
                        zoomEnabled: true,
                        controlIconsEnabled: false,
                        fit: true,
                        center: true,
                        minZoom: 0.1,
                        maxZoom: 10,
                        beforePan: function() {{
                            return {{x: true, y: true}};
                        }}
                    }});
                    
                    // Connect zoom controls
                    const controls = container.querySelector('.zoom-controls');
                    if (controls) {{
                        controls.querySelector('.zoom-in').addEventListener('click', function() {{ panZoomInstance.zoomIn(); }});
                        controls.querySelector('.zoom-out').addEventListener('click', function() {{ panZoomInstance.zoomOut(); }});
                        controls.querySelector('.zoom-reset').addEventListener('click', function() {{ panZoomInstance.reset(); }});
                    }}
                    
                    // Update status
                    container.querySelector('.mermaid-render-status').textContent = 'Diagram rendered successfully.';
                    container.querySelector('.mermaid-render-status').className = 'text-success mt-2 mermaid-render-status';
                }} catch (error) {{
                    console.error('Error setting up zoom:', error);
                    
                    // Get the container
                    const container = svg.closest('.mermaid-container');
                    if (container) {{
                        container.querySelector('.mermaid-render-status').textContent = 
                            'Error setting up zoom. The diagram is visible but zooming may not work.';
                    }}
                }}
            }});
        }}
        
        // Wait for Mermaid to finish rendering, then setup zoom
        document.addEventListener('DOMContentLoaded', function() {{
            // Try to detect when Mermaid has finished
            const checkMermaidRendered = setInterval(function() {{
                // Check if any SVGs have been created
                const mermaidSvgs = document.querySelectorAll('.mermaid svg');
                if (mermaidSvgs.length > 0) {{
                    clearInterval(checkMermaidRendered);
                    setupZoom();
                }}
            }}, 500);
            
            // Safety timeout - if after 10 seconds we still don't have SVGs, show fallbacks
            setTimeout(function() {{
                clearInterval(checkMermaidRendered);
                
                // Check if any containers don't have SVGs
                document.querySelectorAll('.diagram-container').forEach(function(container) {{
                    if (!container.querySelector('svg')) {{
                        const parentContainer = container.closest('.mermaid-container');
                        if (parentContainer) {{
                            parentContainer.querySelector('.mermaid-render-status').textContent = 
                                'Diagram failed to render. View the source code below instead.';
                            parentContainer.querySelector('.mermaid-render-status').className = 
                                'text-danger mt-2 mermaid-render-status';
                                
                            const fallback = parentContainer.querySelector('.mermaid-fallback');
                            if (fallback) {{
                                fallback.style.display = 'block';
                                parentContainer.querySelector('.show-code-btn').textContent = 'Hide Source Code';
                            }}
                        }}
                    }}
                }});
            }}, 10000);
        }});
    </script>
</body>
</html>"""

    # Process the markdown content to prepare it for HTML insertion
    # 1. Convert mermaid code blocks to be interactive with a fallback option
    def mermaid_replacer(match):
        diagram_code = match.group(1).strip()
        
        # Create an index for this diagram
        diagram_index = mermaid_replacer.counter
        mermaid_replacer.counter += 1
        
        # Create a container with zoom controls and both rendered and fallback views
        return f'''<div class="mermaid-container">
            <div class="zoom-controls">
                <button class="zoom-btn zoom-in btn btn-sm btn-outline-secondary">+</button>
                <button class="zoom-btn zoom-out btn btn-sm btn-outline-secondary">-</button>
                <button class="zoom-btn zoom-reset btn btn-sm btn-outline-secondary">Reset</button>
            </div>
            <div class="diagram-container">
                <div class="mermaid">
{diagram_code}
                </div>
            </div>
            <div class="text-muted mt-2 mermaid-render-status">Rendering diagram...</div>
            <button class="btn btn-sm btn-outline-secondary show-code-btn" onclick="toggleCodeView(this)">Show Source Code</button>
            <div class="mermaid-fallback">{diagram_code}</div>
        </div>'''
    
    # Initialize counter for diagram indexing
    mermaid_replacer.counter = 0
    
    # Replace mermaid code blocks
    content_with_interactive_mermaid = re.sub(
        r'```mermaid\n([\s\S]*?)\n```', 
        mermaid_replacer, 
        markdown_content
    )
    
    # 2. Replace markdown headers with HTML
    content_with_html_headers = re.sub(
        r'# (.*)\n', 
        r'<h1>\1</h1>\n', 
        content_with_interactive_mermaid
    )
    content_with_html_headers = re.sub(
        r'## (.*)\n', 
        r'<h2>\1</h2>\n', 
        content_with_html_headers
    )
    content_with_html_headers = re.sub(
        r'### (.*)\n', 
        r'<h3>\1</h3>\n', 
        content_with_html_headers
    )
    
    # 3. Replace markdown tables with HTML tables
    def table_replacer(match):
        table_content = match.group(0)
        lines = table_content.strip().split('\n')
        
        # Skip empty tables
        if len(lines) < 3:
            return table_content
            
        # Process header row
        header_cells = [cell.strip() for cell in lines[0].split('|')]
        header_cells = [cell for cell in header_cells if cell]  # Remove empty cells
        
        # Skip separator row
        
        # Determine table type for CSS class
        table_class = "table-striped table-hover"
        if "Step ID" in header_cells and "Business Function ID" in header_cells:
            table_class += " process-steps"
        elif "ID / Type" in header_cells and "Description" in header_cells and "Considerations" in header_cells:
            table_class += " test-scenarios"
        elif "ID" in header_cells and "Type" in header_cells and "Description" in header_cells and "Considerations" in header_cells:
            table_class += " test-scenarios"
        elif "ID" in header_cells and "Checks that" in header_cells:
            table_class += " test-scenarios"
        
        # Process data rows
        html_table = f'<div class="table-responsive"><table class="table {table_class}">\n<thead>\n<tr>\n'
        
        # Add header cells
        for cell in header_cells:
            html_table += f'  <th>{cell}</th>\n'
        
        html_table += '</tr>\n</thead>\n<tbody>\n'
        
        # Add data rows (skip header and separator)
        for line in lines[2:]:
            if not line.strip():
                continue
                
            cells = [cell.strip() for cell in line.split('|')]
            cells = [cell for cell in cells if cell != '']  # Remove empty cells from start/end
            
            html_table += '<tr>\n'
            for cell in cells:
                html_table += f'  <td>{cell}</td>\n'
            html_table += '</tr>\n'
            
        html_table += '</tbody>\n</table></div>\n'
        return html_table
    
    # Find and replace markdown tables
    table_pattern = r'\|[^\n]+\|\n\|[-:| ]+\|\n(?:\|[^\n]+\|\n)+'
    content_with_html_tables = re.sub(table_pattern, table_replacer, content_with_html_headers)
    
    # 4. Convert code blocks to HTML (except those already processed)
    def code_replacer(match):
        language = match.group(1)
        code_content = match.group(2)
        
        # If it's a mermaid block, we've already processed it
        if language.lower() == 'mermaid':
            return match.group(0)
        
        return f'<pre><code class="{language}">{code_content}</code></pre>'
    
    content_with_html_code = re.sub(
        r'```(\w+)\n([\s\S]*?)\n```', 
        code_replacer, 
        content_with_html_tables
    )
    
    # 5. Replace simple markdown formatting
    # Bold
    content_with_formatting = re.sub(
        r'\*\*(.*?)\*\*', 
        r'<strong>\1</strong>', 
        content_with_html_code
    )
    # Italic
    content_with_formatting = re.sub(
        r'\*(.*?)\*', 
        r'<em>\1</em>', 
        content_with_formatting
    )
    
    # Insert processed content into HTML template
    html_content = html_template.replace('<div id="content">', f'<div id="content">\n{content_with_formatting}')
    
    return html_content

def generate_html_report(markdown_content, output_path, title=None):
    """
    Generate an HTML report from the markdown content and save it to the specified path.
    
    Args:
        markdown_content (str): The markdown report content
        output_path (str): Path where to save the HTML file
        title (str, optional): The title for the HTML page
    
    Returns:
        str: The path to the generated HTML file
    """
    # If title not provided, try to extract it from the markdown
    if not title:
        title_match = re.search(r'# (.*)\n', markdown_content)
        if title_match:
            title = title_match.group(1)
        else:
            title = "Stored Procedure Analysis Report"
    
    # Convert markdown to HTML
    html_content = convert_markdown_to_html(markdown_content, title)
    
    # If output_path is a markdown file path, change extension to html
    if output_path.lower().endswith('.md'):
        output_path = output_path[:-3] + '.html'
    
    # Make sure the directory exists
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    
    # Write the HTML content to the file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    return output_path
