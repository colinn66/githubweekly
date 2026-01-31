import os
import subprocess
import sys
from datetime import datetime
from xml.etree import ElementTree as ET
from xml.dom import minidom

# 安装 markdown 库（首次运行自动安装）
try:
    import markdown
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "markdown"])
    import markdown

# RSS 基础配置（替换为你的仓库信息）
RSS_TITLE = "我的 MD 文件 RSS 订阅"
RSS_LINK = "https://github.com/qjm100/githubweekly"  # 示例：https://github.com/xxx/xxx
RSS_DESCRIPTION = "基于 Commit 时间自动生成的 MD 文件 RSS 订阅（完整 HTML 内容）"
RSS_LANGUAGE = "zh-CN"
MD_DIR = "./"  # MD 文件根目录（可改为 posts/ 等）
# 可选：配置 MD 转 HTML 的扩展（支持代码块、表格、换行等）
MD_EXTENSIONS = [
    "extra",  # 支持表格、换行、脚注等
    "codehilite",  # 代码块高亮（需额外安装 pygments，可选）
    "sane_lists",  # 优化列表渲染
    "nl2br",  # 换行符转 <br>，适配 RSS 阅读
]


def get_file_commit_time(file_path):
    """通过 git log 获取文件最后一次提交的时间（UTC 时间）"""
    try:
        # 执行 git log 获取最后一次提交的时间（ISO 格式）
        result = subprocess.check_output(
            ["git", "log", "-1", "--format=%ci", "--", file_path],
            encoding="utf-8",
            stderr=subprocess.DEVNULL,
        ).strip()
        # 转换为 RSS 要求的 RFC 822 格式（UTC）
        commit_time = datetime.strptime(result.split(" ")[0], "%Y-%m-%d")
        return commit_time.strftime("%a, %d %b %Y %H:%M:%S GMT")
    except (subprocess.CalledProcessError, ValueError):
        # 无提交记录时用当前时间
        return datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")


def md_to_html(file_path):
    """读取 MD 文件并完整转换为 HTML"""
    with open(file_path, "r", encoding="utf-8") as f:
        md_content = f.read().strip()

    # MD 转 HTML（启用扩展，保证格式完整）
    html_content = markdown.markdown(
        md_content,
        extensions=MD_EXTENSIONS,
        extension_configs={
            "codehilite": {
                "linenums": False,  # 关闭代码行号（可选）
                "css_class": "code-block",  # 给代码块加类名，方便样式控制
            }
        },
    )

    # 补充基础样式（适配 RSS 阅读器，可选）
    style = """
    <style>
        .code-block { background: #f5f5f5; padding: 10px; border-radius: 4px; font-family: monospace; }
        table { border-collapse: collapse; margin: 10px 0; }
        th, td { border: 1px solid #ddd; padding: 6px 12px; }
        th { background: #f0f0f0; }
        h1, h2, h3 { margin: 15px 0 5px; }
        p { line-height: 1.6; margin: 8px 0; }
        ul, ol { margin: 8px 0 8px 20px; }
    </style>
    """
    # 拼接样式和内容，保证 HTML 完整
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

    # 遍历所有 MD 文件（排除隐藏文件）
    for root, dirs, files in os.walk(MD_DIR):
        for file in files:
            if file.endswith(".md") and not file.startswith("."):
                file_path = os.path.join(root, file)
                # MD 转完整 HTML 内容
                html_content = md_to_html(file_path)
                # 获取文件最后一次提交时间
                file_commit_time = get_file_commit_time(file_path)
                # 标题：去掉 .md 后缀的文件名
                title = os.path.splitext(file)[0]
                # MD 文件的 GitHub 原始链接（替换空格为 URL 编码）
                file_github_link = (
                    f"{RSS_LINK}/blob/main/{file_path.replace(' ', '%20')}"
                )

                # 构建 RSS Item
                item = ET.SubElement(channel, "item")
                ET.SubElement(item, "title").text = title
                ET.SubElement(item, "link").text = file_github_link
                # 核心：description 填充完整 HTML 内容
                desc_elem = ET.SubElement(item, "description")
                desc_elem.text = html_content  # RSS 的 description 支持 HTML 格式
                ET.SubElement(item, "pubDate").text = file_commit_time
                # 唯一标识（GUID）：用文件的 GitHub 链接
                ET.SubElement(item, "guid").text = file_github_link

    # 格式化 XML（美化缩进，处理 HTML 特殊字符）
    rough_xml = ET.tostring(rss, "utf-8")
    parsed_xml = minidom.parseString(rough_xml)
    pretty_xml = parsed_xml.toprettyxml(indent="  ")
    # 去掉 minidom 自动生成的空行和多余声明
    pretty_xml = "\n".join(
        [
            line
            for line in pretty_xml.split("\n")
            if line.strip() and not line.startswith("<?xml")
        ]
    )
    # 补全 XML 声明（必须在第一行）
    final_xml = '<?xml version="1.0" encoding="UTF-8"?>\n' + pretty_xml

    # 写入 RSS 文件
    with open("rss.xml", "w", encoding="utf-8") as f:
        f.write(final_xml)


if __name__ == "__main__":
    generate_rss()
