"""1.0.7: tear a live tab out of the tab strip into a native window."""
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
    assert '1.0.6' in s,name
    p.write_text(s.replace('1.0.6','1.0.7'),encoding='utf-8')
edit('make_brand.py',[('0x60000','0x70000',2)])
edit('project/src/main.rs',[
('use tao::platform::windows::WindowBuilderExtWindows;', 'use tao::platform::windows::{WindowBuilderExtWindows,WindowExtWindows};',1),
('fn build_window(target:', '''// Content events carry a process-wide tab ID, not its initial window ID.
fn content_tab(msg:&Msg)->Option<u64>{
    match msg{
        Msg::Title(id,_)|Msg::Loaded(id,_)|Msg::Popup(id,_)|Msg::Download(id,_)|Msg::DownloadStart(id)=>Some(*id),
        _=>None
    }
}
fn active_after_remove(active:usize,removed:usize,remaining:usize)->usize{
    (if removed<active{active.saturating_sub(1)}else{active}).min(remaining.saturating_sub(1))
}
#[repr(C)]
struct CursorPoint{x:i32,y:i32}
#[link(name="user32")] extern "system"{fn GetCursorPos(point:*mut CursorPoint)->i32;}
fn position_at_drop(window:&Window){
    let mut cursor=CursorPoint{x:0,y:0};
    if unsafe{GetCursorPos(&mut cursor)}!=0{
        if window.is_maximized(){window.set_maximized(false);}
        let scale=window.scale_factor();
        window.set_outer_position(tao::dpi::PhysicalPosition::new(cursor.x.saturating_sub((80.0*scale) as i32),cursor.y.saturating_sub((17.0*scale) as i32)));
    }
}
fn build_window(target:''',1),
('        let mut new_window=false;\n        let mut changed=false;', '        let mut new_window=false;\n        let mut detach:Option<(u64,u64)>=None;\n        let mut changed=false;',1),
('            Event::UserEvent(Msg::Routed(id,msg))=>{\n                if let Some(w)=windows.get_mut(&id){','''            Event::UserEvent(Msg::Routed(id,msg))=>{
                // A moved WebView keeps its original callbacks. Resolve the
                // current owner even after the original window has closed.
                let owner=if let Some(tab)=content_tab(&msg){
                    windows.iter().find(|(_,w)|w.app.tabs.iter().any(|t|t.id==tab)).map(|(id,_)|*id)
                }else{Some(id)};
                if let Some(w)=owner.and_then(|id|windows.get_mut(&id)){
                    let id=w.app.proxy.id;''',1),
('                                        "new_window"=>new_window=true,','''                                        "new_window"=>new_window=true,
                                        "detach_tab"=>detach=Some((id,c.id)),''',1),
('        if new_window{\n            if windows.len()<WINDOW_LIMIT{','''        if let Some((source_id,tab_id))=detach{
            let candidate=windows.get(&source_id).and_then(|w|w.app.tabs.iter().position(|t|t.id==tab_id).map(|i|(i,w.app.tabs.len())));
            if let Some((index,count))=candidate{
                if count==1{
                    // A single remaining tab is already an independent window.
                    if let Some(w)=windows.get(&source_id){position_at_drop(&w.app.window);}
                }else if windows.len()>=WINDOW_LIMIT{
                    if let Some(w)=windows.get_mut(&source_id){w.app.notice="Window limit reached (12).".into();w.app.sync();}
                }else{
                    // Create the destination chrome first. Do not mutate the
                    // source until the live controller is successfully moved.
                    let template=windows.get(&source_id).map(|w|&w.app.chrome);
                    let session=WindowSession{tabs:vec![],active:0};
                    match build_window(target,ScopedProxy{inner:raw_proxy.clone(),id:next_id},&base,global.clone(),session,writer.as_ref().unwrap().0.clone(),template){
                        Ok(mut dest)=>{
                            position_at_drop(&dest.app.window);
                            let dest_hwnd=dest.app.window.hwnd();
                            let origin=windows.get_mut(&source_id).unwrap();
                            let origin_hwnd=origin.app.window.hwnd();
                            let tab=&origin.app.tabs[index];
                            let moved=if let Some(v)=tab.view.as_ref(){
                                // Reparent, do not reload or create a second
                                // content WebView. Preserve history and DOM.
                                let _=v.set_visible(false);
                                tab.shown.set(None);
                                match v.reparent(dest_hwnd){
                                    Ok(())=>true,
                                    Err(e)=>{
                                        let _=v.reparent(origin_hwnd);
                                        origin.app.notice=format!("Could not move tab: {e}");
                                        false
                                    }
                                }
                            }else{true}; // A sleeping tab has no live controller.
                            if moved{
                                let tab=origin.app.tabs.remove(index);
                                tab.shown.set(None);tab.low.set(None);tab.hidden_since.set(None);
                                origin.app.active=active_after_remove(origin.app.active,index,origin.app.tabs.len());
                                origin.app.last_layout.set(None);
                                origin.app.show();
                                origin.app.save_due=None;
                                dest.app.tabs.clear();
                                dest.app.tabs.push(tab);
                                dest.app.active=0;
                                dest.app.last_layout.set(None);
                                dest.app.sync();
                                windows.insert(next_id,dest);
                                next_id+=1;
                                changed=true;
                            }else{
                                origin.app.last_layout.set(None);origin.app.layout();origin.app.sync();
                            }
                        }
                        Err(e)=>{if let Some(w)=windows.get_mut(&source_id){w.app.notice=format!("Could not create detached window: {e}");w.app.sync();}}
                    }
                }
            }
        }
        if new_window{
            if windows.len()<WINDOW_LIMIT{''',1),
('mod tests {','''mod tests {
    #[test] fn moved_tab_routes_by_content_identity(){
        use super::{Msg,content_tab,active_after_remove};
        assert_eq!(content_tab(&Msg::Title(4294967297,"moved".into())),Some(4294967297));
        assert_eq!(content_tab(&Msg::DownloadStart(4294967297)),Some(4294967297));
        assert_eq!(content_tab(&Msg::Command("{}".into())),None);
        assert_eq!(active_after_remove(2,0,2),1);
        assert_eq!(active_after_remove(1,1,1),0);
        assert_eq!(active_after_remove(0,1,1),0);
    }
''',1)
])
# Each independent window previously allocated IDs from 1. Give each window
# its own ID range, so callbacks from reparented tabs remain unambiguous.
p=root/'project/src/main.rs'
s=p.read_text(encoding='utf-8')
a=s.index('fn build_window(target:')
b=s.index('fn window_session(',a)
builder=s[a:b]
assert builder.count('next:1,saved')==1
builder=builder.replace('next:1,saved','next:proxy.id*4294967296+1,saved')
p.write_text(s[:a]+builder+s[b:],encoding='utf-8')
edit('project/src/ui.html',[
('</style><body>','''#tabs .select{touch-action:none;user-select:none}
#tabs .tab.is-dragging{opacity:.55}
#tabs .tab.detach-ready{opacity:.85;outline:1px dashed currentColor;outline-offset:-2px}
body.tab-tearing,body.tab-tearing #tabs .select{cursor:grabbing!important}
</style><body>''',1),
("const label=button('',()=>send('select','',t.id));label.className='select';","div.dataset.tabId=String(t.id);const label=button('',()=>send('select','',t.id));label.className='select';",1),
('if(nextTabKey!==tabKey){','if(nextTabKey!==tabKey&&!tabDrag){',1),
("const addressInput=$('address');",'''// Capture a left-button tab gesture; ordinary clicks, X buttons and
// window-title dragging remain separate. Commit tear-off on pointer release.
let tabDrag=null,suppressTabClick=false;
const tabStrip=$('tabs');
function outsideTabStrip(x,y){
    const r=tabStrip.closest('.strip').getBoundingClientRect();
    return y<r.top-12||y>r.bottom+12||x<r.left-12||x>r.right+12;
}
function cleanupTabDrag(){
    const d=tabDrag;tabDrag=null;
    if(!d)return;
    d.tab.classList.remove('is-dragging','detach-ready');
    document.body.classList.remove('tab-tearing');
    if(d.label.hasPointerCapture(d.pointer))d.label.releasePointerCapture(d.pointer);
}
tabStrip.addEventListener('pointerdown',e=>{
    suppressTabClick=false;
    const label=e.target.closest('.select');
    if(!label||e.button!==0||!e.isPrimary||tabDrag)return;
    const tab=label.closest('.tab');
    if(!tab)return;
    tabDrag={pointer:e.pointerId,label,tab,id:Number(tab.dataset.tabId),x:e.clientX,y:e.clientY,moved:false};
    label.setPointerCapture(e.pointerId);
});
document.addEventListener('pointermove',e=>{
    const d=tabDrag;if(!d||d.pointer!==e.pointerId)return;
    if(!d.moved&&Math.hypot(e.clientX-d.x,e.clientY-d.y)<12)return;
    d.moved=true;
    d.tab.classList.add('is-dragging');
    d.tab.classList.toggle('detach-ready',outsideTabStrip(e.clientX,e.clientY));
    document.body.classList.add('tab-tearing');
    e.preventDefault();
});
document.addEventListener('pointerup',e=>{
    const d=tabDrag;if(!d||d.pointer!==e.pointerId)return;
    const tear=d.moved&&outsideTabStrip(e.clientX,e.clientY);
    if(d.moved){suppressTabClick=true;e.preventDefault();}
    cleanupTabDrag();
    if(tear)send('detach_tab','',d.id);
    if(d.moved&&state.tabs)window.renderState(state);
});
function cancelTabGesture(e){
    if(tabDrag&&tabDrag.pointer===e.pointerId){suppressTabClick=tabDrag.moved;cleanupTabDrag();if(state.tabs)window.renderState(state);}
}
document.addEventListener('pointercancel',cancelTabGesture);
document.addEventListener('lostpointercapture',cancelTabGesture);
document.addEventListener('click',e=>{
    if(suppressTabClick&&e.target.closest('#tabs .select')){
        suppressTabClick=false;e.preventDefault();e.stopImmediatePropagation();
    }
},true);
document.addEventListener('keydown',e=>{
    if(e.key==='Escape'&&tabDrag){suppressTabClick=tabDrag.moved;cleanupTabDrag();if(state.tabs)window.renderState(state);e.preventDefault();e.stopImmediatePropagation();}
},true);
const addressInput=$('address');''',1)
])
edit('test_ui.py',[
("    page.locator('#address').fill('test query')",'''    # Tear off a tab, without accidentally selecting or closing it.
    page.evaluate('messages.length=0')
    t=page.locator('#tabs .select').first
    b=t.bounding_box();x=b['x']+b['width']/2;y=b['y']+b['height']/2
    tab_id=page.locator('#tabs .tab').first.evaluate('e=>Number(e.dataset.tabId)')
    page.mouse.move(x,y);page.mouse.down();page.mouse.move(x+2,y)
    assert page.evaluate('messages.length')==0
    page.mouse.move(x,y+65,steps=6)
    assert page.locator('#tabs .detach-ready').count()==1
    page.mouse.up()
    assert page.evaluate('messages.map(m=>m.action)')==['detach_tab']
    assert page.evaluate('messages.at(-1).id')==tab_id
    assert page.locator('#tabs .is-dragging').count()==0
    # Dragging back into the strip cancels tear-off.
    page.evaluate('messages.length=0')
    page.mouse.move(x,y);page.mouse.down();page.mouse.move(x,y+65,steps=5);page.mouse.move(x,y,steps=5);page.mouse.up()
    assert page.evaluate('messages.length')==0
    t.click()
    assert page.evaluate('messages.map(m=>m.action)')==['select']
    page.locator('#address').fill('test query')''',1)
])
