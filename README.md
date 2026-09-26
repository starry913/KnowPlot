# KnowPlot

KnowPlot 是一个用个人论文图图库指导科研绘图的本地工作流。看到喜欢的图，存入图库并选类别；需要画图时，让 Codex 看参考图和论文内容，写 `DESIGN.md`，再在 Figma 中用可编辑图层绘制和微调。

它把**参考检索、构图设计、局部图片素材和真实画布检查**连在一起。KnowPlot 不训练模型，也不会仅凭图片里的 OCR 文字判断审美。默认流程使用当前 Codex 对话，无需另填 API Key。

## 组成

- `personal_studio.py`、`personal_library.py`：本地 Streamlit 图片图库。只需上传图片并选“方法框架图 / 关键机制示意图 / 实验数据图”。图库在本机 `personal_data/` 中，默认不会提交到 Git。
- `skills/knowplot/`：Codex skill。先核实论文事实，从图库选主参考和分参考，写每张图独立的 `DESIGN.md`，再指导 Figma 绘制与验收。
- `figma_incremental/`：KnowPlot Live 开发插件及本地同步服务。用稳定图层 ID 做局部更新，未变更的图层保留 Figma 中的手工调整。图片生成只负责与论文内容强相关的局部无字素材。

## 本地使用

需要 Python 3.10+、Codex、Figma Design 桌面版。先安装图库依赖：

```bash
python -m pip install -r requirements.txt
```

Windows 上双击 `启动KnowPlot图库.cmd`，或运行：

```bash
python -m streamlit run personal_studio.py --server.showEmailPrompt false
```

打开终端显示的本地地址，把喜欢的论文图加入三类图库之一。图像会保存为 WebP，并生成缩略图。图库和运行记录只在本机。

将 `skills/knowplot/` 复制到自己的 Codex skills 目录（通常是 `~/.codex/skills/knowplot/`），随后在 KnowPlot 项目里对 Codex 说：

> 用 $knowplot 根据我的论文画一张方法框架图。先看个人图库、写 DESIGN.md，再在 Figma 中分层绘制并检查。

方法图生成的流程是：**论文事实 → 视觉参考 → DESIGN.md → 可编辑 Figma 图层 → 实际导出检查**。统计数据图须基于真实数据绘制，不能让图像模型编造数值。

## Figma 同步

按 [KnowPlot Live 使用说明](figma_incremental/README.md) 导入开发插件并启动本地同步服务。仓库只附不含个人素材的 `scene.example.json`；第一次启动服务时会复制为本机 `scene.json`。之后 Codex 修改工作场景，插件会更新相关图层并回传预览。

## 隐私与来源

公开仓库不包含个人参考图、论文 PDF、图库数据库、Figma 运行场景、预览或 API Key。使用时请只导入自己有权使用的图片；参考图用于分析构图，不直接贴入新图。KnowPlot 的起点是基于 [PaperVizAgent / PaperBanana](https://github.com/google-research/papervizagent) 探索的个人工作流，详见 [NOTICE.md](NOTICE.md)。

## 开发检查

```bash
python -m unittest discover -s tests
python figma_incremental/test_bridge.py
node figma_incremental/test_code.cjs
```
