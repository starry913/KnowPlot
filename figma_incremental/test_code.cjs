// Minimal Figma API contract test: create, no-op, targeted update, explicit delete.
const fs = require('fs');
const vm = require('vm');
const assert = require('assert');

let nextId = 1;
function node(type) {
  const n = {
    type, id: String(nextId++), children: [], parent: null, height: 1,
    x: 0, y: 0, width: 1, name: '',
    setPluginData() { throw Error('Cannot set private plugin data without an ID'); },
    getPluginData() { throw Error('Cannot get private plugin data without an ID'); },
    resize(w,h) { this.width=w; this.height=h; },
    appendChild(ch) { if(ch.parent)ch.remove();this.children.push(ch);ch.parent=this; },
    insertChild(i,ch) { if(ch.parent)ch.remove();this.children.splice(i,0,ch);ch.parent=this; },
    remove() { if(this.parent) this.parent.children.splice(this.parent.children.indexOf(this),1);this.parent=null; },
    findAll(pred) { return this.children.flatMap(ch=>[...(pred(ch)?[ch]:[]),...ch.findAll(pred)]); },
    findOne(pred) { return this.findAll(pred)[0] || null; },
    async exportAsync() { return Uint8Array.from([137,80,78,71]); }
  };
  return n;
}
const page=node('PAGE');
const figma={
  currentPage:page, ui:{onmessage:null,postMessage(m){figma.last=m}},
  showUI(){},viewport:{scrollAndZoomIntoView(){}},
  createFrame:()=>{const n=node('FRAME');page.appendChild(n);return n},
  createRectangle:()=>{const n=node('RECTANGLE');page.appendChild(n);return n},
  createEllipse:()=>{const n=node('ELLIPSE');page.appendChild(n);return n},
  createText:()=>{const n=node('TEXT');page.appendChild(n);return n},
  createNodeFromSvg:()=>{const n=node('FRAME');page.appendChild(n);return n},
  createImage:(bytes)=>({hash:'test-image-'+bytes.length,async getSizeAsync(){return {width:100,height:100}}}),
  async loadFontAsync(){return}
};
vm.runInNewContext(fs.readFileSync(__dirname+'/code.js','utf8'),{figma,__html__:''});
const scene=JSON.parse(fs.readFileSync(__dirname+'/scene.example.json','utf8'));
for(const e of scene.elements) if(e.type==='image') e.imageBytes=Array.from(fs.readFileSync(__dirname+'/assets/'+e.asset));
async function apply(s){await figma.ui.onmessage({type:'apply',scene:s});assert(figma.last.ok,figma.last.error);return figma.last}
(async()=>{
  const first=await apply(scene);
  assert.strictEqual(first.stats.created,scene.elements.length);
  assert.strictEqual(first.stats.updated,0);
  const frame=page.findOne(n=>n.name.startsWith('PFL|S|'+scene.id+'|'));
  assert(frame);
  const title=frame.findOne(n=>n.name.startsWith('PFL|E|template-name|'));
  const originalId=title.id;
  title.x=1234; // manual Figma adjustment
  const second=await apply(scene);
  assert.strictEqual(second.stats.unchanged,scene.elements.length);
  assert.strictEqual(title.x,1234,'unchanged code should preserve manual move');
  const changed=JSON.parse(JSON.stringify(scene));
  changed.elements.find(e=>e.id==='template-name').text+=' (revised)';
  const third=await apply(changed);
  assert.strictEqual(third.stats.updated,1);
  assert.strictEqual(third.stats.unchanged,scene.elements.length-1);
  assert.strictEqual(frame.findOne(n=>n.name.startsWith('PFL|E|template-name|')).id,originalId,'native text layer must survive');
  changed.delete=['main-divider'];
  changed.elements=changed.elements.filter(e=>e.id!=='main-divider');
  const fourth=await apply(changed);
  assert.strictEqual(fourth.stats.deleted,1);
  assert.strictEqual(frame.findOne(n=>n.name.startsWith('PFL|E|main-divider|')),null);
  console.log('incremental scene tests passed');
})().catch(e=>{console.error(e);process.exitCode=1});
