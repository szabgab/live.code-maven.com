# /// script
# dependencies = [
#   "jinja2",
#   "markdown-it-py",
#   "pyyaml",
#   "linkify-it-py",
# ]
# ///

import os
from datetime import datetime, date
import yaml
from markdown_it import MarkdownIt
from jinja2 import FileSystemLoader, Environment

def format_table(headers, rows):
    """
    Format a markdown table given headers and list of rows (lists of cell strings).
    Pads all cells dynamically to match the maximum width in each column.
    """
    if not rows:
        return ""
        
    # Calculate column widths
    col_widths = [len(h) for h in headers]
    for row in rows:
        for idx, cell in enumerate(row):
            if idx < len(col_widths):
                col_widths[idx] = max(col_widths[idx], len(cell))
            else:
                col_widths.append(len(cell))
                
    # Build header row
    header_str = "| " + " | ".join(f"{h:<{col_widths[idx]}}" for idx, h in enumerate(headers)) + " |"
    # Build separator row
    sep_str = "| " + " | ".join("-" * col_widths[idx] for idx in range(len(headers))) + " |"
    
    # Build data rows
    row_strs = []
    for row in rows:
        row_str = "| " + " | ".join(f"{cell:<{col_widths[idx]}}" for idx, cell in enumerate(row)) + " |"
        row_strs.append(row_str)
        
    return "\n".join([header_str, sep_str] + row_strs)

def rebuild():
    # Load events
    yaml_path = 'events.yaml'
    if not os.path.exists(yaml_path):
        raise FileNotFoundError(f"YAML file not found at {yaml_path}")
        
    with open(yaml_path, 'r', encoding='utf-8') as f:
        events = yaml.safe_load(f)
        
    # Load config from static/_config.yml
    config_path = 'static/_config.yml'
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            site_config = yaml.safe_load(f)
    else:
        site_config = {}
        
    # Load index template
    template_path = 'pages/index.md'
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Template file not found at {template_path}")
        
    with open(template_path, 'r', encoding='utf-8') as f:
        template = f.read()
        
    # Separate events into schedule and earlier
    schedule_rows = []
    earlier_rows = []
    
    current_date = date.today()
    
    for event in events:
        date_val = event.get('date', '')
        try:
            event_date = datetime.strptime(str(date_val).strip(), "%Y.%m.%d").date()
        except ValueError:
            # Fallback for malformed dates: classify as past
            event_date = date.min
            
        language = event.get('language', '')
        title = event.get('title', '')
        link = event.get('link')
        speakers = event.get('speakers', '')
        register = event.get('register')
        
        # Format title cell
        if link:
            title_cell = f"[{title}]({link})"
        else:
            title_cell = title
            
        if event_date >= current_date:
            # Schedule event (future or today)
            # Format register link
            if register:
                if register.startswith('http://') or register.startswith('https://'):
                    register_cell = f"[register]({register})"
                else:
                    register_cell = register
            else:
                register_cell = ""
            schedule_rows.append([str(date_val), language, title_cell, speakers, register_cell])
        else:
            # Earlier event (past)
            earlier_rows.append([str(date_val), language, title_cell, speakers])
            
    # Format tables
    schedule_headers = ['When', 'Language', 'Title', 'Who', 'Register']
    schedule_table_md = format_table(schedule_headers, schedule_rows)
    
    earlier_headers = ['When', 'Language', 'Video recordings and notes', 'Who']
    earlier_table_md = format_table(earlier_headers, earlier_rows)
    
    # Replace placeholders
    output = template.replace('{{ SCHEDULE_TABLE }}', schedule_table_md)
    output = output.replace('{{ EARLIER_TABLE }}', earlier_table_md)
    
    # Convert index markdown to HTML
    md = MarkdownIt('gfm-like')
    index_html_content = md.render(output)
    
    # Setup Jinja2 environment
    loader = FileSystemLoader('templates')
    env = Environment(loader=loader)
    layout_template = env.get_template('layout.html')
    
    # Ensure site/ directory exists
    os.makedirs('site', exist_ok=True)
    
    # Render index.html with Jinja2
    index_page_meta = {
        'title': 'Upcoming and Recordings',
        'url': '/'
    }
    index_html = layout_template.render(site=site_config, page=index_page_meta, content=index_html_content)
    
    index_html_path = 'site/index.html'
    with open(index_html_path, 'w', encoding='utf-8') as f:
        f.write(index_html)
        
    # Generate site/about.md from pages/about.md (literally as markdown)
    about_path = 'pages/about.md'
    if not os.path.exists(about_path):
        raise FileNotFoundError(f"About file not found at {about_path}")
        
    with open(about_path, 'r', encoding='utf-8') as f:
        about_content = f.read()
        
    about_output_path = 'site/about.md'
    with open(about_output_path, 'w', encoding='utf-8') as f:
        f.write(about_content)
        
    # Also render site/about.html (using the Jinja2 template)
    about_html_content = md.render(about_content)
    about_page_meta = {
        'title': 'About the Code-Maven Live events',
        'url': '/about'
    }
    about_html = layout_template.render(site=site_config, page=about_page_meta, content=about_html_content)
    
    about_html_path = 'site/about.html'
    with open(about_html_path, 'w', encoding='utf-8') as f:
        f.write(about_html)
        
    # Compile static/assets/css/style.scss to site/assets/css/style.css by removing front matter
    scss_path = 'static/assets/css/style.scss'
    if os.path.exists(scss_path):
        with open(scss_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        css_lines = []
        in_front_matter = False
        front_matter_count = 0
        for line in lines:
            if line.strip() == '---':
                front_matter_count += 1
                if front_matter_count <= 2:
                    in_front_matter = (front_matter_count == 1)
                    continue
            if not in_front_matter:
                css_lines.append(line)
                
        # Ensure site/assets/css/ directory exists
        os.makedirs('site/assets/css', exist_ok=True)
        css_path = 'site/assets/css/style.css'
        with open(css_path, 'w', encoding='utf-8') as f:
            f.writelines(css_lines)
            
    # Copy CNAME if it exists
    cname_src = 'static/CNAME'
    if os.path.exists(cname_src):
        import shutil
        shutil.copy(cname_src, 'site/CNAME')
            
    # Create .nojekyll in site/ directory to bypass Jekyll
    with open('site/.nojekyll', 'w', encoding='utf-8') as f:
        f.write('')
        
    print(f"Successfully rebuilt site/index.html, site/about.html, site/about.md, and site/assets/css/style.css")

if __name__ == '__main__':
    rebuild()
