<p align="center">
  <img src="icons/readme-banner.png" alt="PaperFlick banner" width="100%">
</p>

<p align="center">
  <img src="icons/readme-logo-light.png#gh-light-mode-only" alt="PaperFlick" height="96">
  <img src="icons/readme-logo-dark.png#gh-dark-mode-only" alt="PaperFlick" height="96">
</p>

# PaperFlick（纸闪）

个人向 Windows 批量打印工具：把 PDF / DOCX / 图片排成打印项列表，按间隔串行提交，降低 Print Spooler 卡死风险；失败项可保留并一键重打。

| | 名称 |
|---|---|
| 英文 / GitHub | **PaperFlick**（仓库 [`nancliu/PaperFlick`](https://github.com/nancliu/PaperFlick)） |
| 中文 | **纸闪** |

## 功能概览

- **打印项列表**：添加文件 / 文件夹，或拖入主内容区；单击行打开预览，行内移除；支持 PDF、DOCX/DOC、常见图片后缀
- **打印机**：可拖拽加宽的侧边栏；悬停看全名；系统默认项带「（默认）」；无已存选择时回落系统默认打印机
- **方向**：添加时按首页几何推断朝向；预览窗可对单项 / 同类型 / 全部应用横向、纵向或打印机默认
- **预览缩略图**：先出预览窗再绘缩略图；图片（Pillow）、PDF（pymupdf）、DOCX（Windows Shell 缩略图；失败则文字回退）
- **批次**：间隔串行；演练（Dry Run）不送真实打印机；Live 时 PDF→SumatraPDF，图片→Pillow/Windows，DOCX→Word 再 OnlyOffice
- **失败与重打**：失败原因可见（状态着色）；失败数 > 0 时显示重新打印失败项、清除已成功、移除全部失败
- **设置**：默认折叠的「设置」区（间隔秒数、等队列空、演练）；状态栏右侧版本可点开关于；写入 `%APPDATA%\PaperFlick\settings.json`（可用 `PAPERFLICK_APPDATA` 覆盖）

## 运行（开发）

需要 [mamba](https://mamba.readthedocs.io/)（或 micromamba）。在 **非 base** 环境中安装依赖：

```powershell
mamba env create -f environment.yml
mamba activate paperflick
pip install -e .
python -m paperflick
```

若环境已存在，用 `mamba env update -f environment.yml --prune` 同步依赖后，再 `pip install -e .`。

Live 打印额外依赖本机软件（按格式）：SumatraPDF、Microsoft Word，以及可选的 OnlyOffice（DOCX 回退）。

## 检查

```powershell
mamba activate paperflick
pip install -e ".[dev]"
ruff check src tests
pytest -q
pre-commit install
```

- GUI 测试：`pytest -q -m gui`（需本机可用的 Tcl/Tk；CI 默认跑 `-m "not gui"`）
- Windows 下用脚本或 `pytest` 跑检查，不要用多行 `python -c`
- GitHub Actions 按 `pyproject.toml` 的 `pip install -e ".[dev]"` 安装；测试收集所需依赖须写进 `pyproject`，不能只写在 `environment.yml`
- 运行时验证见 `.cursor/skills/verify-paperflick/`

## 文档

- [产品规划](docs/产品规划.md) — 定位、命名依据、交互、技术选型与验收标准
- [GLOSSARY.md](GLOSSARY.md) — 领域术语
- [CODING_STANDARDS.md](CODING_STANDARDS.md) — 评审用判断性约定
- [docs/adr/](docs/adr/) — 技术决策
- [AGENTS.md](AGENTS.md) — 本仓库对 agent 的工作约定

## 状态

个人向 v1 主路径已落地（列表单击预览、打印机侧栏、演练 / Live 多格式提交、失败重打、设置分层与关于）。后续以 GitHub Issues 为准。
