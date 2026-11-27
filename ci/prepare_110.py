"""1.1.0: live native drag preview, magnetic docking, black theme, stability."""
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
    assert '1.0.8' in s,name
    p.write_text(s.replace('1.0.8','1.1.0'),encoding='utf-8')
edit('make_brand.py',[('0xFEEF04BD,0x10000,0x10000,0x80000,0x10000,0x80000','0xFEEF04BD,0x10000,0x10001,0,0x10001,0',1)])
edit('project/src/main.rs',[
('    fn ScreenToClient(hwnd:isize,point:*mut CursorPoint)->i32;\n}', '''    fn ScreenToClient(hwnd:isize,point:*mut CursorPoint)->i32;
    fn GetAsyncKeyState(key:i32)->i16;
    fn CreateWindowExW(ex_style:u32,class:*const u16,title:*const u16,style:u32,x:i32,y:i32,width:i32,height:i32,parent:isize,menu:isize,instance:isize,param:*mut std::ffi::c_void)->isize;
    fn DestroyWindow(hwnd:isize)->i32;
    fn SetWindowPos(hwnd:isize,after:isize,x:i32,y:i32,cx:i32,cy:i32,flags:u32)->i32;
    fn ShowWindow(hwnd:isize,cmd:i32)->i32;
    fn GetWindowRect(hwnd:isize,rect:*mut NativeRect)->i32;
    fn GetClientRect(hwnd:isize,rect:*mut NativeRect)->i32;
    fn MonitorFromPoint(point:CursorPoint,flags:u32)->isize;
    fn GetMonitorInfoW(monitor:isize,info:*mut NativeMonitorInfo)->i32;
}
#[repr(C)]
#[derive(Clone,Copy,Default)]
struct NativeRect{left:i32,top:i32,right:i32,bottom:i32}
#[repr(C)]
struct NativeMonitorInfo{size:u32,monitor:NativeRect,work:NativeRect,flags:u32}
#[repr(C)]
struct NativeThumbnailProperties{flags:u32,destination:NativeRect,source:NativeRect,opacity:u8,visible:i32,client_only:i32}
#[link(name="dwmapi")] extern "system"{
    fn DwmRegisterThumbnail(destination:isize,source:isize,thumbnail:*mut isize)->i32;
    fn DwmUpdateThumbnailProperties(thumbnail:isize,properties:*const NativeThumbnailProperties)->i32;
    fn DwmUnregisterThumbnail(thumbnail:isize)->i32;
}
fn cursor_point()->Option<CursorPoint>{
    let mut p=CursorPoint{x:0,y:0};if unsafe{GetCursorPos(&mut p)}!=0{Some(p)}else{None}
}
fn mouse_held()->bool{unsafe{GetAsyncKeyState(0x01)}<0}
fn escape_held()->bool{unsafe{GetAsyncKeyState(0x1b)}<0}
fn work_area(p:CursorPoint)->Option<NativeRect>{
    let monitor=unsafe{MonitorFromPoint(p,2)};
    let mut info=NativeMonitorInfo{size:std::mem::size_of::<NativeMonitorInfo>() as u32,monitor:NativeRect::default(),work:NativeRect::default(),flags:0};
    if monitor!=0&&unsafe{GetMonitorInfoW(monitor,&mut info)}!=0{Some(info.work)}else{None}
}
// Keep the preview clear of the cursor, including on negative-coordinate monitors.
fn preview_origin(p:CursorPoint,width:i32,height:i32,area:NativeRect)->(i32,i32){
    let x=if p.x.saturating_add(18).saturating_add(width)<=area.right{p.x.saturating_add(18)}else{p.x.saturating_sub(width).saturating_sub(18)};
    let y=if p.y.saturating_add(18).saturating_add(height)<=area.bottom{p.y.saturating_add(18)}else{p.y.saturating_sub(height).saturating_sub(18)};
    // Avoid clamping the preview back on top of the cursor.
    (x,y)
}
fn bounded_window_origin(p:CursorPoint,width:i32,height:i32,area:NativeRect)->(i32,i32){
    let max_x=(area.right.saturating_sub(width)).max(area.left);
    let max_y=(area.bottom.saturating_sub(height)).max(area.top);
    (p.x.saturating_sub(80).clamp(area.left,max_x),p.y.saturating_sub(17).clamp(area.top,max_y))
}
// This is a real, non-activating native Windows preview window. DWM mirrors
// the live source window; the tab/controller itself is moved only on commit.
struct NativeDragPreview{hwnd:isize,thumbnail:isize,width:i32,height:i32,shown:bool,last:Option<(i32,i32)>}
impl NativeDragPreview{
    fn create(source:isize,p:CursorPoint)->Option<Self>{
        let mut source_rect=NativeRect::default();
        if unsafe{GetWindowRect(source,&mut source_rect)}==0{return None;}
        let sw=(source_rect.right-source_rect.left).max(1);
        let sh=(source_rect.bottom-source_rect.top).max(1);
        let area=work_area(p).unwrap_or(NativeRect{left:p.x-1000,top:p.y-800,right:p.x+1000,bottom:p.y+800});
        let maxw=((area.right-area.left)/2-24).clamp(220,720);
        let maxh=((area.bottom-area.top)/2-24).clamp(150,460);
        let scale=(maxw as f64/sw as f64).min(maxh as f64/sh as f64).min(0.8);
        let width=((sw as f64*scale).round() as i32).max(120);
        let height=((sh as f64*scale).round() as i32).max(90);
        let (x,y)=preview_origin(p,width,height,area);
        let class:Vec<u16>="STATIC".encode_utf16().chain(Some(0)).collect();
        let title:Vec<u16>="Hwigoat Rust".encode_utf16().chain(Some(0)).collect();
        // WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE | WS_EX_TOPMOST; never a taskbar item.
        let hwnd=unsafe{CreateWindowExW(0x08000088,class.as_ptr(),title.as_ptr(),0x80800000,x,y,width,height,0,0,0,std::ptr::null_mut())};
        if hwnd==0{return None;}
        let mut thumbnail=0;
        if unsafe{DwmRegisterThumbnail(hwnd,source,&mut thumbnail)}<0{
            unsafe{DestroyWindow(hwnd)};return None;
        }
        let mut client=NativeRect::default();
        if unsafe{GetClientRect(hwnd,&mut client)}==0{
            unsafe{DwmUnregisterThumbnail(thumbnail);DestroyWindow(hwnd);};return None;
        }
        let properties=NativeThumbnailProperties{flags:0x1|0x4|0x8,destination:client,source:NativeRect::default(),opacity:245,visible:1,client_only:0};
        if unsafe{DwmUpdateThumbnailProperties(thumbnail,&properties)}<0{
            unsafe{DwmUnregisterThumbnail(thumbnail);DestroyWindow(hwnd);};return None;
        }
        Some(Self{hwnd,thumbnail,width,height,shown:false,last:None})
    }
    fn position(&mut self,p:CursorPoint){
        let area=work_area(p).unwrap_or(NativeRect{left:p.x-1000,top:p.y-800,right:p.x+1000,bottom:p.y+800});
        let xy=preview_origin(p,self.width,self.height,area);
        if self.last!=Some(xy){
            if unsafe{SetWindowPos(self.hwnd,-1,xy.0,xy.1,0,0,0x0001|0x0010)}!=0{self.last=Some(xy);}
        }
    }
    fn visible(&mut self,show:bool){
        if show!=self.shown{unsafe{ShowWindow(self.hwnd,if show{4}else{0});};self.shown=show;}
    }
}
impl Drop for NativeDragPreview{
    fn drop(&mut self){unsafe{DwmUnregisterThumbnail(self.thumbnail);DestroyWindow(self.hwnd);}}
}
struct NativeTabDrag{source:u64,tab:u64,started:Instant,preview:Option<NativeDragPreview>,attempted:bool}
fn outside_source_strip(windows:&std::collections::BTreeMap<u64,LiveWindow>,source:u64,p:CursorPoint)->bool{
    let Some(w)=windows.get(&source) else{return false;};
    let mut client=p;
    if unsafe{ScreenToClient(w.app.window.hwnd(),&mut client)}==0{return false;}
    let scale=w.app.window.scale_factor();
    let x=client.x as f64/scale;let y=client.y as f64/scale;
    let width=w.app.window.inner_size().width as f64/scale;
    x< -12.0||x>width+12.0||y< -12.0||y>52.0
}
fn drag_matches(drag:&Option<NativeTabDrag>,source:u64,tab:u64)->bool{
    drag.as_ref().map(|d|d.source==source&&d.tab==tab).unwrap_or(false)
}
fn finish_native_drag(windows:&std::collections::BTreeMap<u64,LiveWindow>,drag:&mut Option<NativeTabDrag>){
    if let Some(d)=drag.take(){
        if let Some(w)=windows.get(&d.source){let _=w.app.chrome.evaluate_script("window.finishNativeTabDrag?.()");}
        // Dropping the native preview unregisters the DWM thumbnail and destroys its HWND.
    }
}''',1),
('window.set_outer_position(tao::dpi::PhysicalPosition::new(cursor.x.saturating_sub((80.0*scale) as i32),cursor.y.saturating_sub((17.0*scale) as i32)));','''let size=window.outer_size();
        let (x,y)=work_area(cursor).map(|a|bounded_window_origin(cursor,size.width.min(i32::MAX as u32) as i32,size.height.min(i32::MAX as u32) as i32,a)).unwrap_or((cursor.x.saturating_sub((80.0*scale) as i32),cursor.y.saturating_sub((17.0*scale) as i32)));
        window.set_outer_position(tao::dpi::PhysicalPosition::new(x,y));''',1),
('    let mut hovered_drop:Option<(u64,Option<u64>)>=None;\n    ev.run(move|event,target,flow|{','''    let mut hovered_drop:Option<(u64,Option<u64>)>=None;
    let mut active_drag:Option<NativeTabDrag>=None;
    let mut next_drag_tick=Instant::now();
    ev.run(move|event,target,flow|{''',1),
('        let mut preview=false;\n        let mut clear_preview=false;','''        let mut begin_drag:Option<(u64,u64)>=None;
        let mut cancel_drag:Option<(u64,u64)>=None;''',1),
('                                        "drag_hover"=>{if app.tabs.iter().any(|t|t.id==c.id){preview=true;}},\n                                        "drag_cancel"=>clear_preview=true,\n                                        "detach_tab"=>{clear_preview=true;detach=Some((id,c.id,c.value=="outside"));},','''                                        "drag_hover"=>{
                                            if active_drag.is_none()&&mouse_held(){
                                                if let Some(i)=app.tabs.iter().position(|t|t.id==c.id){
                                                    // Make the live source visible before DWM starts mirroring.
                                                    app.active=i;app.panel=false;app.show();app.save();begin_drag=Some((id,c.id));
                                                }
                                            }
                                        },
                                        "drag_cancel"=>cancel_drag=Some((id,c.id)),
                                        "detach_tab"=>{
                                            // Ignore late or duplicate release IPC after native release handling.
                                            if drag_matches(&active_drag,id,c.id){detach=Some((id,c.id,c.value=="outside"));}
                                        },''',1),
('        if clear_preview||close.is_some(){set_drop_preview(&windows,&mut hovered_drop,None);}\n        else if preview{let hit=drop_target(&windows);set_drop_preview(&windows,&mut hovered_drop,hit);}','''        if let Some((source,tab))=begin_drag{
            if active_drag.is_none(){active_drag=Some(NativeTabDrag{source,tab,started:Instant::now(),preview:None,attempted:false});next_drag_tick=Instant::now();}
        }
        let invalid_drag=active_drag.as_ref().map(|d|!windows.get(&d.source).map(|w|w.app.tabs.iter().any(|t|t.id==d.tab)).unwrap_or(false)).unwrap_or(false);
        let cancelled=close.is_some()||invalid_drag||cancel_drag.map(|(source,tab)|drag_matches(&active_drag,source,tab)).unwrap_or(false)||active_drag.as_ref().map(|d|d.started.elapsed()>Duration::from_secs(120)).unwrap_or(false)||active_drag.is_some()&&escape_held();
        if cancelled{
            detach=None;
            finish_native_drag(&windows,&mut active_drag);set_drop_preview(&windows,&mut hovered_drop,None);
        }else if active_drag.is_some(){
            let now=Instant::now();
            if now>=next_drag_tick||detach.is_some(){
                next_drag_tick=now+Duration::from_millis(16);
                if let Some(p)=cursor_point(){
                    let d=active_drag.as_mut().unwrap();
                    // Reposition before hit-testing so the preview never covers the pointer.
                    if let Some(v)=d.preview.as_mut(){v.position(p);}
                    let hit=drop_target(&windows);
                    let outside=outside_source_strip(&windows,d.source,p);
                    if detach.is_some()||!mouse_held(){
                        detach=Some((d.source,d.tab,outside));
                    }else{
                        if hit.is_none()&&outside&&!d.attempted{
                            d.attempted=true;
                            d.preview=windows.get(&d.source).and_then(|w|NativeDragPreview::create(w.app.window.hwnd(),p));
                        }
                        if let Some(v)=d.preview.as_mut(){v.position(p);v.visible(hit.is_none()&&outside);}
                        set_drop_preview(&windows,&mut hovered_drop,hit);
                    }
                }else{detach=None;finish_native_drag(&windows,&mut active_drag);set_drop_preview(&windows,&mut hovered_drop,None);}
            }
        }
        if detach.is_some(){
            finish_native_drag(&windows,&mut active_drag);set_drop_preview(&windows,&mut hovered_drop,None);
        }''',1),
('if now>=next_memory{\n            for w in windows.values_mut(){let app=&mut w.app;if app.saved.memory_saver{app.layout();if app.saved.auto_release{app.release_background(true);}app.sync();}}','''if now>=next_memory{
            // Never unload the controller while a drag is in progress.
            if active_drag.is_none(){for w in windows.values_mut(){let app=&mut w.app;if app.saved.memory_saver{app.layout();if app.saved.auto_release{app.release_background(true);}app.sync();}}}''',1),
('        if let Some(d)=dirty_due{due=due.min(d);}\n        *flow=ControlFlow::WaitUntil(due);','''        if let Some(d)=dirty_due{due=due.min(d);}
        if active_drag.is_some(){due=due.min(next_drag_tick);}
        *flow=ControlFlow::WaitUntil(due);''',1),
('mod tests {','''mod tests {
    #[test] fn preview_avoids_pointer_and_negative_monitor_edges(){
        use super::{NativeRect,CursorPoint,preview_origin,bounded_window_origin};
        let area=NativeRect{left:-1920,top:0,right:0,bottom:1040};
        let p=CursorPoint{x:-10,y:1030};
        let (x,y)=preview_origin(p,640,400,area);
        assert!(x+640<p.x&&y+400<p.y);
        assert_eq!(bounded_window_origin(p,800,500,area),(-800,540));
        let p=CursorPoint{x:-1915,y:5};
        let (x,y)=preview_origin(p,640,400,area);assert!(x>p.x&&y>p.y);
    }
''',1)
])
# Guard the transfer against capacity before detaching and preserve the
# original live controller when native reparent reports failure.
edit('project/src/ui.html',[
('body{--tab-idle:#202020;--tab-active:#383838;--tab-idle-text:#dedede;--tab-border:#565656;--drop-ink:#fafafa;--drop-bg:#1b1b1b}','body{--frame:#000000;--toolbar:#101010;--field:#050505;--panel:#050505;--text:#fafafa;--muted:#c4c4c4;--hover:#292929;--line:#333333;--accent:#f5f5f5;--tab-idle:#090909;--tab-active:#202020;--tab-idle-text:#d7d7d7;--tab-border:#484848;--drop-ink:#fafafa;--drop-bg:#101010}',1),
('body.tab-drop-target #dragArea{background:var(--hover);border-radius:8px 8px 0 0}','''body.tab-drop-target #dragArea{background:var(--hover);border-radius:8px 8px 0 0}
body.tab-drop-target .strip{box-shadow:inset 0 -2px 0 var(--accent)}
#tabDropMarker{width:4px}
#tabDropHint{font-size:12px;padding:6px 10px;font-weight:700}
.tab.active .name{color:var(--text)}.tab .close{opacity:.9}.tab.active .close{opacity:1}
#tabs .tab.is-dragging{opacity:.62}
#tabs .tab.detach-ready{opacity:.9;outline:2px solid var(--accent);outline-offset:-2px}
body:not(.light) .settings-head .emblem{background:#000}
body:not(.light) .toolbar input::placeholder{color:#b3b3b3}
@media(prefers-reduced-motion:reduce){*{scroll-behavior:auto!important}}''',1),
('    const d=$(\'dragArea\').getBoundingClientRect();\n    const zones=[];\n    if(r.width>0&&r.height>0)zones.push({left:r.left,right:r.right,top:r.top,bottom:r.bottom,append:false});\n    if(d.width>0&&d.height>0)zones.push({left:d.left,right:d.right,top:d.top,bottom:d.bottom,append:true});','''    const strip=tabStrip.closest('.strip').getBoundingClientRect();
    const controls=$('windowControls');
    const end=controls.hidden?strip.right:controls.getBoundingClientRect().left;
    const zones=[];
    // The entire bar (except caption controls) is a target, with extra
    // vertical tolerance into the toolbar. Blank gaps/buttons append.
    const top=strip.top-10,bottom=strip.bottom+14,split=Math.min(end,Math.max(strip.left,r.right));
    if(split>strip.left)zones.push({left:strip.left,right:split,top,bottom,append:false});
    if(end>split)zones.push({left:split,right:end,top,bottom,append:true});''',1),
("tabStrip.addEventListener('scroll',geometryChanged,{passive:true});",'''tabStrip.addEventListener('scroll',geometryChanged,{passive:true});
if(typeof ResizeObserver==='function'){
    const resizeObserver=new ResizeObserver(geometryChanged);
    resizeObserver.observe(tabStrip);resizeObserver.observe(tabStrip.closest('.strip'));
}''',1),
('    const now=performance.now();if(now-d.lastProbe>=50){d.lastProbe=now;send(\'drag_hover\',\'\',d.id);}','''    // The native loop tracks the pointer once the gesture is recognized;
    // sending one start message prevents late hover IPC from restarting it.
    if(d.lastProbe===-1000){d.lastProbe=performance.now();send('drag_hover','',d.id);}''',1),
("function cancelTabGesture(e){","""window.finishNativeTabDrag=()=>{
    if(!tabDrag)return;
    suppressTabClick=tabDrag.moved;cleanupTabDrag();if(state.tabs)window.renderState(state);
};
function cancelTabGesture(e){""",1)
])
edit('test_ui.py',[
("=='rgb(12, 12, 12)'","=='rgb(0, 0, 0)'",1),
("=='rgb(56, 56, 56)'","=='rgb(32, 32, 32)'",1),
("    assert g['zones'] and g['tabs']","""    assert g['zones'] and g['tabs']
    assert max(z['bottom'] for z in g['zones']) >= 54
    assert min(z['top'] for z in g['zones']) <= 0
    assert g['zones'][-1]['append']
    assert g['zones'][-1]['right'] <= page.locator('#windowControls').bounding_box()['x']+1""",1),
("    page.locator('#address').fill('test query')",'''    # Escape cancellation and native cleanup leave no stuck capture/marker.
    page.evaluate('messages.length=0;telemetry.length=0')
    t=page.locator('#tabs .select').first
    b=t.bounding_box();x=b['x']+b['width']/2;y=b['y']+b['height']/2
    page.mouse.move(x,y);page.mouse.down();page.mouse.move(x,y+70,steps=8)
    page.mouse.move(x+30,y+78,steps=4)
    assert page.evaluate("telemetry.filter(m=>m.action==='drag_hover').length")==1
    page.keyboard.press('Escape');page.mouse.up()
    assert page.evaluate("telemetry.some(m=>m.action==='drag_cancel')")
    assert page.evaluate('messages.length')==0
    assert page.locator('#tabs .is-dragging').count()==0
    page.mouse.move(x,y);page.mouse.down();page.mouse.move(x,y+65,steps=6)
    page.evaluate('window.finishNativeTabDrag()');page.mouse.up()
    assert page.locator('#tabs .is-dragging').count()==0
    assert page.evaluate('messages.length')==0
    page.locator('#address').fill('test query')''',1)
])
