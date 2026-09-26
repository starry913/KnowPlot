# KnowPlot Live：Figma 本地图层同步

这是 KnowPlot 的 Figma Design 开发插件。Codex 更新 `scene.json` 后，插件凭每个元素的稳定 `id` 局部同步；没有改动源属性的图层会保留在 Figma 中手工调整过的位置和尺寸。文字、普通形状可直接编辑，箭头和插画为独立图层。删除图层需要把 ID 放进场景的 `delete` 列表。

## 准备

1. 在 Figma Design 桌面版中打开**自己的可编辑文件**。
2. 在画布空白处选择 **Plugins → Development → Import plugin from manifest**，导入本目录的 `manifest.json`。
3. 运行 `python figma_incremental/bridge.py`，或在 Windows 双击 `启动本地图层同步.cmd`。服务只监听 `127.0.0.1:8765`，无需 API Key。首次启动会从 `scene.example.json` 建立本机 `scene.json`。
4. 在 Figma 运行 **KnowPlot Live**，保持插件窗口打开。它会定期检查本机 `scene.json` 的变化并导出 `figma-preview.png`。

`scene.example.json` 是没有私人论文内容的演示场景。自己的绘图场景、预览与 `assets/` 素材均被 Git 忽略。若 Figma 无法访问本地服务，可在插件窗口手工选择 `scene.json` 或粘贴其内容。

## 迭代时

- 图层标识保存在 Figma 图层名的 `PFL|...` 前缀中，不要手工修改这段前缀。
- 同一 JSON 重复同步不会重复创建图层，也不会覆盖源属性未改变图层的 Figma 手工微调。如果要修改已手工调整的图层，请先把新尺寸和位置写回 JSON。
- 图片用 `image` 元素及 `assets/` 下的 PNG 文件；准确文字、数字、公式和箭头保持为可编辑图层。
- 看 Figma 实际回传的 `figma-preview.png`，检查箭头端点、字体、文字边界、图标大小与遮挡。只通过脚本校验不能代替画布检查。

## 自检

```bash
python -m json.tool figma_incremental/scene.example.json
python figma_incremental/test_bridge.py
node figma_incremental/test_code.cjs
```
