"""1.1.1: smooth pointer-anchored drag feedback and docking transitions."""
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
    p.write_text(s.replace('1.1.0','1.1.1'),encoding='utf-8')
edit('make_brand.py',[('0xFEEF04BD,0x10000,0x10001,0,0x10001,0','0xFEEF04BD,0x10000,0x10001,0x10000,0x10001,0x10000',1)])
edit('project/src/main.rs',[
('struct NativeDragPreview{hwnd:isize,thumbnail:isize,width:i32,height:i32,shown:bool,last:Option<(i32,i32)>}', '''// Keep one grab offset throughout the gesture. Never flip across the pointer
// at monitor edges. A preview may be partially clipped at an edge.
fn preview_anchor(p:CursorPoint,width:i32,height:i32,area:NativeRect)->(i32,i32){
    let y=if p.y.saturating_add(height).saturating_add(12)<=area.bottom{12}else{-height-12};
    (-(width/3).min(80),y)
}
fn anchored_position(p:CursorPoint,offset:(i32,i32))->(i32,i32){
    (p.x.saturating_add(offset.0),p.y.saturating_add(offset.1))
}
struct NativeDragPreview{hwnd:isize,thumbnail:isize,offset:(i32,i32),shown:bool,last:Option<(i32,i32)>}''',1),
('let (x,y)=preview_origin(p,width,height,area);','let offset=preview_anchor(p,width,height,area);\n        let (x,y)=anchored_position(p,offset);',1),
('opacity:245,visible:1,client_only:0','opacity:255,visible:1,client_only:0',1),
('Some(Self{hwnd,thumbnail,width,height,shown:false,last:None})','Some(Self{hwnd,thumbnail,offset,shown:false,last:Some((x,y))})',1),
('''        let area=work_area(p).unwrap_or(NativeRect{left:p.x-1000,top:p.y-800,right:p.x+1000,bottom:p.y+800});
        let xy=preview_origin(p,self.width,self.height,area);''','        let xy=anchored_position(p,self.offset);',1),
('SetWindowPos(self.hwnd,-1,xy.0,xy.1,0,0,0x0001|0x0010)','SetWindowPos(self.hwnd,0,xy.0,xy.1,0,0,0x0001|0x0004|0x0010)',1),
('struct NativeTabDrag{source:u64,tab:u64,started:Instant,preview:Option<NativeDragPreview>,attempted:bool}','struct NativeTabDrag{source:u64,tab:u64,started:Instant,preview:Option<NativeDragPreview>,attempted:bool,last_dock:Option<Instant>}',1),
('started:Instant::now(),preview:None,attempted:false','started:Instant::now(),preview:None,attempted:false,last_dock:None',1),
('next_drag_tick=now+Duration::from_millis(16);','next_drag_tick=now+Duration::from_millis(8);',1),
('if let Some((id,_))=*current{if let Some(w)=windows.get(&id){let _=w.app.chrome.evaluate_script("window.clearTabDropPreview?.()");}}','if let Some((id,_))=*current{if next.map(|(n,_)|n)!=Some(id){if let Some(w)=windows.get(&id){let _=w.app.chrome.evaluate_script("window.clearTabDropPreview?.()");}}}',1),
('''                        if hit.is_none()&&outside&&!d.attempted{
                            d.attempted=true;
                            d.preview=windows.get(&d.source).and_then(|w|NativeDragPreview::create(w.app.window.hwnd(),p));
                        }
                        if let Some(v)=d.preview.as_mut(){v.position(p);v.visible(hit.is_none()&&outside);}''','''                        // Hide immediately when a dock target is entered; only
                        // re-show after a brief stable exit to avoid edge flicker.
                        if hit.is_some(){d.last_dock=Some(now);}
                        let free=hit.is_none()&&outside;
                        let reveal=free&&(!d.attempted||d.last_dock.map(|t|now.saturating_duration_since(t)>=Duration::from_millis(36)).unwrap_or(true));
                        if free&&!d.attempted{
                            d.attempted=true;
                            d.preview=windows.get(&d.source).and_then(|w|NativeDragPreview::create(w.app.window.hwnd(),p));
                        }
                        if let Some(v)=d.preview.as_mut(){v.position(p);v.visible(reveal);}''',1),
('mod tests {','''mod tests {
    #[test] fn drag_anchor_is_stable_across_screen_edges(){
        use super::{NativeRect,CursorPoint,preview_anchor,anchored_position};
        let a=NativeRect{left:-1920,top:0,right:0,bottom:1080};
        let first=CursorPoint{x:-900,y:200};let offset=preview_anchor(first,640,400,a);
        assert_eq!(offset,(-80,12));
        assert_eq!(anchored_position(first,offset),(-980,212));
        let edge=CursorPoint{x:2,y:1078};
        assert_eq!(anchored_position(edge,offset),(-78,1090));
        let offset=preview_anchor(edge,640,400,a);assert_eq!(offset,(-80,-412));
        assert!(anchored_position(edge,offset).1+400<edge.y);
    }
''',1)
])
edit('project/src/ui.html',[
('</style><body>','''/* The drag ghost is visual only; real tab rectangles stay stable for docking. */
#tabDragGhost{position:fixed;left:0;top:0;margin:0;z-index:1002;pointer-events:none;flex:none;will-change:transform;background:var(--tab-active);color:var(--text);border:1px solid var(--tab-border);border-radius:9px;box-shadow:0 4px 12px #0005;overflow:hidden;opacity:1}
#tabDragGhost[hidden]{display:none}
#tabDragGhost *{pointer-events:none}
#tabs .tab.is-dragging:not(.detach-ready){opacity:.30}
#tabDropMarker,#tabDropHint{transition:left 85ms cubic-bezier(.2,.8,.2,1)}
@media(prefers-reduced-motion:reduce){#tabDropMarker,#tabDropHint{transition:none}}
</style><body>''',1),
("function cleanupTabDrag(){",'''function updateDragGhost(d,x,y,outside){
    if(!d.ghost){
        const ghost=d.tab.cloneNode(true);ghost.id='tabDragGhost';
        ghost.classList.remove('is-dragging','detach-ready');ghost.classList.add('active');
        ghost.setAttribute('aria-hidden','true');ghost.inert=true;
        ghost.style.width=d.width+'px';ghost.style.maxWidth=d.width+'px';ghost.style.minWidth=d.width+'px';
        ghost.hidden=true;document.body.append(ghost);d.ghost=ghost;
    }
    d.ghost.hidden=outside;
    if(outside){if(d.frame){cancelAnimationFrame(d.frame);d.frame=0;}return;}
    const r=tabStrip.closest('.strip').getBoundingClientRect();
    d.ghostX=Math.max(r.left,Math.min(r.right-d.width,x-d.grabX));
    d.ghostY=Math.max(r.top,Math.min(r.bottom-d.height,d.top));
    // One compositor-friendly transform per display frame, no delayed cursor easing.
    if(!d.frame)d.frame=requestAnimationFrame(()=>{d.frame=0;if(tabDrag===d&&!d.ghost.hidden)d.ghost.style.transform='translate3d('+d.ghostX+'px,'+d.ghostY+'px,0)';});
    // Set the position before revealing a newly created ghost (no flash at 0,0).
    if(!d.ghost.style.transform)d.ghost.style.transform='translate3d('+d.ghostX+'px,'+d.ghostY+'px,0)';
}
function cleanupTabDrag(){''',1),
("    if(!d)return;\n    d.tab.classList.remove('is-dragging','detach-ready');","    if(!d)return;\n    if(d.frame)cancelAnimationFrame(d.frame);\n    if(d.ghost)d.ghost.remove();\n    d.tab.classList.remove('is-dragging','detach-ready');",1),
("    tabDrag={pointer:e.pointerId,label,tab,id:Number(tab.dataset.tabId),x:e.clientX,y:e.clientY,moved:false,lastProbe:-1000};","    const r=tab.getBoundingClientRect();\n    tabDrag={pointer:e.pointerId,label,tab,id:Number(tab.dataset.tabId),x:e.clientX,y:e.clientY,moved:false,lastProbe:-1000,grabX:e.clientX-r.left,width:r.width,height:r.height,top:r.top,ghost:null,frame:0};",1),
("    if(!d.moved&&Math.hypot(e.clientX-d.x,e.clientY-d.y)<12)return;","    if(!d.moved&&Math.hypot(e.clientX-d.x,e.clientY-d.y)<7)return;",1),
("    d.tab.classList.toggle('detach-ready',outsideTabStrip(e.clientX,e.clientY));","    const outside=outsideTabStrip(e.clientX,e.clientY);\n    d.tab.classList.toggle('detach-ready',outside);\n    updateDragGhost(d,e.clientX,e.clientY,outside);",1),
])
edit('test_ui.py',[
("    # Escape cancellation and native cleanup leave no stuck capture/marker.",'''    # In-strip drag ghost follows the cursor without changing real drop geometry.
    page.evaluate('messages.length=0;telemetry.length=0')
    t=page.locator('#tabs .select').first
    b=t.bounding_box();x=b['x']+b['width']/2;y=b['y']+b['height']/2
    real=page.locator('#tabs .tab').first.bounding_box()['x']
    page.mouse.move(x,y);page.mouse.down();page.mouse.move(x+25,y,steps=5)
    ghost=page.locator('#tabDragGhost')
    ghost.wait_for(state='visible')
    page.wait_for_function("document.querySelector('#tabDragGhost').getBoundingClientRect().x>"+str(real+15))
    assert page.locator('#tabs .tab').first.bounding_box()['x']==real
    page.mouse.move(x+65,y,steps=5)
    page.wait_for_function("document.querySelector('#tabDragGhost').getBoundingClientRect().x>"+str(real+45))
    page.mouse.move(x+65,y+70,steps=5)
    assert not ghost.is_visible()
    page.mouse.move(x+65,y,steps=5)
    assert ghost.is_visible()
    page.keyboard.press('Escape');page.mouse.up()
    assert ghost.count()==0
    assert page.evaluate('messages.length')==0
    assert page.locator('#tabs .is-dragging').count()==0
    # Escape cancellation and native cleanup leave no stuck capture/marker.''',1)
])
