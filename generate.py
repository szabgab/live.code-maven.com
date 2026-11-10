# /// script
# dependencies = [
#   "jinja2",
#   "markdown-it-py",
#   "pyyaml",
#   "linkify-it-py",
#   "requests",
#   "icalendar",
# ]
# ///

import os
import re
import shutil
from datetime import datetime, date
import requests
import icalendar
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


def parse_event_date(date_val):
    date_str = str(date_val).strip()
    try:
        dt = datetime.strptime(date_str, "%Y.%m.%d")
        return dt.date(), None
    except ValueError:
        pass
    dt = datetime.strptime(date_str, "%Y.%m.%dT%H:%M:%S%z")
    return dt.date(), dt


def get_event_topics(event):
    topics_val = event.get("topics")
    if isinstance(topics_val, list):
        return topics_val
    elif isinstance(topics_val, str):
        return [topics_val] if topics_val else []
    elif topics_val is None:
        return []
    else:
        return [str(topics_val)]


def partition_events(events, topic_filter=None):
    schedule_events = []
    earlier_events = []

    current_date = date.today()

    for event in events:
        if not event:
            continue

        topics = get_event_topics(event)

        if topic_filter and topic_filter.lower() not in [t.lower() for t in topics]:
            continue

        date_val = event.get("date", "")
        event_date, event_dt = parse_event_date(date_val)

        if event_date >= current_date:
            display_date = event_dt.strftime("%Y.%m.%d %H:%M%z")
            iso_date = event_dt.isoformat()
            target_list = schedule_events
        else:
            display_date = event_date.strftime("%Y.%m.%d")
            iso_date = None
            target_list = earlier_events

        target_list.append(
            {
                "date": display_date,
                "iso_date": iso_date,
                "topics": topics,
                "title": event.get("title", ""),
                "link": event.get("link"),
                "speakers": event.get("speakers", ""),
                "register": event.get("register"),
            }
        )

    return schedule_events, earlier_events


def render_and_write_page(layout_template, site_config, title, url, content, out_path):
    page_meta = {"title": title, "url": url}
    html_output = layout_template.render(
        site=site_config, page=page_meta, content=content
    )
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html_output)


def build_page(
    events,
    template,
    layout_template,
    site_config,
    md,
    topic_filter=None,
    past_template=None,
):
    schedule_events, earlier_events = partition_events(events, topic_filter)

    if topic_filter:
        topic_data = site_config["topics"].get(topic_filter) or {}
        topic_title = topic_data.get("title", topic_filter)
        maven_name = f"{topic_title} Maven"
        raw_text = topic_data.get("text")
        topic_text = format_html_tables(md.render(str(raw_text))) if raw_text else None
    else:
        topic_data = None
        maven_name = "Code-Maven"
        topic_text = None

    html_content = template.render(
        schedule_events=schedule_events,
        earlier_events=earlier_events if topic_filter else [],
        topic_filter=topic_filter,
        maven_name=maven_name,
        topic_data=topic_data,
        topic_text=topic_text,
    )

    if topic_filter:
        page_title = f"{maven_name} community online events"
        page_url = f"/{topic_filter.lower()}.html"
        out_filename = f"site/{topic_filter.lower()}.html"
        render_site_config = {**site_config, "title": page_title}
    else:
        page_title = "Code-Maven community online events"
        page_url = "/"
        out_filename = "site/index.html"
        render_site_config = site_config

        if past_template is not None:
            past_html_content = past_template.render(
                earlier_events=earlier_events,
            )
            render_and_write_page(
                layout_template=layout_template,
                site_config=site_config,
                title="Code-Maven community online past events",
                url="/past",
                content=past_html_content,
                out_path="site/past.html",
            )

    render_and_write_page(
        layout_template=layout_template,
        site_config=render_site_config,
        title=page_title,
        url=page_url,
        content=html_content,
        out_path=out_filename,
    )


def generate_future_events(events):
    current_date = date.today()
    future_md_lines = []
    future_text_lines = []
    for event in events:
        if not event:
            continue
        date_val = event.get("date", "")
        try:
            event_date, _ = parse_event_date(date_val)
        except ValueError:
            event_date = date.min
        if event_date >= current_date:
            topics = get_event_topics(event)
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


def get_items(site_config, field):
    links = set()
    items = []
    for topic, data in site_config.get("topics").items():
        if data is None:
            continue
        item = data.get(field)
        if item is None:
            continue
        if item["url"] in links:
            continue
        links.add(item["url"])
        items.append(item)
    return items


def generate_links_page(
    template, layout_template, site_config, field, context_key, title, url, out_path
):
    items = get_items(site_config, field)
    html_content = template.render(**{context_key: items})
    render_and_write_page(
        layout_template=layout_template,
        site_config=site_config,
        title=title,
        url=url,
        content=html_content,
        out_path=out_path,
    )


def generate_topics_page(template, layout_template, site_config, events):
    topic_counts = {topic: 0 for topic in site_config["topics"].keys()}
    for event in events:
        if not event:
            continue
        event_topics = get_event_topics(event)

        for t in event_topics:
            if t in topic_counts:
                topic_counts[t] += 1

    topics_list = [
        {"name": topic, "count": count} for topic, count in topic_counts.items()
    ]

    topics_html_content = template.render(topics=topics_list)
    render_and_write_page(
        layout_template=layout_template,
        site_config=site_config,
        title="Code-Maven Topics",
        url="/topics",
        content=topics_html_content,
        out_path="site/topics.html",
    )


def generate_redirects(site_config):
    redirects = site_config.get("redirect") or {}
    for source, target in redirects.items():
        target_url = (
            target if target.startswith(("http://", "https://", "/")) else f"/{target}"
        )
        html = f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>Redirecting...</title>
    <link rel="canonical" href="{target_url}">
    <meta http-equiv="refresh" content="0; url={target_url}">
    <script>window.location.href = "{target_url}";</script>
  </head>
  <body>
    <p>Redirecting to <a href="{target_url}">{target}</a>...</p>
  </body>
</html>
"""
        out_path = os.path.join("site", f"{source}.html")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)


def compile_style_scss():
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


def copy_static_files():
    # Copy static/img directory to site/img
    static_img_dir = "static/img"
    if os.path.exists(static_img_dir):
        shutil.copytree(static_img_dir, "site/img", dirs_exist_ok=True)

    # Copy static/js directory to site/js
    static_js_dir = "static/js"
    if os.path.exists(static_js_dir):
        shutil.copytree(static_js_dir, "site/js", dirs_exist_ok=True)

    # Copy static/favicon directory contents to site/ root
    static_favicon_dir = "static/favicon"
    if os.path.exists(static_favicon_dir):
        for filename in os.listdir(static_favicon_dir):
            src_file = os.path.join(static_favicon_dir, filename)
            if os.path.isfile(src_file):
                shutil.copy(src_file, os.path.join("site", filename))


# Load config from config.yml
def load_config():
    config_path = "config.yml"
    site_config = {}
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            site_config = yaml.safe_load(f)

    for topic, data in site_config["topics"].items():
        if data is None:
            print(f"No data for topic '{topic}'")
            continue

        DEFAULTS = {
            "calendar": "https://luma.com/code-maven",
            "facebook": "https://www.facebook.com/CodeMavens/",
            "linkedin": "https://www.linkedin.com/company/code-maven-world/",
            "telegram": "https://t.me/Code_Mavens",
        }

        for field, value in DEFAULTS.items():
            if field in data:
                if "label" not in data[field]:
                    data[field]["label"] = f"{topic} Maven"
            else:
                print(f"No {field} for topic '{topic}'")
                data[field] = {
                    "label": "Code Maven",
                    "url": value,
                }
                if field == "calendar":
                    data[field]["id"] = "cal-HdYbTQFG0qbnA4h"

    return site_config


def verify_config_calendars(site_config):
    errors = []
    url_to_id = {}
    id_to_url = {}

    for topic, data in site_config.get("topics", {}).items():
        if not data:
            continue
        calendar = data["calendar"]
        cal_url = calendar.get("url")
        cal_id = calendar.get("id")
        if not cal_url:
            errors.append(
                f"Topic '{topic}' calendar entry in config.yml is missing 'url'"
            )
            continue
        if not cal_id:
            errors.append(
                f"Topic '{topic}' calendar entry in config.yml is missing 'id'"
            )
            continue

        prev_id, prev_topic = url_to_id.setdefault(cal_url, (cal_id, topic))
        if prev_id != cal_id:
            errors.append(
                f"Calendar URL '{cal_url}' has conflicting IDs: '{prev_id}' (in '{prev_topic}') and '{cal_id}' (in '{topic}')"
            )

        prev_url, prev_topic = id_to_url.setdefault(cal_id, (cal_url, topic))
        if prev_url != cal_url:
            errors.append(
                f"Calendar ID '{cal_id}' has conflicting URLs: '{prev_url}' (in '{prev_topic}') and '{cal_url}' (in '{topic}')"
            )

    if errors:
        raise ValueError(
            "Config calendar verification failed:\n"
            + "\n".join(f"  - {err}" for err in errors)
        )


def verify_chronological_order_of_event_dates(events):
    current_date = date.today()
    prev_date = None
    for idx, event in enumerate(events):
        if not event:
            continue
        date_val = event.get("date")
        if not date_val:
            raise ValueError(f"Event at index {idx} is missing a date field")
        try:
            event_date, event_dt = parse_event_date(date_val)
        except ValueError as e:
            raise ValueError(
                f"Event at index {idx} has an invalid date format: '{date_val}'"
            ) from e

        if event_date >= current_date and event_dt is None:
            raise ValueError(
                f"Future event at index {idx} with date '{date_val}' must use the 'YYYY.MM.DDTHH:MM:SS+HH:MM' format"
            )

        if prev_date is not None and event_date < prev_date:
            raise ValueError(
                f"Events are not in chronological order: event at index {idx} with date {date_val} comes after a later date {prev_date.strftime('%Y.%m.%d')}"
            )
        prev_date = event_date


def verify_topics_and_their_casings(site_config, events):
    topics = list(site_config["topics"].keys())
    for idx, event in enumerate(events):
        if not event:
            continue
        topics_list = get_event_topics(event)
        for topic in topics_list:
            if topic not in topics:
                # Check case-insensitively
                matching = [t for t in topics if t.lower() == topic.lower()]
                if matching:
                    raise ValueError(
                        f"Topic '{topic}' at index {idx} has incorrect casing. Expected '{matching[0]}'"
                    )
                else:
                    raise ValueError(
                        f"Topic '{topic}' at index {idx} is not in the list of valid topics: {sorted(topics)}"
                    )


def fetch_luma_events(calendar_id, current_date):
    luma_ics_url = f"https://api.luma.com/ics/get?entity=calendar&id={calendar_id}"
    response = requests.get(luma_ics_url, timeout=30)
    response.raise_for_status()

    cal = icalendar.Calendar.from_ical(response.text)
    luma_events = {}
    for component in cal.walk("VEVENT"):
        dtstart_prop = component.get("DTSTART")
        if not dtstart_prop:
            continue
        dtstart = dtstart_prop.dt
        event_date = dtstart.date() if isinstance(dtstart, datetime) else dtstart
        if event_date < current_date or event_date.year >= 2030:
            continue

        summary = str(component.get("SUMMARY", ""))
        description = str(component.get("DESCRIPTION", ""))
        match = re.search(r"https://luma\.com/[a-zA-Z0-9_-]+", description)
        if not match:
            continue
        url = match.group(0)
        luma_events[url] = {
            "dt": dtstart if isinstance(dtstart, datetime) else None,
            "date": event_date,
            "title": summary,
        }
    return luma_events


def get_future_local_events(events, current_date, start_hour=None, end_hour=None):
    local_events = {}
    for event in events:
        if not event:
            continue
        date_val = event.get("date", "")
        event_date, event_dt = parse_event_date(date_val)
        if event_date < current_date:
            continue
        if start_hour is not None and (event_dt is None or event_dt.hour < start_hour):
            continue
        if end_hour is not None and (event_dt is None or event_dt.hour > end_hour):
            continue
        register = event.get("register")
        title = event.get("title", "")
        local_events[register] = {
            "dt": event_dt,
            "date": event_date,
            "date_str": str(date_val),
            "title": title,
        }
    return local_events


def compare_luma_to_local_events(luma_events, local_events, calendar_label):
    errors = []
    for url, luma_ev in luma_events.items():
        luma_dt = luma_ev["dt"]
        luma_dt_str = luma_dt.isoformat() if luma_dt else luma_ev["date"].isoformat()
        summary = luma_ev["title"]

        if url not in local_events:
            errors.append(
                f"Event in Luma calendar ({calendar_label}) is missing from events.yaml: {url} ('{summary}' on {luma_dt_str})"
            )
        else:
            local_ev = local_events[url]
            if local_ev["dt"] != luma_dt:
                local_dt_str = (
                    local_ev["dt"].isoformat()
                    if local_ev["dt"]
                    else local_ev["date"].isoformat()
                )
                errors.append(
                    f"Date/time mismatch for {url} in {calendar_label}: events.yaml has '{local_ev['date_str']}' ({local_dt_str}), Luma calendar has '{luma_dt_str}'"
                )
            if local_ev["title"] != summary:
                errors.append(
                    f"Title mismatch for {url} in {calendar_label}: events.yaml has '{local_ev['title']}', Luma calendar has '{summary}'"
                )
    return errors


def verify_luma_calendar(
    events, calendar_name, calendar_id, start_hour=None, end_hour=None
):
    current_date = date.today()
    luma_events = fetch_luma_events(calendar_id, current_date)
    local_events = get_future_local_events(events, current_date, start_hour, end_hour)

    errors = []

    for url, local_ev in local_events.items():
        if url not in luma_events:
            errors.append(
                f"Event in events.yaml is missing from Luma calendar ({calendar_name}): {url} ('{local_ev['title']}' on {local_ev['date_str']})"
            )

    errors.extend(
        compare_luma_to_local_events(luma_events, local_events, calendar_name)
    )

    if errors:
        raise ValueError(
            f"Luma calendar ({calendar_name}) verification failed:\n"
            + "\n".join(f"  - {err}" for err in errors)
        )


def verify_topic_calendars(site_config, events):
    current_date = date.today()
    local_events = get_future_local_events(events, current_date)

    calendars = {}
    for topic, data in site_config.get("topics", {}).items():
        if not data or "calendar" not in data:
            continue
        cal = data["calendar"]
        cal_id = cal.get("id")
        cal_url = cal.get("url")
        if cal_id and cal_id not in calendars:
            calendars[cal_id] = cal_url

    errors = []
    for cal_id, cal_url in calendars.items():
        luma_events = fetch_luma_events(cal_id, current_date)
        errors.extend(
            compare_luma_to_local_events(
                luma_events, local_events, f"{cal_url}, {cal_id}"
            )
        )

    if errors:
        raise ValueError(
            "Topic calendars verification failed:\n"
            + "\n".join(f"  - {err}" for err in errors)
        )


def render_all_markdown_files_in_pages(md, site_config, layout_template):
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
                html_path = os.path.join("site", f"{name_without_ext}.html")
                render_and_write_page(
                    layout_template=layout_template,
                    site_config=site_config,
                    title=title,
                    url=f"/{name_without_ext}",
                    content=html_content,
                    out_path=html_path,
                )
                generated_pages.append(html_path)
    return generated_pages


def load_events():
    yaml_path = "events.yaml"
    if not os.path.exists(yaml_path):
        raise FileNotFoundError(f"YAML file not found at {yaml_path}")

    with open(yaml_path, "r", encoding="utf-8") as f:
        events = yaml.safe_load(f)

    if not events:
        events = []

    return events


def rebuild():
    events = load_events()
    site_config = load_config()

    verify_config_calendars(site_config)
    verify_chronological_order_of_event_dates(events)
    verify_topics_and_their_casings(site_config, events)
    verify_luma_calendar(events, "code-maven", "cal-HdYbTQFG0qbnA4h")
    verify_luma_calendar(
        events, "code-maven-east", "cal-RuSzE7lTx5303F9", start_hour=8, end_hour=12
    )
    verify_topic_calendars(site_config, events)

    # Setup Jinja2 environment
    loader = FileSystemLoader("templates")
    env = Environment(loader=loader)
    layout_template = env.get_template("layout.html")
    index_template = env.get_template("index.html")
    past_template = env.get_template("past.html")
    linkedin_template = env.get_template("linkedin.html")
    facebook_template = env.get_template("facebook.html")
    telegram_template = env.get_template("telegram.html")
    calendars_template = env.get_template("calendars.html")
    topics_template = env.get_template("topics.html")

    md = MarkdownIt("gfm-like")

    # Ensure site/ directory exists
    os.makedirs("site", exist_ok=True)

    # Render main index.html and past.html pages
    build_page(
        events=events,
        template=index_template,
        layout_template=layout_template,
        site_config=site_config,
        md=md,
        topic_filter=None,
        past_template=past_template,
    )

    # Render topic-specific pages
    for topic in site_config["topics"].keys():
        build_page(
            events=events,
            template=index_template,
            layout_template=layout_template,
            site_config=site_config,
            md=md,
            topic_filter=topic,
        )

    generated_pages = render_all_markdown_files_in_pages(
        md, site_config, layout_template
    )

    # Render site/linkedin.html
    generate_links_page(
        template=linkedin_template,
        layout_template=layout_template,
        site_config=site_config,
        field="linkedin",
        context_key="linkedin_links",
        title="Code-Maven LinkedIn Channels",
        url="/linkedin",
        out_path="site/linkedin.html",
    )

    # Render site/facebook.html
    generate_links_page(
        template=facebook_template,
        layout_template=layout_template,
        site_config=site_config,
        field="facebook",
        context_key="facebook_links",
        title="Code-Maven Facebook Groups",
        url="/facebook",
        out_path="site/facebook.html",
    )

    # Render site/telegram.html
    generate_links_page(
        template=telegram_template,
        layout_template=layout_template,
        site_config=site_config,
        field="telegram",
        context_key="telegram_links",
        title="Code-Maven Telegram Groups",
        url="/telegram",
        out_path="site/telegram.html",
    )

    # Render site/calendars.html
    generate_links_page(
        template=calendars_template,
        layout_template=layout_template,
        site_config=site_config,
        field="calendar",
        context_key="calendars",
        title="Code-Maven Calendars",
        url="/calendars",
        out_path="site/calendars.html",
    )

    # Render site/topics.html
    generate_topics_page(
        template=topics_template,
        layout_template=layout_template,
        site_config=site_config,
        events=events,
    )

    generate_redirects(site_config)

    compile_style_scss()

    copy_static_files()

    # Create .nojekyll in site/ directory to bypass Jekyll
    with open("site/.nojekyll", "w", encoding="utf-8") as f:
        f.write("")

    # Generate site/future.md
    generate_future_events(events)

    print(
        f"Successfully rebuilt site/index.html, site/past.html, {', '.join(generated_pages)}, site/linkedin.html, site/facebook.html, site/telegram.html, site/calendars.html, site/topics.html, site/future.md, and site/assets/css/style.css"
    )


if __name__ == "__main__":
    rebuild()
