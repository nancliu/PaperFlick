# PaperFlick（纸闪）

个人向 Windows 批量打印：把多个文件排成列表，间隔串行交给打印机，并保留失败项以便重打。

## Language

**Print Item（打印项）**：
列表中的一行：一个待打文件，带类型、方向覆盖与状态（等待 / 打印中 / 成功 / 失败等）。
_Avoid_: Job, Document, File（单独指路径时除外）

**Print Job（打印作业）**：
一次提交给 Windows Print Spooler（或等价引擎）的出纸请求；一个打印项成功时通常对应至少一个作业。
_Avoid_: Print Item, Task

**Batch（批次）**：
用户一次「开始」所覆盖的、按序处理的一组打印项；失败不中断整批。
_Avoid_: Queue（易与 Spooler 队列混淆）, Run

**Dry Run（干跑）**：
不向真实打印机送作业、但走同一套调度与状态机的运行方式，用于自测与 agent 验证。UI 文案可用「演练（不送打印机）」；设置与代码标识仍用 Dry Run / `dry_run`。
_Avoid_: Mock print（易被理解成只 mock 函数）, Test mode（过宽）；勿把 UI「演练」写成第二套领域名

**Orientation（方向）**：
某打印项出纸时的页面朝向策略。
_Avoid_: Rotate, Page setup

**Auto / Landscape / Portrait / PrinterDefault**：
Orientation 的四态：自动按首页几何推断；强制横向；强制纵向；不改方向、交给打印机当前默认。UI 文案可用「自动 / 横向 / 纵向 / 打印机」。
_Avoid_: 混用中英文当代码标识；用 `horizontal`/`vertical` 代替 Landscape/Portrait

**Facing（朝向结果）**：
由 Orientation 与页面几何经 `resolve_facing` 得到的 Landscape / Portrait；PrinterDefault 解析为不强制（无 Facing）。不作为 Orientation 持久化。
_Avoid_: 把 Facing 存成 Orientation；把「打印机」预览画成假的横向/纵向

**Preview Paper（预览纸面）**：
预览窗里用灰底 + 白纸框表达 Facing 的纸张叠层（A4 比例；横向时对调）。不是 Print Job，也不是系统打印对话框。
_Avoid_: 把 Preview Paper 当成提交端口或真实打印机纸张尺寸
