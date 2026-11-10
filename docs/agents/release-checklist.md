# PaperFlick 发版清单

目标产物：**Windows 安装包** + **GitHub Release** + **PyPI**。  
Skills：`generating-python-installer`（封装）+ `ship --no-auto`（发版）。  
本机策略：**首次禁止 agent 自动 push / publish**；每步等人确认。

> ADR `0004` 仍写「首版 mamba + 源码；冻二进制延后」。走本清单前，先开小 PR 修订 ADR（接受 Nuitka dist + Inno），再封装。

---

## 0. 一次性前置

- [ ] 本机已装：**MSVC 或 MinGW**、**Nuitka**、**Inno Setup**、`gh` 已登录、`twine`/`build` 可用
- [ ] PyPI 凭据就绪：优先 1Password `op://…/token` + `TWINE_USERNAME=__token__`（或 keyring）；agent 仅在明确授权且本机可 `op read` 时代发
- [ ] Cursor 已装 skill：`ship`、`generating-python-installer`
- [ ] 工作树干净；在默认分支（或已合并待发版 tip）
- [ ] 定版本号 `X.Y.Z`（与 `pyproject.toml` 即将写入的值一致）

PaperFlick 冻结后仍依赖本机外部程序（不进安装包）：

| 能力 | 依赖 |
|---|---|
| PDF 静默打印 | SumatraPDF（路径检测） |
| DOCX | Word COM → OnlyOffice |
| 打印机队列 | Windows Spooler + pywin32 |

安装包说明 / README 必须写清这些运行时依赖。

---

## 1. 质量门禁（封装前）

在 `paperflick` mamba 环境：

```powershell
mamba run -n paperflick ruff check src tests
mamba run -n paperflick pytest -q
```

- [ ] ruff / pytest 全绿
- [ ] 按需跑 `.cursor/skills/verify-paperflick/`（至少：boot、settings、Dry Run）
- [ ] 确认无未提交改动、无本地仅有的 secret

---

## 2. 封装（`/generating-python-installer`）

顺序固定：**先做出安装包，再发版**（安装包版本号 = 即将发布的 `X.Y.Z`）。

### 2.1 Nuitka 编译档位（按 semver bump 选，省时间）

本机 `build_optimized.bat` 接受档位参数（也可用环境变量 `PAPERFLICK_BUILD_PROFILE`）。  
**不要**为了「省事」每次都开 LTO 全量：上次 LTO 链接可占整次编译大半时间。

| 档位 | 何时用 | LTO | 是否清空 `dist\` | 缓存（Nuitka/clcache） | 命令 |
|---|---|---|---|---|---|
| `patch` | 补丁：文案/UI/资源微调、未动原生依赖 | `no` | 否（增量） | 保留 | `build_optimized.bat patch` |
| `minor` | 小功能：预览/设置等纯 Python 行为 | `no` | 是（全量 folder） | 保留 | `build_optimized.bat minor` |
| `major` | 大版本、或 MSVC/依赖/插件集合大变、对外正式质量包 | `yes` | 是 | 保留 | `build_optimized.bat major` |

强制走 `major`（即使版本号是 patch）：换过 Python/Nuitka 大版本、增删 `pywin32`/`pymupdf` 等原生轮子、或用户明确要求「发版质量包」。

默认经验：`patch`/`minor` 关 LTO 可把链接从数十分钟降到可接受范围；`major` 才付 LTO 成本。

Agent：封装前先根据即将发布的 bump 选定档位并打印选择；用户可一句话覆盖（例如「这次强制 major」）。

### 2.2 封装步骤

1. 调用 skill；**逐项确认**参数（skill 禁止默认值）：
   - App Name：`PaperFlick` / `纸闪`
   - Version：`X.Y.Z` + **编译档位** `patch|minor|major`
   - Publisher：（你的发布者名）
   - Exe Name：如 `PaperFlick.exe`
   - Source / Output / Icon / URL
2. Nuitka：**folder/dist 模式**（不要 onefile）；`--windows-console-mode=disable`；LTO/清 dist 按上表
3. 特别核对打包进 dist 的模块：`customtkinter`、`tkinterdnd2`、`pywin32`、`pymupdf`、`pypdf`、`PIL`、`docx`
4. dist 瘦身 / DLL 分析后，在**干净 Windows 机或 VM** 安装并冒烟：
   - [ ] 启动空窗
   - [ ] 设置读写
   - [ ] Dry Run 一批 PDF/图片（DOCX 视本机 Word/OnlyOffice）
5. 产出命名建议：`PaperFlick-Setup-X.Y.Z.exe`（路径记下来，供 Release 附件）

**本步不 push、不打 tag、不发 PyPI。**

---

## 3. 发版准备 + 交互发版（`/ship X.Y.Z --no-auto`）

必须带 **`--no-auto`**。对人确认点：

| 步骤 | 确认内容 | 首次默认 |
|---|---|---|
| 版本 | `X.Y.Z` 与安装包一致 | 你拍板 |
| 文件变更 | changelog / README / docs / `pyproject.toml` | 审 diff |
| Build | `python -m build`（wheel + sdist） | 允许本地 build |
| Push + tag | `git push` + `vX.Y.Z` | **拒绝；你自己推** |
| GitHub Release | `gh release create` | **拒绝；你自己建，并挂安装包** |
| PyPI | `twine upload` | **拒绝；你自己发** |

Agent 在 push/publish 被拒后应停在 `PARTIAL`（本地 commit/tag 或仅工作区变更），并给出你可复制的命令。

若 skill 已在本地创建 annotated tag 但未 push，你可自检：

```powershell
git status
git tag -l "vX.Y.Z"
git log -1 --oneline
```

---

## 4. 人工收尾（衔接缝：两个 skill 都不管）

### 4.1 推送

```powershell
git push origin HEAD
git push origin vX.Y.Z
git ls-remote --tags origin "refs/tags/vX.Y.Z"
```

### 4.2 GitHub Release + 安装包附件

```powershell
gh release create vX.Y.Z --title "vX.Y.Z" --notes-file <changelog-notes.md> --latest `
  "path\to\PaperFlick-Setup-X.Y.Z.exe"
```

若 Release 已由先前步骤创建、只缺附件：

```powershell
gh release upload vX.Y.Z "path\to\PaperFlick-Setup-X.Y.Z.exe" --clobber
```

### 4.3 PyPI

```powershell
mamba run -n paperflick python -m build
mamba run -n paperflick twine check dist\*
mamba run -n paperflick twine upload dist\*
```

- [ ] https://pypi.org/project/paperflick/`X.Y.Z` 可见
- [ ] Release 页可见安装包下载
- [ ] README / Release notes 写明 Sumatra / Word·OnlyOffice 依赖

---

## 5. 明确不在本清单内

- 代码签名（Authenticode）→ 另配证书与签程
- 自动更新通道 → 另设计
- macOS / Linux 安装包 → 非目标
- Docker → 非目标

---

## 推荐会话口令

1. 「按 `docs/agents/release-checklist.md` 修订 ADR 0004，再开封装 PR。」
2. 「`/generating-python-installer`，版本 `X.Y.Z`，做出 Setup。」
3. 「`/ship X.Y.Z --no-auto`；**不要** push、**不要** `gh release create`、**不要** twine。」
4. 你本地执行 §4。
