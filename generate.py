# /// script
# dependencies = [
#   "jinja2",
#   "markdown-it-py",
#   "pyyaml",
#   "linkify-it-py",
# ]
# ///

import os
import shutil
from datetime import datetime, date
import yaml
from markdown_it import MarkdownIt
from jinja2 import FileSystemLoader, Environment

VALID_TOPICS = {
    "AI",
    "Android",
    "CMOS",
    "Databases",
    "DevOps",
    "FalkorDB",
    "Git",
    "GitHub",
    "Go",
    "JavaScript",
    "MCP",
    "Open Source",
    "Perl",
    "PHP",
    "Postgres",
    "Python",
    "Ruby",
    "Rust",
}

TOPIC_SPECIFIC_PAGES = {"Perl", "Python", "Rust", "PHP"}


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


def format_html_tables(html):
    return html.replace(
        "<table>",
        '<div class="table-container"><table class="table is-striped is-hoverable is-fullwidth">',
    ).replace("</table>", "</table></div>")


def build_page(
    events,
    template,
    layout_template,
    site_config,
    topic_filter=None,
):
    # Separate events into schedule and earlier
    schedule_events = []
    earlier_events = []

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

        title = event.get("title", "")
        link = event.get("link")
        speakers = event.get("speakers", "")
        register = event.get("register")

        event_data = {
            "date": str(date_val),
            "topics": topics,
            "title": title,
            "link": link,
            "speakers": speakers,
            "register": register,
        }

        if event_date >= current_date:
            schedule_events.append(event_data)
        else:
            earlier_events.append(event_data)

    html_content = template.render(
        schedule_events=schedule_events,
        earlier_events=earlier_events,
        topic_filter=topic_filter,
    )

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


def generate_future_events(events):
    current_date = date.today()
    future_md_lines = []
    future_text_lines = []
    for event in events:
        if not event:
            continue
        date_val = event.get("date", "")
        try:
            event_date = datetime.strptime(str(date_val).strip(), "%Y.%m.%d").date()
        except ValueError:
            event_date = date.min
        if event_date >= current_date:
            topics_val = event.get("topics")
            if isinstance(topics_val, list):
                topics = topics_val
            elif isinstance(topics_val, str):
                topics = [topics_val] if topics_val else []
            elif topics_val is None:
                topics = []
            else:
                topics = [str(topics_val)]
            topics_str = ", ".join(topics)
            title = event.get("title", "")
            register = event.get("register", "")
            speakers = event.get("speakers", "")
            if isinstance(speakers, str):
                speakers = speakers.strip()
            elif speakers is None:
                speakers = ""
            else:
                speakers = str(speakers).strip()
            by_speakers = f" by {speakers}" if speakers else ""

            line = f"* {date_val} ({topics_str}) [{title}]({register}){by_speakers}"
            future_md_lines.append(line)
            line = f"* {date_val} ({topics_str}) {title}{by_speakers} {register}"
            future_text_lines.append(line)

    with open("site/future.md", "w", encoding="utf-8") as fh:
        fh.write("\n".join(future_md_lines) + "\n")

    with open("site/future.txt", "w", encoding="utf-8") as fh:
        fh.write("\n".join(future_text_lines) + "\n")


def generate_linkedin_page(template, layout_template, site_config):
    linkedin_links = site_config.get("linkedin", [])
    linkedin_html_content = template.render(linkedin_links=linkedin_links)
    linkedin_page_meta = {"title": "Code-Maven LinkedIn Channels", "url": "/linkedin"}
    linkedin_html = layout_template.render(
        site=site_config, page=linkedin_page_meta, content=linkedin_html_content
    )

    linkedin_html_path = "site/linkedin.html"
    with open(linkedin_html_path, "w", encoding="utf-8") as f:
        f.write(linkedin_html)


def generate_facebook_page(template, layout_template, site_config):
    facebook_links = site_config.get("facebook", [])
    facebook_html_content = template.render(facebook_links=facebook_links)
    facebook_page_meta = {"title": "Code-Maven Facebook Groups", "url": "/facebook"}
    facebook_html = layout_template.render(
        site=site_config, page=facebook_page_meta, content=facebook_html_content
    )

    facebook_html_path = "site/facebook.html"
    with open(facebook_html_path, "w", encoding="utf-8") as f:
        f.write(facebook_html)


def generate_telegram_page(template, layout_template, site_config):
    telegram_links = site_config.get("telegram_links", [])
    telegram_html_content = template.render(telegram_links=telegram_links)
    telegram_page_meta = {"title": "Code-Maven Telegram Groups", "url": "/telegram"}
    telegram_html = layout_template.render(
        site=site_config, page=telegram_page_meta, content=telegram_html_content
    )

    telegram_html_path = "site/telegram.html"
    with open(telegram_html_path, "w", encoding="utf-8") as f:
        f.write(telegram_html)


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

    # Setup Jinja2 environment
    loader = FileSystemLoader("templates")
    env = Environment(loader=loader)
    layout_template = env.get_template("layout.html")
    index_template = env.get_template("index.html")
    linkedin_template = env.get_template("linkedin.html")
    facebook_template = env.get_template("facebook.html")
    telegram_template = env.get_template("telegram.html")
    calendars_template = env.get_template("calendars.html")

    md = MarkdownIt("gfm-like")

    # Ensure site/ directory exists
    os.makedirs("site", exist_ok=True)

    # Render main index.html page
    build_page(
        events=events,
        template=index_template,
        layout_template=layout_template,
        site_config=site_config,
        topic_filter=None,
    )

    # Render topic-specific pages
    for topic in TOPIC_SPECIFIC_PAGES:
        build_page(
            events=events,
            template=index_template,
            layout_template=layout_template,
            site_config=site_config,
            topic_filter=topic,
        )

    # Render all markdown files in pages/
    pages_dir = "pages"
    generated_pages = []
    if os.path.exists(pages_dir):
        for filename in os.listdir(pages_dir):
            if filename.endswith(".md"):
                md_path = os.path.join(pages_dir, filename)
                name_without_ext = os.path.splitext(filename)[0]

                with open(md_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Extract the title from the first '# ' header
                title = ""
                for line in content.splitlines():
                    if line.startswith("# "):
                        title = line[2:].strip()
                        break

                if not title:
                    title = name_without_ext.replace("-", " ").replace("_", " ").title()

                html_content = format_html_tables(md.render(content))
                page_meta = {"title": title, "url": f"/{name_without_ext}"}
                page_html = layout_template.render(
                    site=site_config, page=page_meta, content=html_content
                )

                html_path = os.path.join("site", f"{name_without_ext}.html")
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(page_html)
                generated_pages.append(html_path)

    # Render site/linkedin.html
    generate_linkedin_page(
        template=linkedin_template,
        layout_template=layout_template,
        site_config=site_config,
    )

    # Render site/facebook.html
    generate_facebook_page(
        template=facebook_template,
        layout_template=layout_template,
        site_config=site_config,
    )

    # Render site/telegram.html
    generate_telegram_page(
        template=telegram_template,
        layout_template=layout_template,
        site_config=site_config,
    )

    # Render site/calendars.html
    calendars_links = site_config.get("calendars", [])
    calendars_html_content = calendars_template.render(calendars=calendars_links)
    calendars_page_meta = {"title": "Code-Maven Calendars", "url": "/calendars"}
    calendars_html = layout_template.render(
        site=site_config, page=calendars_page_meta, content=calendars_html_content
    )

    calendars_html_path = "site/calendars.html"
    with open(calendars_html_path, "w", encoding="utf-8") as f:
        f.write(calendars_html)

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

    # Copy static/img directory to site/img
    static_img_dir = "static/img"
    if os.path.exists(static_img_dir):
        shutil.copytree(static_img_dir, "site/img", dirs_exist_ok=True)

    # Copy static/favicon directory contents to site/ root
    static_favicon_dir = "static/favicon"
    if os.path.exists(static_favicon_dir):
        for filename in os.listdir(static_favicon_dir):
            src_file = os.path.join(static_favicon_dir, filename)
            if os.path.isfile(src_file):
                shutil.copy(src_file, os.path.join("site", filename))

    # Create .nojekyll in site/ directory to bypass Jekyll
    with open("site/.nojekyll", "w", encoding="utf-8") as f:
        f.write("")

    # Generate site/future.md
    generate_future_events(events)

    print(
        f"Successfully rebuilt site/index.html, {', '.join(generated_pages)}, site/linkedin.html, site/facebook.html, site/telegram.html, site/calendars.html, site/future.md, and site/assets/css/style.css"
    )


if __name__ == "__main__":
    rebuild()
