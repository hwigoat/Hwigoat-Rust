"""1.0.8: cross-window tab docking, tab ordering and higher-contrast chrome."""
from pathlib import Path
import sys
root=Path(sys.argv[1])
def edit(name,changes):
    p=root/name
    s=p.read_text(encoding='utf-8')
    for old,new,count in changes:
        if s.count(old)!=count: raise RuntimeError(f'{name}: expected {count} of {old[:120]!r}, got {s.count(old)}')
        s=s.replace(old,new)
    p.write_text(s,encoding='utf-8')
for name in ('project/Cargo.toml','project/src/ui.html','test_ui.py','setup.go','make_brand.py'):
    p=root/name
    s=p.read_text(encoding='utf-8')
    assert '1.0.7' in s,name
    p.write_text(s.replace('1.0.7','1.0.8'),encoding='utf-8')
edit('make_brand.py',[('0x70000','0x80000',2)])
edit('project/src/main.rs',[
('struct LiveWindow{app:App,ready:bool,started:bool,created:Instant}', 'struct LiveWindow{app:App,ready:bool,started:bool,created:Instant,drop_geometry:DropGeometry}',1),
('Ok(LiveWindow{app,ready:false,started:false,created:Instant::now()})','Ok(LiveWindow{app,ready:false,started:false,created:Instant::now(),drop_geometry:DropGeometry::default()})',1),
('#[repr(C)]\nstruct CursorPoint{x:i32,y:i32}\n#[link(name="user32")] extern "system"{fn GetCursorPos(point:*mut CursorPoint)->i32;}','''#[repr(C)]
#[derive(Clone,Copy)]
struct CursorPoint{x:i32,y:i32}
#[link(name="user32")] extern "system"{
    fn GetCursorPos(point:*mut CursorPoint)->i32;
    fn WindowFromPoint(point:CursorPoint)->isize;
    fn GetAncestor(hwnd:isize,flags:u32)->isize;
    fn ScreenToClient(hwnd:isize,point:*mut CursorPoint)->i32;
}
#[derive(Deserialize,Default)]
struct DropGeometry{zones:Vec<DropZone>,tabs:Vec<DropBounds>}
#[derive(Deserialize)]
struct DropZone{left:f64,right:f64,top:f64,bottom:f64,append:bool}
#[derive(Deserialize)]
struct DropBounds{id:u64,left:f64,right:f64}
impl DropGeometry{
    // Use the visible, clipped tab rectangles reported by trusted browser UI.
    fn slot(&self,x:f64,y:f64)->Option<Option<u64>>{
        let zone=self.zones.iter().find(|z|x>=z.left&&x<=z.right&&y>=z.top&&y<=z.bottom)?;
        if zone.append{return Some(None);}
        Some(self.tabs.iter().find(|t|x<(t.left+t.right)/2.0).map(|t|t.id))
    }
    fn valid(&self)->bool{
        self.zones.len()<=2&&self.tabs.len()<=80&&
        self.zones.iter().all(|z|[z.left,z.right,z.top,z.bottom].iter().all(|n|n.is_finite()&&n.abs()<100000.0)&&z.left<=z.right&&z.top<=z.bottom)&&
        self.tabs.iter().all(|t|t.id>0&&t.left.is_finite()&&t.right.is_finite()&&t.left<=t.right&&t.left.abs()<100000.0&&t.right.abs()<100000.0)
    }
}
fn drop_target(windows:&std::collections::BTreeMap<u64,LiveWindow>)->Option<(u64,Option<u64>)>{
    let mut p=CursorPoint{x:0,y:0};
    if unsafe{GetCursorPos(&mut p)}==0{return None;}
    // Respect native stacking/occlusion; do not merge into a hidden window.
    let hit=unsafe{WindowFromPoint(p)};
    if hit==0{return None;}
    let root=unsafe{GetAncestor(hit,2)};
    let (&id,w)=windows.iter().find(|(_,w)|w.app.window.hwnd()==root)?;
    if !w.started||w.app.window.is_minimized(){return None;}
    let mut client=p;
    if unsafe{ScreenToClient(root,&mut client)}==0{return None;}
    let scale=w.app.window.scale_factor();
    let x=client.x as f64/scale;let y=client.y as f64/scale;
    w.drop_geometry.slot(x,y).map(|before|(id,before))
}
fn set_drop_preview(windows:&std::collections::BTreeMap<u64,LiveWindow>,current:&mut Option<(u64,Option<u64>)>,next:Option<(u64,Option<u64>)>){
    if *current==next{return;}
    if let Some((id,_))=*current{if let Some(w)=windows.get(&id){let _=w.app.chrome.evaluate_script("window.clearTabDropPreview?.()");}}
    if let Some((id,before))=next{if let Some(w)=windows.get(&id){
        let value=before.map(|v|v.to_string()).unwrap_or_else(||"null".into());
        let _=w.app.chrome.evaluate_script(&format!("window.showTabDropPreview?.({value})"));
    }}
    *current=next;
}
fn insert_index<T>(items:&[T],before:Option<u64>,id:impl Fn(&T)->u64)->usize{
    before.and_then(|b|items.iter().position(|t|id(t)==b)).unwrap_or(items.len())
}
fn reorder_tab(w:&mut LiveWindow,tab_id:u64,before:Option<u64>)->bool{
    let Some(index)=w.app.tabs.iter().position(|t|t.id==tab_id) else{return false;};
    if before==Some(tab_id){return false;}
    let target=insert_index(&w.app.tabs,before,|t|t.id);
    let target=if index<target{target-1}else{target};
    if index==target{return false;}
    let tab=w.app.tabs.remove(index);
    w.app.tabs.insert(target,tab);w.app.active=target;w.app.panel=false;
    w.app.last_layout.set(None);w.app.show();w.app.save_due=None;true
}
fn dock_tab(origin:&mut LiveWindow,dest:&mut LiveWindow,tab_id:u64,before:Option<u64>)->bool{
    let Some(index)=origin.app.tabs.iter().position(|t|t.id==tab_id) else{return false;};
    if dest.app.tabs.len()>=80{origin.app.notice="Destination has reached its 80-tab limit.".into();origin.app.sync();return false;}
    let source_hwnd=origin.app.window.hwnd();
    let dest_hwnd=dest.app.window.hwnd();
    let tab=&origin.app.tabs[index];
    if let Some(v)=tab.view.as_ref(){
        let _=v.set_visible(false);tab.shown.set(None);
        if let Err(e)=v.reparent(dest_hwnd){
            let _=v.reparent(source_hwnd);
            origin.app.notice=format!("Could not dock tab: {e}");
            origin.app.last_layout.set(None);origin.app.layout();origin.app.sync();return false;
        }
    }
    let tab=origin.app.tabs.remove(index);
    tab.shown.set(None);tab.low.set(None);tab.hidden_since.set(None);
    origin.app.active=active_after_remove(origin.app.active,index,origin.app.tabs.len());
    if !origin.app.tabs.is_empty(){origin.app.last_layout.set(None);origin.app.show();}
    origin.app.save_due=None;
    let target=insert_index(&dest.app.tabs,before,|t|t.id);
    dest.app.tabs.insert(target,tab);dest.app.active=target;dest.app.panel=false;
    dest.app.last_layout.set(None);dest.app.show();dest.app.save_due=None;
    true
}''',1),
('    let mut launch_reported=false;\n    ev.run(move|event,target,flow|{','    let mut launch_reported=false;\n    let mut hovered_drop:Option<(u64,Option<u64>)>=None;\n    ev.run(move|event,target,flow|{',1),
('let mut detach:Option<(u64,u64)>=None;','let mut detach:Option<(u64,u64,bool)>=None;\n        let mut preview=false;\n        let mut clear_preview=false;',1),
('                                if c.action=="ready"{','''                                if c.action=="tab_geometry"{
                                    if c.value.len()<16000{
                                        if let Ok(g)=serde_json::from_str::<DropGeometry>(&c.value){if g.valid(){w.drop_geometry=g;}}
                                    }
                                }else if c.action=="ready"{''',1),
('                                        "detach_tab"=>detach=Some((id,c.id)),','''                                        "drag_hover"=>{if app.tabs.iter().any(|t|t.id==c.id){preview=true;}},
                                        "drag_cancel"=>clear_preview=true,
                                        "detach_tab"=>{clear_preview=true;detach=Some((id,c.id,c.value=="outside"));},''',1),
('        if let Some((id,last_tab))=close{','''        if clear_preview||close.is_some(){set_drop_preview(&windows,&mut hovered_drop,None);}
        else if preview{let hit=drop_target(&windows);set_drop_preview(&windows,&mut hovered_drop,hit);}
        if let Some((id,last_tab))=close{''',1),
('        if let Some((source_id,tab_id))=detach{\n            let candidate=', '''        if let Some((source_id,tab_id,outside))=detach{
            if let Some((target_id,before))=drop_target(&windows){
                if target_id==source_id{
                    if let Some(w)=windows.get_mut(&source_id){if reorder_tab(w,tab_id,before){changed=true;}}
                }else if let Some(mut source)=windows.remove(&source_id){
                    let success=windows.get_mut(&target_id).map(|dest|dock_tab(&mut source,dest,tab_id,before)).unwrap_or(false);
                    // Only close an empty source after successful transfer. The
                    // destination retains the live content and global event IDs.
                    if !success||!source.app.tabs.is_empty(){windows.insert(source_id,source);}
                    if success{changed=true;}
                }
            }else if outside{
            let candidate=''',1),
('        if new_window{\n            if windows.len()<WINDOW_LIMIT{','        }\n        if new_window{\n            if windows.len()<WINDOW_LIMIT{',1),
('mod tests {','''mod tests {
    #[test] fn tab_drop_slots_and_bounds(){
        use super::{DropGeometry,insert_index};
        let g:DropGeometry=serde_json::from_str(r#"{"zones":[{"left":8,"right":200,"top":4,"bottom":39,"append":false},{"left":300,"right":500,"top":4,"bottom":39,"append":true}],"tabs":[{"id":7,"left":8,"right":100},{"id":9,"left":100,"right":200}]}"#).unwrap();
        assert!(g.valid());assert_eq!(g.slot(20.,15.),Some(Some(7)));assert_eq!(g.slot(120.,15.),Some(Some(9)));
        assert_eq!(g.slot(180.,15.),Some(None));assert_eq!(g.slot(350.,15.),Some(None));
        assert_eq!(g.slot(250.,15.),None);assert_eq!(g.slot(20.,50.),None);
        assert_eq!(insert_index(&[7u64,9],Some(9),|v|*v),1);assert_eq!(insert_index(&[7u64,9],None,|v|*v),2);
    }
''',1)
])
edit('project/src/ui.html',[
('</style><body>','''/* High-contrast monochrome chrome. Retain the native 40 + 48px layout. */
body{--tab-idle:#202020;--tab-active:#383838;--tab-idle-text:#dedede;--tab-border:#565656;--drop-ink:#fafafa;--drop-bg:#1b1b1b}
body.light{--tab-idle:#e0e0e0;--tab-active:#fff;--tab-idle-text:#343434;--tab-border:#a0a0a0;--drop-ink:#151515;--drop-bg:#fff}
#tabs{gap:3px}.tab{background:var(--tab-idle);color:var(--tab-idle-text);border:1px solid transparent;border-bottom:0;padding-left:8px}
.tab.active{background:var(--tab-active);color:var(--text);border-color:var(--tab-border);box-shadow:inset 0 2px 0 var(--accent)}
.tab:not(.active):not(:hover)::after{display:none}
.tab:not(.active):hover{background:var(--hover);color:var(--text)}
.tab .select{font-size:13px;font-weight:500;gap:7px}.tab.active .select{font-weight:650}
.tab .close{color:var(--tab-idle-text)}.tab .close:hover{background:var(--hover);color:var(--text)}
#tabs .tab.is-dragging{opacity:.48}
#tabs .tab.detach-ready{opacity:.88;outline:1px dashed var(--accent);outline-offset:-2px}
.toolbar .icon svg,.strip>.icon svg{stroke-width:1.9}
.toolbar form{border-color:var(--tab-border)}.toolbar form:focus-within{border-color:var(--accent)}
#dragArea{position:relative}
#tabDropMarker{position:fixed;z-index:1000;pointer-events:none;top:5px;width:3px;height:33px;background:var(--drop-ink);border-radius:3px;box-shadow:0 0 0 2px var(--drop-bg)}
#tabDropMarker::after{content:'';position:absolute;top:-2px;left:-3px;border-left:4px solid transparent;border-right:4px solid transparent;border-top:5px solid var(--drop-ink)}
#tabDropHint{position:fixed;z-index:1000;pointer-events:none;top:41px;max-width:210px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;padding:5px 9px;border:1px solid var(--tab-border);background:var(--drop-bg);color:var(--drop-ink);border-radius:7px;font-size:11px;font-weight:600;box-shadow:0 2px 8px #0004}
body.tab-drop-target #dragArea{background:var(--hover);border-radius:8px 8px 0 0}
</style><body>''',1),
("let tabDrag=null,suppressTabClick=false;\nconst tabStrip=$('tabs');",'''let tabDrag=null,suppressTabClick=false;
const tabStrip=$('tabs');
let geometryKey='',dropPreview=null,previewActive=false;
const dropMarker=document.createElement('div');dropMarker.id='tabDropMarker';dropMarker.hidden=true;
const dropHint=document.createElement('div');dropHint.id='tabDropHint';dropHint.hidden=true;dropHint.textContent='여기에 탭 놓기';
document.body.append(dropMarker,dropHint);
function reportTabGeometry(){
    const r=tabStrip.getBoundingClientRect();
    const d=$('dragArea').getBoundingClientRect();
    const zones=[];
    if(r.width>0&&r.height>0)zones.push({left:r.left,right:r.right,top:r.top,bottom:r.bottom,append:false});
    if(d.width>0&&d.height>0)zones.push({left:d.left,right:d.right,top:d.top,bottom:d.bottom,append:true});
    const tabs=[];
    for(const el of tabStrip.querySelectorAll('.tab')){
        const t=el.getBoundingClientRect(),left=Math.max(r.left,t.left),right=Math.min(r.right,t.right);
        if(right>left)tabs.push({id:Number(el.dataset.tabId),left,right});
    }
    const value=JSON.stringify({zones,tabs});
    if(value!==geometryKey){geometryKey=value;send('tab_geometry',value);}
}
function paintDropPreview(){
    if(!previewActive)return;
    const r=tabStrip.getBoundingClientRect();
    const tabs=Array.from(tabStrip.querySelectorAll('.tab'));
    const before=tabs.find(t=>Number(t.dataset.tabId)===dropPreview);
    const x=before?before.getBoundingClientRect().left:tabs.length?Math.min(r.right,tabs[tabs.length-1].getBoundingClientRect().right):r.left;
    const at=Math.max(2,Math.min(innerWidth-5,x));
    dropMarker.style.left=at+'px';
    dropHint.style.left=Math.max(6,Math.min(innerWidth-150,at+7))+'px';
    dropMarker.hidden=false;dropHint.hidden=false;
}
window.showTabDropPreview=before=>{previewActive=true;dropPreview=before;document.body.classList.add('tab-drop-target');paintDropPreview();};
window.clearTabDropPreview=()=>{previewActive=false;dropPreview=null;dropMarker.hidden=true;dropHint.hidden=true;document.body.classList.remove('tab-drop-target');};
const geometryChanged=()=>{reportTabGeometry();paintDropPreview();};
window.addEventListener('resize',geometryChanged);
window.addEventListener('scroll',geometryChanged,{passive:true});
tabStrip.addEventListener('scroll',geometryChanged,{passive:true});
''',1),
('tabDrag={pointer:e.pointerId,label,tab,id:Number(tab.dataset.tabId),x:e.clientX,y:e.clientY,moved:false};','tabDrag={pointer:e.pointerId,label,tab,id:Number(tab.dataset.tabId),x:e.clientX,y:e.clientY,moved:false,lastProbe:-1000};',1),
("    document.body.classList.add('tab-tearing');\n    e.preventDefault();","    document.body.classList.add('tab-tearing');\n    const now=performance.now();if(now-d.lastProbe>=50){d.lastProbe=now;send('drag_hover','',d.id);}\n    e.preventDefault();",1),
("    if(tear)send('detach_tab','',d.id);","    if(d.moved)send('detach_tab',tear?'outside':'inside',d.id);",1),
("if(tabDrag&&tabDrag.pointer===e.pointerId){suppressTabClick=tabDrag.moved;cleanupTabDrag();if(state.tabs)window.renderState(state);}","if(tabDrag&&tabDrag.pointer===e.pointerId){suppressTabClick=tabDrag.moved;if(tabDrag.moved)send('drag_cancel','',tabDrag.id);cleanupTabDrag();if(state.tabs)window.renderState(state);}",1),
("if(e.key==='Escape'&&tabDrag){suppressTabClick=tabDrag.moved;cleanupTabDrag();","if(e.key==='Escape'&&tabDrag){suppressTabClick=tabDrag.moved;if(tabDrag.moved)send('drag_cancel','',tabDrag.id);cleanupTabDrag();",1),
("if(s.panel&&listKey!==JSON.stringify([s.bookmarks,s.history,$('filter').value.toLowerCase()]))lists()};","if(s.panel&&listKey!==JSON.stringify([s.bookmarks,s.history,$('filter').value.toLowerCase()]))lists();geometryChanged()};",1)
])
edit('test_ui.py',[
("window.messages=[];window.ipc={postMessage:s=>window.messages.push(JSON.parse(s))};","window.messages=[];window.telemetry=[];window.ipc={postMessage:s=>{const m=JSON.parse(s);(['tab_geometry','drag_hover','drag_cancel'].includes(m.action)?telemetry:messages).push(m)}};",1),
("# Dragging back into the strip cancels tear-off.","# Returning to the strip requests an in-window drop (native decides reorder/no-op).",1),
("    assert page.evaluate('messages.length')==0\n    t.click()\n    assert page.evaluate('messages.map(m=>m.action)')==['select']","    assert page.evaluate('messages.map(m=>m.action)')==['detach_tab']\n    assert page.evaluate('messages.at(-1).value')=='inside'\n    page.evaluate('messages.length=0')\n    t.click()\n    assert page.evaluate('messages.map(m=>m.action)')==['select']",1),
("    page.locator('#address').fill('test query')",'''    # Geometry telemetry and a native-requested docking indicator.
    g=page.evaluate("JSON.parse(telemetry.filter(m=>m.action==='tab_geometry').at(-1).value)")
    assert g['zones'] and g['tabs']
    assert page.evaluate("telemetry.some(m=>m.action==='drag_hover')")
    page.evaluate('id=>window.showTabDropPreview(id)',g['tabs'][0]['id'])
    assert page.locator('#tabDropMarker').is_visible()
    assert page.locator('#tabDropHint').inner_text()=='여기에 탭 놓기'
    page.evaluate('window.clearTabDropPreview()')
    assert not page.locator('#tabDropMarker').is_visible()
    render(light=False)
    assert page.locator('.tab.active').evaluate('e=>getComputedStyle(e).backgroundColor')=='rgb(56, 56, 56)'
    render(light=True)
    assert page.locator('.tab.active').evaluate('e=>getComputedStyle(e).backgroundColor')=='rgb(255, 255, 255)'
    render(light=False)
    page.locator('#address').fill('test query')''',1)
])
