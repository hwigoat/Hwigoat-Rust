"""1.0.6: independent native windows, one shared profile and one session writer."""
from pathlib import Path
import sys
root=Path(sys.argv[1])
def edit(name,replacements):
    p=root/name
    s=p.read_text(encoding='utf-8')
    for old,new,count in replacements:
        if s.count(old)!=count: raise RuntimeError(f'{name}: expected {count} of {old[:100]!r}, got {s.count(old)}')
        s=s.replace(old,new)
    p.write_text(s,encoding='utf-8')
for name in ('project/Cargo.toml','project/src/ui.html','test_ui.py','setup.go','make_brand.py'):
    p=root/name
    s=p.read_text(encoding='utf-8')
    assert '1.0.5' in s,name
    p.write_text(s.replace('1.0.5','1.0.6'),encoding='utf-8')
edit('make_brand.py',[('0x50000','0x60000',2)])
edit('project/src/main.rs',[
('event_loop::{ControlFlow,EventLoopBuilder,EventLoopProxy}', 'event_loop::{ControlFlow,EventLoopBuilder,EventLoopProxy,EventLoopWindowTarget}',1),
('struct Saved {tabs:Vec<Entry>,','struct Saved {windows:Vec<WindowSession>,tabs:Vec<Entry>,',1),
('Self{tabs:vec![],active:0,bookmarks:', 'Self{windows:vec![],tabs:vec![],active:0,bookmarks:',1),
('#[derive(Deserialize)] struct Command', '''#[derive(Clone,Serialize,Deserialize)] struct WindowSession{tabs:Vec<Entry>,active:usize}
#[derive(Deserialize)] struct Command''',1),
('UiLoaded(String)}','UiLoaded(String),Routed(u64,Box<Msg>),OpenWindow}',1),
('struct Tab {','''#[derive(Clone)] struct ScopedProxy{inner:EventLoopProxy<Msg>,id:u64}
impl ScopedProxy{
    fn send_event(&self,msg:Msg)->Result<(),()>{
        let routed=if self.id==0{msg}else{Msg::Routed(self.id,Box::new(msg))};
        self.inner.send_event(routed).map_err(|_|())
    }
}
struct Tab {''',1),
('proxy:EventLoopProxy<Msg>,notice:String','proxy:ScopedProxy,notice:String',1),
('fn run()->Result<(),Box<dyn std::error::Error>> {','''fn run()->Result<(),Box<dyn std::error::Error>>{
    if std::env::var_os("HWIGOAT_SMOKE_FILE").is_some(){run_single()}else{run_multi()}
}
fn run_single()->Result<(),Box<dyn std::error::Error>> {''',1),
('let proxy=ev.create_proxy();','let proxy=ScopedProxy{inner:ev.create_proxy(),id:0};',1),
('mod tests {','''mod tests {
    #[test] fn multi_session_legacy_and_roundtrip(){
        let mut saved:Saved=serde_json::from_str(r#"{"tabs":[{"url":"https://example.com/","title":"old"}],"active":0}"#).unwrap();
        assert!(saved.windows.is_empty());
        saved.windows=vec![super::WindowSession{tabs:saved.tabs.clone(),active:0},super::WindowSession{tabs:vec![Entry{url:"https://example.org/".into(),title:"other".into()}],active:0}];
        let out:Saved=serde_json::from_slice(&serde_json::to_vec(&saved).unwrap()).unwrap();
        assert_eq!(out.windows.len(),2);assert_eq!(out.windows[1].tabs[0].url,"https://example.org/");
    }
''',1)
])
p=root/'project/src/main.rs'
s=p.read_text(encoding='utf-8')
# Reuse the established, origin-checked UI builder rather than creating a new IPC path.
a=s.index('    let p=proxy.clone(); let load_proxy=proxy.clone();',s.index('fn run_single'))
b=s.index('    // A model exists before',a)
builder=s[a:b]
builder=builder.replace('.build(&ev)?;','.build(target)?;',1)
builder=builder.replace('    let chrome=WebViewBuilder::new_with_web_context(&mut shared_ctx)\n        .with_profile_name','    let builder=WebViewBuilder::new_with_web_context(&mut shared_ctx);\n    let builder=if let Some(v)=template{builder.with_environment(v.environment())}else{builder};\n    let chrome=builder\n        .with_profile_name',1)
assert 'let builder=if let Some(v)=template' in builder
builder=builder.replace('    let entries=saved.tabs.clone();let selected=saved.active;\n    let (save_tx,save_thread)=if smoke.is_none(){let (tx,worker)=start_writer(path);(Some(tx),Some(worker))}else{(None,None)};','    let entries=session.tabs;let selected=session.active;\n    let save_tx=Some(tx);let save_thread=None;',1)
assert 'let entries=session.tabs' in builder
extra=r'''
const WINDOW_LIMIT:usize=12;
struct LiveWindow{app:App,ready:bool,started:bool,created:Instant}
#[link(name="kernel32")] extern "system"{
    fn CreateEventW(attributes:*mut std::ffi::c_void,manual_reset:i32,initial_state:i32,name:*const u16)->isize;
    fn SetEvent(handle:isize)->i32;
    fn WaitForSingleObject(handle:isize,milliseconds:u32)->u32;
}
fn open_window_signal(base:&Path)->Result<InstanceGuard,Box<dyn std::error::Error>>{
    use std::hash::{Hash,Hasher};
    let mut hasher=std::collections::hash_map::DefaultHasher::new();
    base.to_string_lossy().to_lowercase().hash(&mut hasher);
    let name:Vec<u16>=format!("Local\\HwigoatRustNewWindow-{:016x}",hasher.finish()).encode_utf16().chain(Some(0)).collect();
    let h=unsafe{CreateEventW(std::ptr::null_mut(),0,0,name.as_ptr())};
    if h==0{Err(std::io::Error::last_os_error().into())}else{Ok(InstanceGuard(h))}
}
fn build_window(target:&EventLoopWindowTarget<Msg>,proxy:ScopedProxy,base:&Path,saved:Saved,session:WindowSession,tx:mpsc::Sender<Saved>,template:Option<&WebView>)->Result<LiveWindow,Box<dyn std::error::Error>>{
'''
extra+=builder
extra+=r'''
    if app.tabs.is_empty(){app.add(Entry{url:HOME.into(),title:"New tab".into()},false);}
    Ok(LiveWindow{app,ready:false,started:false,created:Instant::now()})
}
fn window_session(app:&App)->WindowSession{
    let tabs:Vec<Entry>=app.tabs.iter().filter(|t|!t.private).map(|t|t.entry.clone()).collect();
    let active=app.tabs.iter().take(app.active).filter(|t|!t.private).count().min(tabs.len().saturating_sub(1));
    WindowSession{tabs,active}
}
fn snapshot_windows(global:&Saved,windows:&std::collections::BTreeMap<u64,LiveWindow>)->Saved{
    let mut out=global.clone();
    out.windows=windows.values().map(|w|window_session(&w.app)).filter(|s|!s.tabs.is_empty()).collect();
    out.tabs=out.windows.first().map(|w|w.tabs.clone()).unwrap_or_default();
    out.active=out.windows.first().map(|w|w.active).unwrap_or(0);
    out
}
fn run_multi()->Result<(),Box<dyn std::error::Error>>{
    use std::collections::BTreeMap;
    let base=PathBuf::from(std::env::var("LOCALAPPDATA")?).join("HwigoatRust");
    fs::create_dir_all(&base)?;
    // Create the auto-reset event before acquiring the mutex to avoid a startup race.
    let signal=open_window_signal(&base)?;
    let launch_mark=std::env::var_os("HWIGOAT_LAUNCH_MARK").filter(|s|!s.is_empty()).map(PathBuf::from);
    let instance=match lock_instance(&base){
        Ok(g)=>g,
        Err(e) if e.to_string()=="Hwigoat Rust is already open for this profile"&&launch_mark.is_none()=>{
            if unsafe{SetEvent(signal.0)}==0{return Err(std::io::Error::last_os_error().into());}
            return Ok(());
        }
        Err(e)=>return Err(e),
    };
    let path=base.join("session.json");
    let mut global:Saved=match fs::read(&path){
        Ok(b)=>match serde_json::from_slice(&b){Ok(s)=>s,Err(e)=>{let backup=path.with_extension("invalid.json");if backup.exists(){return Err(format!("Session unreadable: {e}; existing backup must be preserved").into());}fs::copy(&path,backup)?;Saved::default()}},
        Err(e) if e.kind()==std::io::ErrorKind::NotFound=>Saved::default(),
        Err(e)=>return Err(e.into())
    };
    let mut sessions=std::mem::take(&mut global.windows);
    if sessions.is_empty(){sessions.push(WindowSession{tabs:std::mem::take(&mut global.tabs),active:global.active});}
    global.tabs.clear();global.active=0;
    set_app_identity();
    let ev=EventLoopBuilder::<Msg>::with_user_event().build();
    let raw_proxy=ev.create_proxy();
    let (tx,worker)=start_writer(path);
    let mut writer=Some((tx,worker));
    let mut windows:BTreeMap<u64,LiveWindow>=BTreeMap::new();
    let mut next_id=1u64;
    for session in sessions.into_iter().take(WINDOW_LIMIT){
        let template=windows.values().next().map(|w|&w.app.chrome);
        let w=build_window(&ev,ScopedProxy{inner:raw_proxy.clone(),id:next_id},&base,global.clone(),session,writer.as_ref().unwrap().0.clone(),template)?;
        windows.insert(next_id,w);next_id+=1;
    }
    // A second desktop/start-menu launch asks the existing process for another
    // native window instead of opening a second session writer.
    let listener=raw_proxy.clone();
    thread::spawn(move||{
        let handle=signal;
        loop{
            if unsafe{WaitForSingleObject(handle.0,0xffffffff)}!=0{break;}
            if listener.send_event(Msg::OpenWindow).is_err(){break;}
        }
    });
    let mut next_update=Instant::now();
    let mut next_status=Instant::now();
    let mut next_memory=Instant::now()+Duration::from_secs(30);
    let mut dirty_due:Option<Instant>=None;
    let mut launch_reported=false;
    ev.run(move|event,target,flow|{
        let _keep=&instance;
        let mut close:Option<(u64,bool)>=None;
        let mut new_window=false;
        let mut changed=false;
        let mut settings_changed=false;
        match event{
            Event::WindowEvent{window_id,event:WindowEvent::CloseRequested,..}=>{
                close=windows.iter().find(|(_,w)|w.app.window.id()==window_id).map(|(id,_)|(*id,false));
            }
            Event::WindowEvent{window_id,event:WindowEvent::Resized(_)|WindowEvent::ScaleFactorChanged{..},..}=>{
                if let Some(w)=windows.values_mut().find(|w|w.app.window.id()==window_id){w.app.layout();w.app.sync();}
            }
            Event::UserEvent(Msg::OpenWindow)=>{new_window=true;}
            Event::UserEvent(Msg::Routed(id,msg))=>{
                if let Some(w)=windows.get_mut(&id){
                    let app=&mut w.app;
                    match *msg{
                        Msg::UiLoaded(_)=>{app.invalidate_ui();app.sync();}
                        Msg::Command(s)=>{
                            if let Ok(c)=serde_json::from_str::<Command>(&s){
                                if c.action=="ready"{
                                    w.ready=true;let _=app.chrome.evaluate_script("window.__hwigoatReadyAck=true");
                                    app.invalidate_ui();if !w.started{w.started=true;app.show();}else{app.sync();}
                                }else if w.started{
                                    match c.action.as_str(){
                                        "new_window"=>new_window=true,
                                        "window_close"=>close=Some((id,false)),
                                        "close" if is_last_close(app.tabs.len(),app.tabs.first().map(|t|t.id),c.id)=>close=Some((id,true)),
                                        "window_minimize"=>app.window.set_minimized(true),
                                        "window_maximize"=>{app.window.set_maximized(!app.window.is_maximized());app.sync();}
                                        "window_drag"=>{let _=app.window.drag_window();}
                                        _=>app.command(c),
                                    }
                                }
                            }
                        }
                        Msg::Popup(tab,u)=>{if let Some(private)=app.tabs.iter().find(|t|t.id==tab).map(|t|t.private){app.add(Entry{url:u,title:"New tab".into()},private);app.show();app.save();}}
                        Msg::DownloadStart(tab)=>{if let Some(t)=app.tabs.iter_mut().find(|t|t.id==tab){t.downloads=t.downloads.saturating_add(1);}app.layout();app.sync();}
                        Msg::Download(tab,ok)=>{if let Some(t)=app.tabs.iter_mut().find(|t|t.id==tab){t.downloads=t.downloads.saturating_sub(1);app.notice=if ok{"Download completed".into()}else{"Download failed or cancelled".into()};}app.layout();app.sync();}
                        Msg::Title(tab,s)=>{if let Some(t)=app.tabs.iter_mut().find(|t|t.id==tab){if t.entry.title!=s{t.entry.title=s;if !t.private{if let Some(h)=app.saved.history.iter_mut().find(|h|h.url==t.entry.url){h.title=t.entry.title.clone();}app.save();}app.sync();}}}
                        Msg::Loaded(tab,u)=>{if allowed(&u){if let Some(t)=app.tabs.iter_mut().find(|t|t.id==tab){t.entry.url=u;if !t.private{let e=t.entry.clone();app.saved.history.retain(|x|x.url!=e.url);app.saved.history.insert(0,e);app.saved.history.truncate(500);}}app.sync();app.save();}}
                        _=>{}
                    }
                    // Every window starts from the shared settings snapshot. Only
                    // one central writer persists updates, so windows cannot race.
                    if app.save_due.take().is_some(){global=app.saved.clone();global.tabs.clear();global.windows.clear();global.active=0;settings_changed=true;changed=true;}
                }
            }
            _=>{}
        }
        if settings_changed{
            for w in windows.values_mut(){
                let frame=global.native_frame||std::env::var_os("HWIGOAT_NATIVE_FRAME").is_some();
                w.app.saved=global.clone();
                if w.app.window.is_decorated()!=frame{w.app.window.set_decorations(frame);}
                w.app.layout();w.app.sync();
            }
        }
        if let Some((id,last_tab))=close{
            if windows.len()==1{
                if last_tab{if let Some(w)=windows.get_mut(&id){w.app.tabs.clear();w.app.active=0;}}
                let snapshot=snapshot_windows(&global,&windows);
                let apply=global.auto_update&&windows.values().all(|w|w.app.tabs.iter().all(|t|t.downloads==0));
                // Preserve the final session before dropping the WebViews.
                windows.clear();
                if let Some((tx,worker))=writer.take(){let _=tx.send(snapshot);drop(tx);let _=worker.join();}
                if apply{let _=update_agent("--apply");}
                *flow=ControlFlow::Exit;return;
            }
            windows.remove(&id);changed=true;
        }
        if new_window{
            if windows.len()<WINDOW_LIMIT{
                let template=windows.values().next().map(|w|&w.app.chrome);
                let session=WindowSession{tabs:vec![],active:0};
                match build_window(target,ScopedProxy{inner:raw_proxy.clone(),id:next_id},&base,global.clone(),session,writer.as_ref().unwrap().0.clone(),template){
                    Ok(w)=>{windows.insert(next_id,w);next_id+=1;changed=true;}
                    Err(e)=>{show_error(&format!("Could not open another window: {e}"));}
                }
            }else{show_error("Window limit reached (12). Close another window first.");}
        }
        let now=Instant::now();
        for w in windows.values_mut(){
            if !w.started&&w.created.elapsed()>=Duration::from_secs(3){w.started=true;w.app.show();}
        }
        if !launch_reported&&windows.values().any(|w|w.ready&&w.started&&w.app.tabs.get(w.app.active).and_then(|t|t.view.as_ref()).is_some()){
            if let Some(ref mark)=launch_mark{launch_reported=fs::write(mark,concat!("version=",env!("CARGO_PKG_VERSION"),"\nnormal profile UI IPC and content controller ready\n")).is_ok();}
        }
        if changed&&dirty_due.is_none(){dirty_due=Some(now+Duration::from_millis(350));}
        if dirty_due.map(|d|now>=d).unwrap_or(false){
            if let Some((tx,_))=&writer{let _=tx.send(snapshot_windows(&global,&windows));}
            dirty_due=None;
        }
        if global.auto_update{
            if now>=next_update{let _=update_agent("--check");next_update=now+Duration::from_secs(1800);}
        }else{next_update=now;}
        if now>=next_status{
            for w in windows.values(){if w.app.panel{w.app.sync();}}
            next_status=now+Duration::from_secs(2);
        }
        if now>=next_memory{
            for w in windows.values_mut(){let app=&mut w.app;if app.saved.memory_saver{app.layout();if app.saved.auto_release{app.release_background(true);}app.sync();}}
            next_memory=now+Duration::from_secs(30);
        }
        // Wait on the earliest timer; idle windows do not need a busy loop.
        let mut due=next_memory;
        if global.auto_update{due=due.min(next_update);}
        if windows.values().any(|w|w.app.panel){due=due.min(next_status);}
        for w in windows.values(){if !w.started{due=due.min(w.created+Duration::from_secs(3));}}
        if let Some(d)=dirty_due{due=due.min(d);}
        *flow=ControlFlow::WaitUntil(due);
    });
}
'''
# On last-tab close, active downloads must be considered before clearing tabs.
extra=extra.replace('                if last_tab{if let Some(w)=windows.get_mut(&id){w.app.tabs.clear();w.app.active=0;}}\n                let snapshot=snapshot_windows(&global,&windows);\n                let apply=global.auto_update&&windows.values().all(|w|w.app.tabs.iter().all(|t|t.downloads==0));','                let apply=global.auto_update&&windows.values().all(|w|w.app.tabs.iter().all(|t|t.downloads==0));\n                if last_tab{if let Some(w)=windows.get_mut(&id){w.app.tabs.clear();w.app.active=0;}}\n                let snapshot=snapshot_windows(&global,&windows);')
s=s.replace('#[cfg(test)]\nmod tests {',extra+'\n#[cfg(test)]\nmod tests {',1)
p.write_text(s,encoding='utf-8')
edit('project/src/ui.html',[
('const paths={feedback:', '''const paths={newwindow:'<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 8h18M12 11v7m-3.5-3.5h7"/>',feedback:''',1),
('<button class="icon" id="privateButton"', '<button class="icon" id="newWindowButton" title="새 창 (Ctrl+N)" aria-label="새 창" data-a="new_window" data-icon="newwindow"></button><button class="icon" id="privateButton"',1),
("if(e.ctrlKey&&e.shiftKey&&e.key.toLowerCase()==='n')",'''if(e.ctrlKey&&!e.shiftKey&&!e.altKey&&e.key.toLowerCase()==='n'){e.preventDefault();send('new_window');return;}
if(e.ctrlKey&&e.shiftKey&&e.key.toLowerCase()==='n')''',1)
])
edit('test_ui.py',[
("    page.locator('#address').fill('test query')",'''    # New-window command must not open another tab in the same window.
    assert page.locator('#newWindowButton').is_visible()
    page.locator('#newWindowButton').click()
    assert page.evaluate('messages.at(-1).action')=='new_window'
    page.keyboard.press('Control+n')
    assert page.evaluate('messages.at(-1).action')=='new_window'
    page.keyboard.press('Control+Shift+n')
    assert page.evaluate('messages.at(-1).action')=='private'
    page.locator('#address').fill('test query')''',1)
])
