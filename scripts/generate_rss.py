import os
import re
from datetime import datetime
from xml.etree import ElementTree as ET
from xml.dom import minidom

# RSS 基础配置
RSS_TITLE = "rss 订阅"
RSS_LINK = "https://github.com/qjm100/githubweekly"  # 替换为仓库地址
RSS_DESCRIPTION = "自动生成的 MD 文件 RSS 订阅"
RSS_LANGUAGE = "zh-CN"
MD_DIR = "./"  # MD 文件根目录，可改为 posts/ 等


def parse_md_metadata(md_content):
    """解析 MD 文件头部的元信息"""
    meta_pattern = re.compile(r"---\n(.*?)\n---", re.DOTALL)
    meta_match = meta_pattern.search(md_content)
    metadata = {}
    if meta_match:
        meta_lines = meta_match.group(1).split("\n")
        for line in meta_lines:
            if ":" in line:
                key, value = line.split(":", 1)
                metadata[key.strip()] = value.strip().strip('"').strip("'")
    # 提取正文（去掉元信息）
    content = meta_pattern.sub("", md_content).strip()
    return metadata, content


def generate_rss():
    # 创建 RSS 根节点
    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")

    # 填充频道信息
    ET.SubElement(channel, "title").text = RSS_TITLE
    ET.SubElement(channel, "link").text = RSS_LINK
    ET.SubElement(channel, "description").text = RSS_DESCRIPTION
    ET.SubElement(channel, "language").text = RSS_LANGUAGE
    ET.SubElement(channel, "pubDate").text = datetime.utcnow().strftime(
        "%a, %d %b %Y %H:%M:%S GMT"
    )

    # 遍历所有 MD 文件
    for root, dirs, files in os.walk(MD_DIR):
        for file in files:
            if file.endswith(".md") and not file.startswith("."):  # 排除隐藏文件
                file_path = os.path.join(root, file)
                with open(file_path, "r", encoding="utf-8") as f:
                    md_content = f.read()

                # 解析元信息和正文
                metadata, content = parse_md_metadata(md_content)
                title = metadata.get("title", file[:-3])  # 无标题则用文件名
                date = metadata.get("date", datetime.utcnow().strftime("%Y-%m-%d"))
                description = metadata.get(
                    "description", content[:200]
                )  # 摘要取前200字

                # 构建 item 节点
                item = ET.SubElement(channel, "item")
                ET.SubElement(item, "title").text = title
                ET.SubElement(
                    item, "link"
                ).text = f"{RSS_LINK}/blob/main/{file_path.replace(' ', '%20')}"  # MD 文件链接
                ET.SubElement(item, "description").text = description
                ET.SubElement(item, "pubDate").text = datetime.strptime(
                    date, "%Y-%m-%d"
                ).strftime("%a, %d %b %Y %H:%M:%S GMT")
                ET.SubElement(
                    item, "guid"
                ).text = f"{RSS_LINK}/blob/main/{file_path}"  # 唯一标识

    # 格式化 XML（美化缩进）
    rough_string = ET.tostring(rss, "utf-8")
    reparsed = minidom.parseString(rough_string)
    pretty_xml = reparsed.toprettyxml(indent="  ")

    # 写入 RSS 文件（仓库根目录）
    with open("rss.xml", "w", encoding="utf-8") as f:
        f.write(pretty_xml)


if __name__ == "__main__":
    generate_rss()
