import os
import yaml

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
        
    # Load template
    template_path = 'templates/index.md'
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Template file not found at {template_path}")
        
    with open(template_path, 'r', encoding='utf-8') as f:
        template = f.read()
        
    # Separate events into schedule and earlier
    schedule_rows = []
    earlier_rows = []
    
    for event in events:
        date = event.get('date', '')
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
            
        if register:
            # Schedule event
            # Format register link
            if register.startswith('http://') or register.startswith('https://'):
                register_cell = f"[register]({register})"
            else:
                register_cell = register
            schedule_rows.append([date, language, title_cell, speakers, register_cell])
        else:
            # Earlier event
            earlier_rows.append([date, language, title_cell, speakers])
            
    # Format tables
    schedule_headers = ['When', 'Language', 'Title', 'Who', 'Register']
    schedule_table_md = format_table(schedule_headers, schedule_rows)
    
    earlier_headers = ['When', 'Language', 'Video recordings and notes', 'Who']
    earlier_table_md = format_table(earlier_headers, earlier_rows)
    
    # Replace placeholders
    output = template.replace('{{ SCHEDULE_TABLE }}', schedule_table_md)
    output = output.replace('{{ EARLIER_TABLE }}', earlier_table_md)
    
    # Write back to docs/index.md
    output_path = 'docs/index.md'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(output)
        
    print(f"Successfully rebuilt {output_path}")

if __name__ == '__main__':
    rebuild()
