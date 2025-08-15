# 操作Openlist自动化Jellyfin剧集结构构建

> 一个基于 Textual 的命令行界面（TUI）小工具，帮你在 “OpenList” 风格的网盘上**选目录 → 批量重命名 → 自动建剧集目录结构 → 批量复制**，并支持按中文标题自动生成**拼音前缀**。主要适用于Jellyfin

---

## 功能概览

- **目录浏览**：Textual 驱动的 TUI 文件浏览器，方向键浏览、回车选择路径。  
- **智能前缀**：从所选源目录名中，智能选择字符用于重命名前缀。  
- **批量重命名**：末尾取集数数字，重命名为 `"{prefix} S01E01"`格式。  
- **自动建结构**：目标侧自动创建 `剧名/Season XX` 的目录结构。  
- **批量复制**：将源目录文件一次性复制到目标目录。

---

## 环境要求

- Python 3.12, 推荐使用uv

```bash
uv sync
```

---

## 配置说明（`conf.json`）

示例字段（请根据实际服务地址/目录调整）：

```json
{
  "dest": "http://127.0.0.1:5244/openlist",
  "username": "",
  "password": "",
  "token": "",
  "base_dir": "/夸克云盘/来自：分享",
  "dst_dir": "/Jellyfin/Opera"
}
```

- `dest`：后端服务前缀 URL  
- `username`/`password`：登录用账号密码（可为空，首次运行会提示输入）  
- `token`：登录成功后写入，后续复用
- `base_dir`：默认源目录
- `dst_dir`：默认目标目录

---

## 运行与使用

### 启动
```bash
uv run main.py
```

## Release（PyInstaller）

1. 基本命令（请勿打包成单文件版）：
   ```bash
   pyinstaller -D main.py --add-data "style.tcss;."
   ```
2. 运行时，配置依然在 exe 同目录
---

## 常见问题（FAQ）

- **Q：不是视频文件或没有集数数字的文件会被改名吗？**  
  A：不会，保留原始文件名。

- **Q：如何浏览选择目录？**  
  A：↑/↓ 选择条目，→ 进入文件夹，← 返回上级，回车选中当前路径。

---

## 第三方库

- **Textual** 提供现代化 TUI 框架。  
- **pypinyin** 用于中文转拼音。  
- **colorama** 日志色彩。

---

# Automating Jellyfin TV Show Structure with Openlist

> A Textual-based terminal user interface (TUI) tool that helps you navigate directories in an “OpenList”-style cloud storage, **select directories → batch rename → automatically create TV show folder structure → batch copy**, and supports automatically generating **Pinyin prefixes** from Chinese titles. Primarily designed for Jellyfin.

---

## Features

- **Directory Browser**: A Textual-powered TUI file browser with arrow keys for navigation and Enter to select a path.  
- **Smart Prefix**: Automatically extracts characters from the selected source directory name to use as a rename prefix.  
- **Batch Rename**: Extracts episode numbers from filenames and renames them to the format `"{prefix} S01E01"`.  
- **Automatic Structure Creation**: Automatically creates a `ShowName/Season XX` folder structure in the target location.  
- **Batch Copy**: Copies all files from the source directory to the target directory in one go.

---

## Requirements

- Python 3.12 (recommended: use `uv`)

```bash
uv sync
```

---

## Configuration (`conf.json`)

Example fields (adjust according to your service address and directory setup):

```json
{
  "dest": "http://127.0.0.1:5244/openlist",
  "username": "",
  "password": "",
  "token": "",
  "base_dir": "/QuarkCloud/FromShare",
  "dst_dir": "/Jellyfin/Opera"
}
```

- `dest`: Backend service base URL  
- `username` / `password`: Login credentials (optional; prompted on first run if empty)  
- `token`: Saved after successful login for reuse  
- `base_dir`: Default source directory  
- `dst_dir`: Default target directory  

---

## Running

### Start
```bash
uv run main.py
```

---

## Release (PyInstaller)

1. Basic command (do **not** use single-file mode):
   ```bash
   pyinstaller -D main.py --add-data "style.tcss;."
   ```
2. At runtime, the configuration file will still be stored in the same directory as the `.exe`.

---

## FAQ

- **Q: Will non-video files or files without episode numbers be renamed?**  
  A: No, they will be kept with their original names.

- **Q: How do I browse and select directories?**  
  A: Use ↑/↓ to move, → to enter a folder, ← to go back, and Enter to select the current path.

---

## Third-Party Libraries

- **Textual** – Provides the modern TUI framework.  
- **pypinyin** – Converts Chinese to Pinyin.  
- **colorama** – Adds color to log output.

