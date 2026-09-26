/* KnowPlot Live: local, incremental scene sync for Figma Design. */
figma.showUI(__html__, { width: 440, height: 640, themeColors: true });

// Development plugins imported without a Figma-assigned manifest ID cannot use
// private plugin data. Stable IDs and source hashes live in native layer names.
const SCENE_MARK = "PFL|S|";
const ELEMENT_MARK = "PFL|E|";
function frameName(id, title) { return SCENE_MARK + id + "| " + (title || id); }
function elementName(e, sourceHash) {
  return ELEMENT_MARK + e.id + "|" + e.type + "|" + sourceHash + "| " + (e.name || e.id);
}
function elementMeta(node) {
  const match = /^PFL\|E\|([a-zA-Z0-9_-]{1,80})\|(rect|ellipse|text|svg|arrow|image)\|([a-f0-9]+)\|/.exec(node.name || "");
  return match ? { id: match[1], kind: match[2], hash: match[3] } : null;
}
const FONT_FALLBACKS = [
  { family: "Arial", style: "Regular" },
  { family: "Inter", style: "Regular" }
];

function hash(value) {
  const s = JSON.stringify(value);
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return (h >>> 0).toString(16);
}
function finite(v, name) {
  if (typeof v !== "number" || !Number.isFinite(v)) throw Error(name + " 必须是有限数字");
  return v;
}
function positive(v, name) {
  if (finite(v, name) <= 0) throw Error(name + " 必须大于 0");
  return v;
}
function color(hex, fallback) {
  const c = hex == null ? fallback : hex;
  if (c === "none") return null;
  if (typeof c !== "string" || !/^#[0-9a-fA-F]{6}$/.test(c)) throw Error("颜色必须是 #RRGGBB: " + c);
  return { r: parseInt(c.slice(1, 3), 16) / 255,
           g: parseInt(c.slice(3, 5), 16) / 255,
           b: parseInt(c.slice(5, 7), 16) / 255 };
}
function paint(c) { return c ? [{ type: "SOLID", color: c }] : []; }
function esc(s) { return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;"); }
function assertScene(scene) {
  if (!scene || typeof scene !== "object") throw Error("场景必须是 JSON 对象");
  if (!/^[a-zA-Z0-9_-]{1,80}$/.test(scene.id || "")) throw Error("scene.id 需要稳定的英文 ID");
  if (!scene.canvas || typeof scene.canvas !== "object") throw Error("缺少 canvas");
  positive(scene.canvas.width, "canvas.width"); positive(scene.canvas.height, "canvas.height");
  if (scene.canvas.width > 10000 || scene.canvas.height > 10000) throw Error("画布尺寸过大");
  if (!Array.isArray(scene.elements) || scene.elements.length > 500) throw Error("elements 必须是至多 500 项的数组");
  const seen = new Set();
  for (const e of scene.elements) {
    if (!e || !/^[a-zA-Z0-9_-]{1,80}$/.test(e.id || "")) throw Error("每个图层需要稳定的英文 id");
    if (seen.has(e.id)) throw Error("重复图层 ID: " + e.id);
    seen.add(e.id);
    if (!["rect", "ellipse", "text", "svg", "arrow", "image"].includes(e.type)) throw Error("不支持的图层类型: " + e.type);
    if (e.type === "arrow") {
      ["x1", "y1", "x2", "y2"].forEach(k => finite(e[k], e.id + "." + k));
    } else {
      finite(e.x, e.id + ".x"); finite(e.y, e.id + ".y");
      positive(e.w, e.id + ".w"); positive(e.h, e.id + ".h");
    }
    if (e.type === "text" && typeof e.text !== "string") throw Error(e.id + ".text 必须是字符串");
    if (e.type === "svg" && (typeof e.svg !== "string" || !e.svg.trim().startsWith("<svg") || e.svg.length > 100000)) throw Error(e.id + ".svg 需要完整且小于 100KB 的 SVG");
    if (e.type === "image" && (!/^[a-zA-Z0-9_.-]+\.png$/.test(e.asset || "") || !Array.isArray(e.imageBytes))) throw Error(e.id + ".image 需要本地 PNG 素材");
  }
  if (scene.delete != null && (!Array.isArray(scene.delete) || scene.delete.some(id => typeof id !== "string"))) throw Error("delete 应是 ID 数组");
  if ((scene.delete || []).some(id => seen.has(id))) throw Error("同一个 ID 不能同时出现在 elements 和 delete");
}
function findFrame(sceneId) {
  return figma.currentPage.findOne(node => node.type === "FRAME" && (node.name || "").startsWith(SCENE_MARK + sceneId + "|"));
}
function findElements(frame) {
  const m = new Map();
  for (const node of frame.children) {
    const meta = elementMeta(node);
    if (meta) m.set(meta.id, node);
  }
  return m;
}
async function fontFor(e) {
  const candidates = e.fontFamily ? [{ family: e.fontFamily, style: e.fontStyle || "Regular" }, ...FONT_FALLBACKS] : FONT_FALLBACKS;
  for (const f of candidates) {
    try { await figma.loadFontAsync(f); return f; } catch (_) { /* next installed font */ }
  }
  throw Error("无法加载可用字体：" + (e.fontFamily || "Arial / Inter"));
}
function arrowSvg(e) {
  const pad = 8, x = Math.min(e.x1, e.x2) - pad, y = Math.min(e.y1, e.y2) - pad;
  const w = Math.max(Math.abs(e.x2 - e.x1) + pad * 2, 16);
  const h = Math.max(Math.abs(e.y2 - e.y1) + pad * 2, 16);
  const a = { x: e.x1 - x, y: e.y1 - y }, b = { x: e.x2 - x, y: e.y2 - y };
  const dx = b.x - a.x, dy = b.y - a.y, len = Math.hypot(dx, dy) || 1;
  const ux = dx / len, uy = dy / len, head = e.head === false ? 0 : (e.headSize || 7);
  const lineEnd = { x: b.x - ux * head * .75, y: b.y - uy * head * .75 };
  const stroke = e.stroke || "#1D2430", weight = e.weight || 1.5;
  color(stroke);
  const body = `<line x1="${a.x}" y1="${a.y}" x2="${lineEnd.x}" y2="${lineEnd.y}" stroke="${esc(stroke)}" stroke-width="${weight}" stroke-linecap="round"/>`;
  const wing = head ? `<path d="M ${b.x} ${b.y} L ${b.x - ux * head - uy * head * .47} ${b.y - uy * head + ux * head * .47} L ${b.x - ux * head + uy * head * .47} ${b.y - uy * head - ux * head * .47} Z" fill="${esc(stroke)}"/>` : "";
  return { x, y, w, h, svg: `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}">${body}${wing}</svg>` };
}
function createElement(e) {
  if (e.type === "rect" || e.type === "image") return figma.createRectangle();
  if (e.type === "ellipse") return figma.createEllipse();
  if (e.type === "text") return figma.createText();
  if (e.type === "svg") return figma.createNodeFromSvg(e.svg);
  return figma.createNodeFromSvg(arrowSvg(e).svg);
}
async function styleElement(node, e, warnings) {
  if (e.type === "arrow") {
    const g = arrowSvg(e); node.x = g.x; node.y = g.y; node.resize(g.w, g.h);
    return;
  }
  node.x = e.x; node.y = e.y;
  if (e.type === "svg") { node.resize(e.w, e.h); return; }
  if (e.type === "image") {
    node.resize(e.w, e.h);
    const img = figma.createImage(new Uint8Array(e.imageBytes));
    await img.getSizeAsync();
    node.fills = [{ type: "IMAGE", imageHash: img.hash, scaleMode: "FIT" }];
    node.strokes = [];
    return;
  }
  if (e.type === "text") {
    const f = await fontFor(e);
    node.fontName = f;
    node.characters = e.text;
    node.fontSize = positive(e.fontSize || 14, e.id + ".fontSize");
    node.textAlignHorizontal = e.align || "LEFT";
    node.textAlignVertical = e.valign || "TOP";
    node.textAutoResize = "HEIGHT";
    node.resize(e.w, Math.max(e.h, 1));
    node.fills = paint(color(e.color, "#17191C"));
    if (e.lineHeight) node.lineHeight = { unit: "PIXELS", value: positive(e.lineHeight, e.id + ".lineHeight") };
    if (node.height > e.h + 1) warnings.push(`${e.id}: 文字高度 ${Math.ceil(node.height)} 超出预留 ${e.h}`);
    return;
  }
  node.resize(e.w, e.h);
  node.fills = paint(color(e.fill, "none"));
  node.strokes = paint(color(e.stroke, "none"));
  node.strokeWeight = e.strokeWeight || 1;
  if (e.type === "rect") node.cornerRadius = e.radius || 0;
  node.dashPattern = e.dash || [];
}
async function applyScene(scene) {
  assertScene(scene);
  let frame = findFrame(scene.id), createdFrame = false;
  if (!frame) {
    frame = figma.createFrame(); frame.name = frameName(scene.id, scene.title);
    frame.x = 100; frame.y = 100;
    frame.layoutMode = "NONE"; frame.clipsContent = false; createdFrame = true;
  }
  frame.resize(scene.canvas.width, scene.canvas.height);
  frame.fills = paint(color(scene.canvas.background, "#FFFFFF"));
  const existing = findElements(frame), warnings = [], stats = { created: 0, updated: 0, unchanged: 0, deleted: 0 };
  for (const e of scene.elements) {
    const nextHash = hash(e.type === "image" ? { ...e, imageBytes: undefined } : e);
    let node = existing.get(e.id);
    const oldMeta = node && elementMeta(node);
    if (oldMeta && oldMeta.hash === nextHash) { stats.unchanged++; continue; }
    const oldKind = oldMeta && oldMeta.kind;
    // SVG imports and arrows have Figma-managed vector internals; replace only that layer.
    if (node && (oldKind !== e.type || e.type === "svg" || e.type === "arrow")) {
      const index = frame.children.indexOf(node);
      const replacement = createElement(e); frame.insertChild(index, replacement); node.remove(); node = replacement;
    } else if (!node) {
      node = createElement(e); frame.appendChild(node);
    }
    await styleElement(node, e, warnings);
    node.name = elementName(e, nextHash);
    if (existing.has(e.id)) stats.updated++; else stats.created++;
  }
  for (const id of scene.delete || []) {
    const node = existing.get(id);
    if (node) { node.remove(); stats.deleted++; }
  }
  if (createdFrame) figma.viewport.scrollAndZoomIntoView([frame]);
  figma.currentPage.selection = [frame];
  const bytes = await frame.exportAsync({ format: "PNG", constraint: { type: "SCALE", value: 1 } });
  return { stats, warnings, preview: Array.from(bytes), frameId: frame.id };
}

figma.ui.onmessage = async msg => {
  if (msg.type !== "apply") return;
  try {
    const result = await applyScene(msg.scene);
    figma.ui.postMessage({ type: "result", ok: true, ...result });
  } catch (error) {
    figma.ui.postMessage({ type: "result", ok: false, error: String(error.message || error) });
  }
};
