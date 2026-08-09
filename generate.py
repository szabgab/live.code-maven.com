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

VALID_TOPICS = {
    "AI",
    "Databases",
    "FalkorDB",
    "Git",
    "GitHub",
    "JavaScript",
    "MCP",
    "Open Source",
    "Perl",
    "Python",
    "Rust",
}


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
    header_str = (
        "| "
        + " | ".join(f"{h:<{col_widths[idx]}}" for idx, h in enumerate(headers))
        + " |"
    )
    # Build separator row
    sep_str = (
        "| " + " | ".join("-" * col_widths[idx] for idx in range(len(headers))) + " |"
    )

    # Build data rows
    row_strs = []
    for row in rows:
        row_str = (
            "| "
            + " | ".join(f"{cell:<{col_widths[idx]}}" for idx, cell in enumerate(row))
            + " |"
        )
        row_strs.append(row_str)

    return "\n".join([header_str, sep_str] + row_strs)


def rebuild():
    # Load events
    yaml_path = "events.yaml"
    if not os.path.exists(yaml_path):
        raise FileNotFoundError(f"YAML file not found at {yaml_path}")

    with open(yaml_path, "r", encoding="utf-8") as f:
        events = yaml.safe_load(f)

    if not events:
        events = []

    # Verify chronological order of event dates
    prev_date = None
    for idx, event in enumerate(events):
        if not event:
            continue
        date_val = event.get("date")
        if not date_val:
            raise ValueError(f"Event at index {idx} is missing a date field")
        try:
            event_date = datetime.strptime(str(date_val).strip(), "%Y.%m.%d").date()
        except ValueError as e:
            raise ValueError(
                f"Event at index {idx} has an invalid date format: '{date_val}'"
            ) from e

        if prev_date is not None and event_date < prev_date:
            raise ValueError(
                f"Events are not in chronological order: event at index {idx} with date {date_val} comes after a later date {prev_date.strftime('%Y.%m.%d')}"
            )
        prev_date = event_date

        # Verify topics and their casing
        topics_val = event.get("topics")
        if isinstance(topics_val, list):
            topics_list = topics_val
        elif isinstance(topics_val, str):
            topics_list = [topics_val] if topics_val else []
        elif topics_val is None:
            topics_list = []
        else:
            topics_list = [str(topics_val)]

        for topic in topics_list:
            if topic not in VALID_TOPICS:
                # Check case-insensitively
                matching = [t for t in VALID_TOPICS if t.lower() == topic.lower()]
                if matching:
                    raise ValueError(
                        f"Topic '{topic}' at index {idx} has incorrect casing. Expected '{matching[0]}'"
                    )
                else:
                    raise ValueError(
                        f"Topic '{topic}' at index {idx} is not in the list of valid topics: {sorted(list(VALID_TOPICS))}"
                    )

    # Load config from static/_config.yml
    config_path = "static/_config.yml"
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            site_config = yaml.safe_load(f)
    else:
        site_config = {}

    # Load index template
    template_path = "pages/index.md"
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Template file not found at {template_path}")

    with open(template_path, "r", encoding="utf-8") as f:
        template = f.read()

    # Setup Jinja2 environment
    loader = FileSystemLoader("templates")
    env = Environment(loader=loader)
    layout_template = env.get_template("layout.html")

    md = MarkdownIt("gfm-like")

    def format_html_tables(html):
        return html.replace(
            "<table>",
            '<div class="table-container"><table class="table is-striped is-hoverable is-fullwidth">',
        ).replace("</table>", "</table></div>")

    def build_page(topic_filter=None):
        # Separate events into schedule and earlier
        schedule_rows = []
        earlier_rows = []

        current_date = date.today()

        for event in events:
            if not event:
                continue

            topics_val = event.get("topics")
            if isinstance(topics_val, list):
                topics = topics_val
            elif isinstance(topics_val, str):
                topics = [topics_val] if topics_val else []
            elif topics_val is None:
                topics = []
            else:
                topics = [str(topics_val)]

            if topic_filter:
                if topic_filter.lower() not in [t.lower() for t in topics]:
                    continue

            date_val = event.get("date", "")
            try:
                event_date = datetime.strptime(str(date_val).strip(), "%Y.%m.%d").date()
            except ValueError:
                # Fallback for malformed dates: classify as past
                event_date = date.min

            topics_cell = "<br>".join(str(t) for t in topics)
            title = event.get("title", "")
            link = event.get("link")
            speakers = event.get("speakers", "")
            register = event.get("register")

            # Format title cell
            if link:
                title_cell = f"[{title}]({link})"
            else:
                title_cell = title

            if event_date >= current_date:
                # Schedule event (future or today)
                # Format register link
                if register:
                    if register.startswith("http://") or register.startswith(
                        "https://"
                    ):
                        register_cell = f"[register]({register})"
                    else:
                        register_cell = register
                else:
                    register_cell = ""
                schedule_rows.append(
                    [str(date_val), topics_cell, title_cell, speakers, register_cell]
                )
            else:
                # Earlier event (past)
                earlier_rows.append([str(date_val), topics_cell, title_cell, speakers])

        # Format tables
        schedule_headers = ["When", "Topics", "Title", "Who", "Register"]
        schedule_table_md = format_table(schedule_headers, schedule_rows)

        earlier_headers = ["When", "Topics", "Video recordings and notes", "Who"]
        earlier_table_md = format_table(earlier_headers, earlier_rows)

        # Replace placeholders
        page_md = template
        if topic_filter:
            page_md = page_md.replace(
                "# Code-Maven Live events",
                f"# Code-Maven Live {topic_filter} events",
            )

        output_content = page_md.replace("{{ SCHEDULE_TABLE }}", schedule_table_md)
        output_content = output_content.replace("{{ EARLIER_TABLE }}", earlier_table_md)

        html_content = format_html_tables(md.render(output_content))

        if topic_filter:
            page_title = f"Code-Maven community online {topic_filter} events"
            page_url = f"/{topic_filter.lower()}.html"
            out_filename = f"site/{topic_filter.lower()}.html"
        else:
            page_title = "Code-Maven community online events"
            page_url = "/"
            out_filename = "site/index.html"

        page_meta = {"title": page_title, "url": page_url}
        html_output = layout_template.render(
            site=site_config, page=page_meta, content=html_content
        )

        with open(out_filename, "w", encoding="utf-8") as f:
            f.write(html_output)

    # Ensure site/ directory exists
    os.makedirs("site", exist_ok=True)

    # Render main index.html page
    build_page(None)

    # Render topic-specific pages
    for topic in ["Perl", "Python", "Rust"]:
        build_page(topic)

    # Generate site/about.md from pages/about.md (literally as markdown)
    about_path = "pages/about.md"
    if not os.path.exists(about_path):
        raise FileNotFoundError(f"About file not found at {about_path}")

    with open(about_path, "r", encoding="utf-8") as f:
        about_content = f.read()

    about_output_path = "site/about.md"
    with open(about_output_path, "w", encoding="utf-8") as f:
        f.write(about_content)

    # Also render site/about.html (using the Jinja2 template)
    about_html_content = format_html_tables(md.render(about_content))
    about_page_meta = {"title": "About the Code-Maven Live events", "url": "/about"}
    about_html = layout_template.render(
        site=site_config, page=about_page_meta, content=about_html_content
    )

    about_html_path = "site/about.html"
    with open(about_html_path, "w", encoding="utf-8") as f:
        f.write(about_html)

    # Compile static/assets/css/style.scss to site/assets/css/style.css by removing front matter
    scss_path = "static/assets/css/style.scss"
    if os.path.exists(scss_path):
        with open(scss_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        css_lines = []
        in_front_matter = False
        front_matter_count = 0
        for line in lines:
            if line.strip() == "---":
                front_matter_count += 1
                if front_matter_count <= 2:
                    in_front_matter = front_matter_count == 1
                    continue
            if not in_front_matter:
                css_lines.append(line)

        # Ensure site/assets/css/ directory exists
        os.makedirs("site/assets/css", exist_ok=True)
        css_path = "site/assets/css/style.css"
        with open(css_path, "w", encoding="utf-8") as f:
            f.writelines(css_lines)

    # Create .nojekyll in site/ directory to bypass Jekyll
    with open("site/.nojekyll", "w", encoding="utf-8") as f:
        f.write("")

    print(
        f"Successfully rebuilt site/index.html, site/about.html, site/about.md, and site/assets/css/style.css"
    )


if __name__ == "__main__":
    rebuild()
