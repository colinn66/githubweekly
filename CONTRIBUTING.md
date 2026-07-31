## 项目结构

```
├── _weekly/         # Jekyll 集合源文件（保留原始文件名：96.md, 97.md, ...）
├── _config.yml      # Jekyll 站点配置
├── _tabs/           # Chirpy 主题导航页（目前仅保留 about）
├── _data/           # 站点数据文件（联系方式、分享按钮等）
├── asset/           # 静态资源（图片、Logo 等）
├── post/            # 原始 Markdown 源文件（供 GitHub 浏览）
├── Gemfile          # Ruby 依赖声明
└── .github/workflows/
    └── pages-deploy.yml  # GitHub Actions 自动部署工作流
```

## 本地开发

```bash
# 安装依赖
bundle install

# 启动本地服务器
bundle exec jekyll serve

# 访问 http://127.0.0.1:4000/githubweekly/
```

## 新增文章

在 `_weekly/` 目录下创建新文件，文件名即期号，如 `104.md`：

```yaml
---
title: "GitHub一周热点第NNN期"
date: "YYYY-MM-DD"
description: "本期摘要"
---

正文内容...
```
