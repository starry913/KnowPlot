# KnowPlot 项目约定

绘制科研图时先读取本项目 `personal_library.py` 的 `list_references()`，按 `framework`、`mechanism`、`experiment` 三类查找用户收藏的图，并实际查看原图。参考图提供视觉方法，不提供当前论文的科学事实。用户只需上传图并选类别，不需要填写出处或审美评价。

使用 `$knowplot`：核对论文内容，选一张主参考图与有明确用途的分参考图，先写本次 `DESIGN.md`，再在 Figma 中按独立图层绘制。image2 只做局部无字小图。所有箭头接到具体源对象与目标对象；工具查询与结果返回分开。检查小图是否足够大、内容是否来自论文、文字是否在框内、公式和数值是否准确。

图书馆和生成运行记录放在 `personal_data/`，不进入 Git。Figma 本地同步插件在 `figma_incremental/`，工作场景为被 Git 忽略的 `scene.json`；修改稳定 ID 对应的局部图层，保留用户在 Figma 中对未改动图层的手工调整。最终核对 Figma 实际导出的预览；没有真实预览时要说明。
