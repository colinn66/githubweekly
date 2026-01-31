#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate RSS feed from markdown files in a GitHub repository.

This script converts markdown files in a specified directory to HTML,
replaces relative image paths with absolute GitHub RAW URLs, and generates
a well-formatted RSS 2.0 XML file. It follows Google Python Style Guide.
"""

import os
import re
import subprocess
import sys
from datetime import datetime
from xml.etree import ElementTree as ET
from xml.dom import minidom

# Try to import markdown, install if missing
try:
    import markdown
except ImportError:
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "markdown"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    import markdown

# -----------------------------------------------------------------------------
# Configuration Constants (All caps with underscores, grouped and documented)
# -----------------------------------------------------------------------------
# RSS Feed Core Configuration
RSS_TITLE = "IT咖啡馆的github每周热点项目"
RSS_LINK = "https://github.com/qjm100/githubweekly"  # Replace with your repo URL
RSS_DESCRIPTION = "github 每周热点项目"
RSS_LANGUAGE = "zh-CN"

# File Path Configuration
MD_DIR = "post/"  # Directory containing markdown files
RSS_OUTPUT_FILE = "rss.xml"  # Output RSS file name
RSS_ICON_PATH = "/asset/it-coffee-circle.png"  # Icon path within repo

# Markdown Conversion Configuration
MD_EXTENSIONS = [
    "extra",  # Enable extra markdown features
    "codehilite",  # Syntax highlighting for code blocks
    "sane_lists",  # Improve list handling
    "nl2br",  # Convert newlines to <br> tags
]
MD_EXTENSION_CONFIGS = {"codehilite": {"linenums": False, "css_class": "code-block"}}

# HTML Styling (for better RSS reader rendering)
HTML_STYLE = """
    <style>
        .code-block { background: #f5f5f5; padding: 10px; border-radius: 4px; font-family: monospace; }
        table { border-collapse: collapse; margin: 10px 0; }
        th, td { border: 1px solid #ddd; padding: 6px 12px; }
        th { background: #f0f0f0; }
        h1, h2, h3 { margin: 15px 0 5px; }
        p { line-height: 1.6; margin: 8px 0; }
        ul, ol { margin: 8px 0 8px 20px; }
        img { max-width: 100%; height: auto; border-radius: 4px; margin: 10px 0; }
    </style>
"""


# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------
def get_file_commit_time(file_path):
    """Gets the last commit time of a file in RFC 822 format (UTC).

    Uses git log to retrieve the commit time. Falls back to current UTC time
    if git command fails or time parsing error occurs.

    Args:
        file_path: Path to the file (str).

    Returns:
        Formatted time string (str) in "Day, DD Mon YYYY HH:MM:SS GMT" format.
    """
    try:
        result = subprocess.check_output(
            ["git", "log", "-1", "--format=%ci", "--", file_path],
            encoding="utf-8",
            stderr=subprocess.DEVNULL,
        ).strip()
        # Extract date part and convert to datetime object
        commit_date = datetime.strptime(result.split(" ")[0], "%Y-%m-%d")
        return commit_date.strftime("%a, %d %b %Y %H:%M:%S GMT")
    except (subprocess.CalledProcessError, ValueError):
        # Fallback to current UTC time
        return datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")


def replace_md_image_paths(md_content, md_file_path):
    """Replaces relative image paths in markdown with absolute GitHub RAW URLs.

    Matches markdown image syntax (![alt](path)) and converts relative paths
    to absolute URLs pointing to GitHub's raw content delivery.

    Args:
        md_content: Original markdown content (str).
        md_file_path: Path to the markdown file (str) to resolve relative paths.

    Returns:
        Modified markdown content with absolute image URLs (str).
    """
    # Regex pattern to match markdown image syntax: ![alt](path) or ![alt](path "title")
    image_pattern = re.compile(r'!\[(.*?)\]\((.*?)(?:\s+".*?")?\)')

    def _replace_image_match(match):
        """Inner function to process each regex match (private by Google style)."""
        alt_text = match.group(1)
        img_path = match.group(2).strip()

        # Skip already absolute URLs
        if img_path.startswith(("http://", "https://")):
            return f"![{alt_text}]({img_path})"

        # Calculate absolute path of the image
        md_dir = os.path.dirname(md_file_path)
        abs_img_path = os.path.abspath(os.path.join(md_dir, img_path))
        repo_root = os.path.abspath("./")
        rel_img_path = os.path.relpath(abs_img_path, repo_root)

        # Build GitHub RAW URL (encode spaces)
        img_raw_link = f"{RSS_LINK}/raw/main/{rel_img_path.replace(' ', '%20')}"
        return f"![{alt_text}]({img_raw_link})"

    return image_pattern.sub(_replace_image_match, md_content)


def md_to_html(file_path):
    """Converts a markdown file to HTML with proper image paths and styling.

    Args:
        file_path: Path to the markdown file (str).

    Returns:
        Complete HTML content (str) with embedded styles and fixed image URLs.
    """
    with open(file_path, "r", encoding="utf-8") as file_handle:
        md_content = file_handle.read().strip()

    # Replace relative image paths with absolute GitHub URLs
    md_content = replace_md_image_paths(md_content, file_path)

    # Convert markdown to HTML
    html_content = markdown.markdown(
        md_content, extensions=MD_EXTENSIONS, extension_configs=MD_EXTENSION_CONFIGS
    )

    # Wrap with container and styles for better rendering
    full_html = f"<div style='max-width: 800px; margin: 0 auto;'>{HTML_STYLE}{html_content}</div>"

    return full_html


def _prettify_xml(element):
    """Prettifies XML output with proper indentation (private helper).

    Args:
        element: Root XML element (xml.etree.ElementTree.Element).

    Returns:
        Formatted XML string (str) with UTF-8 encoding and proper indentation.
    """
    rough_xml = ET.tostring(element, "utf-8")
    parsed_xml = minidom.parseString(rough_xml)
    pretty_xml = parsed_xml.toprettyxml(indent="  ")

    # Remove empty lines and redundant XML declaration
    clean_lines = [
        line
        for line in pretty_xml.split("\n")
        if line.strip() and not line.startswith("<?xml")
    ]

    # Add proper XML declaration at the top
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + "\n".join(clean_lines)


def generate_rss():
    """Main function to generate the RSS feed XML file.

    Creates RSS 2.0 structure, populates with markdown content,
    and writes the final XML to disk.
    """
    # Create RSS root and channel elements
    rss_root = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss_root, "channel")

    # Add core channel metadata
    ET.SubElement(channel, "title").text = RSS_TITLE
    ET.SubElement(channel, "link").text = RSS_LINK
    ET.SubElement(channel, "description").text = RSS_DESCRIPTION
    ET.SubElement(channel, "language").text = RSS_LANGUAGE
    ET.SubElement(channel, "pubDate").text = datetime.utcnow().strftime(
        "%a, %d %b %Y %H:%M:%S GMT"
    )

    # Add RSS icon if file exists
    if os.path.exists(RSS_ICON_PATH.lstrip("/")):  # Fix path check (remove leading /)
        icon_link = (
            f"{RSS_LINK}/raw/main/{RSS_ICON_PATH.lstrip('/').replace(' ', '%20')}"
        )
        image = ET.SubElement(channel, "image")
        ET.SubElement(image, "url").text = icon_link
        ET.SubElement(image, "title").text = RSS_TITLE
        ET.SubElement(image, "link").text = RSS_LINK
        ET.SubElement(image, "width").text = "144"
        ET.SubElement(image, "height").text = "144"

    # Process all markdown files in the target directory
    for root_dir, _, files in os.walk(MD_DIR):
        for file_name in files:
            if file_name.endswith(".md") and not file_name.startswith("."):
                file_path = os.path.join(root_dir, file_name)

                # Convert markdown to HTML
                html_content = md_to_html(file_path)

                # Get metadata for RSS item
                commit_time = get_file_commit_time(file_path)
                item_title = os.path.splitext(file_name)[0]
                item_link = f"{RSS_LINK}/blob/main/{file_path.replace(' ', '%20')}"

                # Create RSS item
                item = ET.SubElement(channel, "item")
                ET.SubElement(item, "title").text = item_title
                ET.SubElement(item, "link").text = item_link

                # Add HTML content as description
                desc_elem = ET.SubElement(item, "description")
                desc_elem.text = html_content

                ET.SubElement(item, "pubDate").text = commit_time
                ET.SubElement(item, "guid").text = item_link  # Unique identifier

    # Generate and write prettified XML
    final_xml = _prettify_xml(rss_root)
    with open(RSS_OUTPUT_FILE, "w", encoding="utf-8") as file_handle:
        file_handle.write(final_xml)


# -----------------------------------------------------------------------------
# Main Execution
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    generate_rss()
