#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate RSS feed and HTML files from markdown files in a GitHub repository.

This script converts markdown files to HTML (saved to asset/html),
replaces relative image paths with absolute GitHub RAW URLs,
and generates a well-formatted RSS 2.0 XML file with links to HTML files.
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
RSS_LINK = "https://qjm100.github.io/githubweekly"  # Replace with your repo URL
RSS_DESCRIPTION = "github 每周热点项目"
RSS_LANGUAGE = "zh-CN"

# File Path Configuration
MD_DIR = "post/"  # Directory containing markdown files
HTML_OUTPUT_DIR = "asset/html"  # 新增：HTML输出目录
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

# HTML Styling (for better RSS reader rendering and standalone HTML files)
HTML_STYLE = """
    <style>
        body { max-width: 800px; margin: 20px auto; padding: 0 20px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
        .code-block { background: #f5f5f5; padding: 10px; border-radius: 4px; font-family: monospace; overflow-x: auto; }
        table { border-collapse: collapse; margin: 10px 0; }
        th, td { border: 1px solid #ddd; padding: 6px 12px; }
        th { background: #f0f0f0; }
        h1, h2, h3 { margin: 15px 0 5px; color: #2c3e50; }
        p { line-height: 1.6; margin: 8px 0; color: #34495e; }
        ul, ol { margin: 8px 0 8px 20px; color: #34495e; }
        img { max-width: 100%; height: auto; border-radius: 4px; margin: 10px 0; }
        .post-meta { color: #7f8c8d; font-size: 0.9em; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 1px solid #eee; }
    </style>
"""


# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------
def parse_md_metadata(md_content):
    """解析Markdown文件开头的YAML元数据块

    Args:
        md_content: 完整的markdown内容字符串

    Returns:
        tuple: (metadata_dict, clean_content)
            - metadata_dict: 包含title/date/description的字典，缺失则返回默认值
            - clean_content: 剥离元数据块后的纯正文内容
    """
    # 匹配开头的YAML元数据块（---开头和结尾）
    meta_pattern = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
    match = meta_pattern.match(md_content)

    metadata = {
        "title": "未命名文章",
        "date": datetime.utcnow().strftime("%Y-%m-%d"),
        "description": "",
    }
    clean_content = md_content

    if match:
        # 提取元数据块内容并清理正文
        meta_content = match.group(1)
        clean_content = md_content[match.end() :].strip()

        # 解析title
        title_match = re.search(r'title:\s*["\'](.*?)["\']', meta_content)
        if title_match:
            metadata["title"] = title_match.group(1)

        # 解析date
        date_match = re.search(r'date:\s*["\'](.*?)["\']', meta_content)
        if date_match:
            metadata["date"] = date_match.group(1)

        # 解析description
        desc_match = re.search(r'description:\s*["\'](.*?)["\']', meta_content)
        if desc_match:
            metadata["description"] = desc_match.group(1)

    return metadata, clean_content


def convert_date_to_rfc822(date_str):
    """将YYYY-MM-DD格式的日期转换为RSS要求的RFC 822格式（UTC）

    Args:
        date_str: YYYY-MM-DD格式的日期字符串

    Returns:
        str: RFC 822格式的日期字符串，格式如 "Tue, 20 May 2024 00:00:00 GMT"
    """
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        # 设置为UTC时间的0点，并格式化为RFC 822
        return date_obj.strftime("%a, %d %b %Y 00:00:00 GMT")
    except ValueError:
        # 解析失败时返回当前UTC时间
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
        img_raw_link = f"{RSS_LINK}{abs_img_path.replace(' ', '%20')}"  # 修复：使用相对仓库根目录的路径
        return f"![{alt_text}]({img_raw_link})"

    return image_pattern.sub(_replace_image_match, md_content)


def md_to_html(file_path):
    """Converts a markdown file to HTML with proper image paths and styling.

    Args:
        file_path: Path to the markdown file (str).

    Returns:
        tuple: (full_html, standalone_html, metadata, html_file_name)
            - full_html: 仅正文的HTML内容（用于RSS）
            - standalone_html: 完整的独立HTML文件内容（带head/body）
            - metadata: 解析出的元数据字典
            - html_file_name: 生成的HTML文件名
    """
    with open(file_path, "r", encoding="utf-8") as file_handle:
        md_content = file_handle.read().strip()

    # 解析元数据并剥离元数据块
    metadata, clean_md_content = parse_md_metadata(md_content)

    # 替换图片路径（仅处理正文）
    clean_md_content = replace_md_image_paths(clean_md_content, file_path)

    # 转换正文为HTML
    html_content = markdown.markdown(
        clean_md_content,
        extensions=MD_EXTENSIONS,
        extension_configs=MD_EXTENSION_CONFIGS,
    )

    # 用于RSS的HTML（仅正文+样式）
    rss_html = f"<div style='max-width: 800px; margin: 0 auto;'>{HTML_STYLE}{html_content}</div>"

    # 生成独立的完整HTML文件内容（带head/body）
    standalone_html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>{metadata['title']}</title>
    <meta name="description" content="{metadata['description'] or metadata['title']}">
    {HTML_STYLE}
</head>
<body>
    <h1>{metadata['title']}</h1>
    <div class="post-meta">发布时间：{metadata['date']}</div>
    {html_content}
</body>
</html>"""

    # 生成HTML文件名（替换md后缀为html，保留原文件名）
    file_name = os.path.basename(file_path)
    html_file_name = os.path.splitext(file_name)[0] + ".html"

    return rss_html, standalone_html, metadata, html_file_name


def save_html_file(standalone_html, html_file_name):
    """保存生成的HTML文件到指定目录

    Args:
        standalone_html: 完整的HTML内容
        html_file_name: 要保存的HTML文件名
    """
    # 确保输出目录存在
    os.makedirs(HTML_OUTPUT_DIR, exist_ok=True)
    
    # 拼接完整的HTML文件路径
    html_file_path = os.path.join(HTML_OUTPUT_DIR, html_file_name)
    
    # 写入HTML文件
    with open(html_file_path, "w", encoding="utf-8") as f:
        f.write(standalone_html)
    
    print(f"✅ 已生成HTML文件: {html_file_path}")


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


def generate_rss_and_html():
    """Main function to generate HTML files and RSS feed XML file.

    Creates RSS 2.0 structure, populates with markdown content,
    generates HTML files, and writes the final files to disk.
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

                # 转换markdown到HTML并获取元数据
                rss_html_content, standalone_html, metadata, html_file_name = md_to_html(file_path)
                
                # 保存HTML文件到asset/html目录
                save_html_file(standalone_html, html_file_name)

                # 使用元数据中的日期（转换为RFC 822格式）
                pub_date = convert_date_to_rfc822(metadata["date"])

                # 使用元数据中的标题
                item_title = metadata["title"]
                
                item_link = f"{RSS_LINK}/{HTML_OUTPUT_DIR}/{html_file_name.replace(' ', '%20')}"
                
                # Create RSS item
                item = ET.SubElement(channel, "item")
                ET.SubElement(item, "title").text = item_title
                ET.SubElement(item, "link").text = item_link

                # 优先使用元数据中的description，没有则用正文摘要
                item_description = (
                    metadata["description"]
                    if metadata["description"]
                    else rss_html_content[:200] + "..."
                )
                desc_elem = ET.SubElement(item, "description")
                desc_elem.text = item_description if metadata["description"] else rss_html_content
                ET.SubElement(item, "pubDate").text = pub_date
                ET.SubElement(item, "guid").text = item_link  # Unique identifier (使用HTML链接)

    # Generate and write prettified XML
    final_xml = _prettify_xml(rss_root)
    with open(RSS_OUTPUT_FILE, "w", encoding="utf-8") as file_handle:
        file_handle.write(final_xml)
    
    print(f"✅ 已生成RSS文件: {RSS_OUTPUT_FILE}")


# -----------------------------------------------------------------------------
# Main Execution
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    generate_rss_and_html()
