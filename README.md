# PaperFlick（纸闪）

个人向 Windows 批量打印工具（PDF / DOCX / 图片）：拖入即打、间隔串行，降低 Print Spooler 卡死风险。

| | 名称 |
|---|---|
| 英文 / GitHub | **PaperFlick**（仓库建议 `PaperFlick` / `paperflick`） |
| 中文 | **纸闪** |

## 运行（开发）

需要 [mamba](https://mamba.readthedocs.io/)（或 micromamba）。在 **非 base** 环境中安装依赖：

```powershell
mamba env create -f environment.yml
mamba activate paperflick
pip install -e .
python -m paperflick
```

若环境已存在，用 `mamba env update -f environment.yml --prune` 同步依赖后，再 `pip install -e .`。

设置默认保存在 `%APPDATA%\PaperFlick\settings.json`。测试时可设置环境变量 `PAPERFLICK_APPDATA` 指向临时目录，以覆盖该路径。

## 文档

- [产品规划](docs/产品规划.md) — 定位、命名依据、交互、技术选型与验收标准

## 状态

Issue #1：启动空窗 + 三项设置读写。打印列表、打印机与处理器尚未实现。
