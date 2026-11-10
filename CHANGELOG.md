# Changelog

## 1.1.0

### Added

- Preview Paper：预览窗灰底 + A4 白纸框叠显 Facing（横向对调；打印机为不强制）
- Windows 安装包装配：Nuitka standalone + Inno Setup、`slim_dist`、发版清单
- 品牌 lockup：标题栏 / About 图标与 README 资源

### Changed

- 设置 disclosure 默认靠右；预览控件置于缩略图之前
- ADR 0004 / 产品规划接受 Nuitka dist + Inno 作为 Windows 交付形态

### Notes

- 运行时仍依赖本机 SumatraPDF（PDF）、Word 或 OnlyOffice（DOCX）、Windows 打印机队列
