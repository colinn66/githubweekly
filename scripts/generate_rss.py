import os
import re
import subprocess
import sys
from datetime import datetime
from xml.etree import ElementTree as ET
from xml.dom import minidom

try:
    import markdown
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "markdown"])
    import markdown

# RSS 基础配置
RSS_TITLE = "我的 MD 文件 RSS 订阅"
RSS_LINK = "https://github.com/你的用户名/你的仓库名"  # 替换为你的仓库地址
RSS_DESCRIPTION = "基于 Commit 时间自动生成的 MD 文件 RSS 订阅（完整 HTML 内容）"
RSS_LANGUAGE = "zh-CN"
MD_DIR = "post/"
# RSS 图标配置
RSS_ICON_PATH = "/asset/it-coffee.circle.png"  # 仓库内图标路径
RSS_ICON_LINK = f"{RSS_LINK}/raw/main/{RSS_ICON_PATH.replace(' ', '%20')}"
RSS_ICON_TITLE = RSS_TITLE

MD_EXTENSIONS = ["extra", "codehilite", "sane_lists", "nl2br"]


def get_file_commit_time(file_path):
    """通过 git log 获取文件最后一次提交的时间（UTC 时间）"""
    try:
        result = subprocess.check_output(
            ["git", "log", "-1", "--format=%ci", "--", file_path],
            encoding="utf-8",
            stderr=subprocess.DEVNULL,
        ).strip()
        commit_time = datetime.strptime(result.split(" ")[0], "%Y-%m-%d")
        return commit_time.strftime("%a, %d %b %Y %H:%M:%S GMT")
    except (subprocess.CalledProcessError, ValueError):
        return datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")


def replace_md_image_paths(md_content, md_file_path):
    """
    替换 MD 中的图片相对路径为 GitHub RAW 绝对链接
    :param md_content: MD 文件内容
    :param md_file_path: 当前 MD 文件的路径（用于计算图片相对路径）
    :return: 替换后的 MD 内容
    """
    # 匹配 MD 图片语法：![alt](path) 或 ![alt](path "title")
    image_pattern = re.compile(r'!\[(.*?)\]\((.*?)(?:\s+".*?")?\)')

    def replace_match(match):
        alt_text = match.group(1)
        img_path = match.group(2).strip()

        # 跳过网络图片（已为绝对链接）
        if img_path.startswith(("http://", "https://")):
            return f"![{alt_text}]({img_path})"

        # 计算图片的绝对路径（相对于仓库根目录）
        md_dir = os.path.dirname(md_file_path)  # MD 文件所在目录
        abs_img_path = os.path.abspath(os.path.join(md_dir, img_path))  # 图片绝对路径
        repo_root = os.path.abspath("./")  # 仓库根目录
        # 转换为仓库内的相对路径（如 asset/xxx.png、posts/img/yyy.jpg）
        rel_img_path = os.path.relpath(abs_img_path, repo_root)
        # 拼接 GitHub RAW 链接（替换空格为 URL 编码）
        img_raw_link = f"{RSS_LINK}/raw/main/{rel_img_path.replace(' ', '%20')}"

        # 返回替换后的图片语法
        return f"![{alt_text}]({img_raw_link})"

    # 替换所有图片链接
    new_md_content = image_pattern.sub(replace_match, md_content)
    return new_md_content


def md_to_html(file_path):
    """读取 MD 文件并完整转换为 HTML（含图片路径替换）"""
    with open(file_path, "r", encoding="utf-8") as f:
        md_content = f.read().strip()

    # 核心步骤：替换 MD 中的图片相对路径为 GitHub RAW 绝对链接
    md_content = replace_md_image_paths(md_content, file_path)

    # MD 转 HTML（启用扩展，保证格式完整）
    html_content = markdown.markdown(
        md_content,
        extensions=MD_EXTENSIONS,
        extension_configs={
            "codehilite": {"linenums": False, "css_class": "code-block"}
        },
    )

    # 补充基础样式（适配 RSS 阅读器，优化图片显示）
    style = """
    <style>
        .code-block { background: #f5f5f5; padding: 10px; border-radius: 4px; font-family: monospace; }
        table { border-collapse: collapse; margin: 10px 0; }
        th, td { border: 1px solid #ddd; padding: 6px 12px; }
        th { background: #f0f0f0; }
        h1, h2, h3 { margin: 15px 0 5px; }
        p { line-height: 1.6; margin: 8px 0; }
        ul, ol { margin: 8px 0 8px 20px; }
        img { max-width: 100%; height: auto; border-radius: 4px; margin: 10px 0; } /* 图片自适应 */
    </style>
    """
    full_html = (
        f"<div style='max-width: 800px; margin: 0 auto;'>{style}{html_content}</div>"
    )

    return full_html


def generate_rss():
    # 创建 RSS 根节点
    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")

    # 填充频道基础信息
    ET.SubElement(channel, "title").text = RSS_TITLE
    ET.SubElement(channel, "link").text = RSS_LINK
    ET.SubElement(channel, "description").text = RSS_DESCRIPTION
    ET.SubElement(channel, "language").text = RSS_LANGUAGE
    ET.SubElement(channel, "pubDate").text = datetime.utcnow().strftime(
        "%a, %d %b %Y %H:%M:%S GMT"
    )

    # 添加 RSS 图标节点
    if os.path.exists(RSS_ICON_PATH):
        image = ET.SubElement(channel, "image")
        ET.SubElement(image, "url").text = RSS_ICON_LINK
        ET.SubElement(image, "title").text = RSS_ICON_TITLE
        ET.SubElement(image, "link").text = RSS_LINK
        ET.SubElement(image, "width").text = "144"
        ET.SubElement(image, "height").text = "144"

    # 遍历所有 MD 文件
    for root, dirs, files in os.walk(MD_DIR):
        for file in files:
            if file.endswith(".md") and not file.startswith("."):
                file_path = os.path.join(root, file)
                html_content = md_to_html(file_path)
                file_commit_time = get_file_commit_time(file_path)
                title = os.path.splitext(file)[0]
                file_github_link = (
                    f"{RSS_LINK}/blob/main/{file_path.replace(' ', '%20')}"
                )

                # 构建 RSS Item
                item = ET.SubElement(channel, "item")
                ET.SubElement(item, "title").text = title
                ET.SubElement(item, "link").text = file_github_link
                desc_elem = ET.SubElement(item, "description")
                desc_elem.text = html_content
                ET.SubElement(item, "pubDate").text = file_commit_time
                ET.SubElement(item, "guid").text = file_github_link

    # 格式化 XML
    rough_xml = ET.tostring(rss, "utf-8")
    parsed_xml = minidom.parseString(rough_xml)
    pretty_xml = parsed_xml.toprettyxml(indent="  ")
    pretty_xml = "\n".join(
        [
            line
            for line in pretty_xml.split("\n")
            if line.strip() and not line.startswith("<?xml")
        ]
    )
    final_xml = '<?xml version="1.0" encoding="UTF-8"?>\n' + pretty_xml

    # 写入 RSS 文件
    with open("rss.xml", "w", encoding="utf-8") as f:
        f.write(final_xml)


if __name__ == "__main__":
    generate_rss()
