"""Prepare 1.0.3 from the existing 1.0.2 source archive."""
from pathlib import Path
import sys, shutil
root=Path(sys.argv[1])
here=Path(__file__).resolve().parent
def edit(path, changes):
    p=root/path
    s=p.read_text(encoding="utf-8")
    for old,new,count in changes:
        assert s.count(old)==count, (path, old[:80], s.count(old))
        s=s.replace(old,new)
    p.write_text(s,encoding="utf-8")
for name in ("project/Cargo.toml","project/src/ui.html","test_ui.py","setup.go","make_brand.py"):
    p=root/name
    p.write_text(p.read_text(encoding="utf-8").replace("1.0.2","1.0.3"),encoding="utf-8")
edit("make_brand.py",[("0x20000","0x30000",2)])
edit("project/src/main.rs",[
("native_frame:bool}","native_frame:bool,auto_update:bool}",1),
("native_frame:false}}","native_frame:false,auto_update:true}}",1),
("let p=self.proxy.clone();let q=p.clone();","let p=self.proxy.clone();let auth=std::sync::Arc::new(std::sync::Mutex::new(auth_url(&t.entry.url)));let auth_nav=auth.clone();let q=p.clone();",1),
("with_navigation_handler(|u|{if std::env::var_os","with_navigation_handler(move |u|{if std::env::var_os",1),
('}else{allowed(&u)}}).with_new_window_req_handler(move |u,_|{if allowed(&u){let _=p.send_event(Msg::Popup(id,u));}NewWindowResponse::Deny})','''}else{let ok=allowed(&u)||u=="about:blank";if allowed(&u){if let Ok(mut a)=auth_nav.lock(){*a=auth_url(&u);}}ok}}).with_new_window_req_handler(move |u,_|{if std::env::var_os("HWIGOAT_SMOKE_FILE").is_some(){return NewWindowResponse::Deny;}let from_auth=auth.lock().map(|a|*a).unwrap_or(false);if auth_url(&u)||(from_auth&&(u=="about:blank"||allowed(&u))){return NewWindowResponse::Allow;}if allowed(&u){let _=p.send_event(Msg::Popup(id,u));}NewWindowResponse::Deny})''',1),
("&&t.downloads==0&&quiet_view(v)","&&t.downloads==0&&!auth_url(&t.entry.url)&&quiet_view(v)",1),
("if t.downloads>0 || t.shown","if t.downloads>0 || auth_url(&t.entry.url) || t.shown",1),
('"native_frame":self.window.is_decorated(),','"native_frame":self.window.is_decorated(),"auto_update":self.saved.auto_update,',1),
('"feedback"=>{self.notice=', '''"auto_update"=>{self.saved.auto_update=!self.saved.auto_update;if self.saved.auto_update{let _=update_agent("--check");}},
"update_check"=>{self.notice=if update_agent("--check"){"Update check started. Use Update status to refresh.".into()}else{"Updater unavailable. Install the official precompiled package.".into()};},
"update_status"=>{self.notice=update_status();},
"open_claude"=>{self.notice=if open_external("https://claude.ai/"){"Claude opened in default browser. Login sessions are not transferred.".into()}else{"Could not open external browser".into()};},
"feedback"=>{self.notice=''',1),
('fn open_feedback()->bool{','fn open_feedback()->bool{open_external(FEEDBACK)}\nfn open_external(target:&str)->bool{if !allowed(target){return false;}',1),
('let url:Vec<u16>=FEEDBACK.encode_utf16()','let url:Vec<u16>=target.encode_utf16()',1),
('fn set_app_identity(){','''fn auth_url(s:&str)->bool{
    url::Url::parse(s).ok().filter(|u|u.scheme()=="https"&&u.username().is_empty()&&u.password().is_none()).and_then(|u|u.host_str().map(str::to_owned)).map(|h| matches!(h.as_str(),"claude.ai"|"www.claude.ai"|"accounts.google.com"|"login.microsoftonline.com"|"login.live.com"|"appleid.apple.com"|"auth0.com")||h.ends_with(".claude.ai")||h.ends_with(".auth0.com")).unwrap_or(false)
}
fn update_root()->Option<PathBuf>{Some(PathBuf::from(std::env::var_os("LOCALAPPDATA")?).join("HwigoatRustSetup"))}
fn update_agent(mode:&str)->bool{
    use std::os::windows::process::CommandExt;
    if std::env::var_os("HWIGOAT_SMOKE_FILE").is_some(){return false;}
    let Some(root)=update_root() else{return false;};
    let agent=root.join(concat!("update-agent-",env!("CARGO_PKG_VERSION"),".exe"));
    if !agent.is_file(){return false;}
    let mut command=std::process::Command::new(agent);
    command.arg(mode).creation_flags(0x08000000);
    if mode=="--apply"{command.arg(std::process::id().to_string());}
    command.spawn().is_ok()
}
fn update_status()->String{
    update_root().and_then(|p|fs::read_to_string(p.join("update-status.txt")).ok()).map(|s|s.chars().take(300).collect()).unwrap_or_else(||"No update status yet.".into())
}
fn set_app_identity(){''',1),
('let mut started=false;', 'if smoke.is_none()&&launch_mark.is_none()&&app.saved.auto_update{let _=update_agent("--check");}\n    let mut started=false;',1),
('app.finish_save();*flow=ControlFlow::Exit;return;', 'app.finish_save();if smoke.is_none()&&app.saved.auto_update&&app.tabs.iter().all(|t|t.downloads==0){let _=update_agent("--apply");}*flow=ControlFlow::Exit;return;',2),
("mod tests {",'''mod tests {
    #[test] fn auth_domains_are_exact(){assert!(super::auth_url("https://claude.ai/login"));assert!(super::auth_url("https://accounts.google.com/"));assert!(!super::auth_url("https://claude.ai.evil.example/"));assert!(!super::auth_url("http://claude.ai/"));assert!(!super::auth_url("https://claude.ai@evil.example/"));}
''',1)
])
edit("project/src/ui.html",[
('window.renderState=s=>{state=s;', 'window.renderState=s=>{state=s;$("updateToggle").setAttribute("aria-pressed",String(s.auto_update!==false));',1)
])
p=root/"project/src/ui.html"
s=p.read_text(encoding="utf-8")
anchor='<section class="section">'
assert anchor in s
s=s.replace(anchor,'''<section class="section"><h2>자동 업데이트 · 로그인 호환성</h2><p>공식 서명된 업데이트만 내려받고 정상 종료 후 적용합니다. 다음 실행에 새 버전을 사용합니다.</p><div class="mode-row"><button id="updateToggle" data-a="auto_update" aria-pressed="true">자동 업데이트</button><button data-a="update_check">업데이트 확인</button><button data-a="update_status">업데이트 상태</button></div><p class="subtle">Google 등에서 WebView 로그인을 제한할 경우 기본 브라우저에서 로그인하세요. 세션은 자동 이전되지 않습니다.</p><button data-a="open_claude">기본 브라우저에서 Claude 열기</button></section>'''+anchor,1)
p.write_text(s,encoding="utf-8")
edit("test_ui.py",[
("render(panel=True)\n    assert page.locator('.settings-head",'''render(panel=True)
    page.locator('[data-a=update_check]').click()
    assert page.evaluate('messages.at(-1).action')=='update_check'
    page.locator('[data-a=update_status]').click()
    assert page.evaluate('messages.at(-1).action')=='update_status'
    page.locator('#updateToggle').click()
    assert page.evaluate('messages.at(-1).action')=='auto_update'
    render(auto_update=False)
    assert page.locator('#updateToggle').get_attribute('aria-pressed')=='false'
    page.locator('[data-a=open_claude]').click()
    assert page.evaluate('messages.at(-1).action')=='open_claude'
    assert page.locator('.settings-head''',1)
])
edit("setup.go",[
("if($running.Count -eq 0){Write-Host 'No matching browser process is running.'; return}","if($running.Count -eq 0){Write-Host 'No matching browser process is running.'; return}\nif($env:HWIGOAT_AUTOMATIC -eq '1'){throw 'Browser reopened; deferred automatic update.'}",1),
("return nil\n\t})\n\tif e != nil {\n\t\treturn e\n\t}\n\tlogf(\"PATCH VERIFIED:",'''self,err:=os.Executable()
        if err!=nil{return err}
        if err=copyAtomic(self,filepath.Join(root,"update-agent-"+version+".exe"));err!=nil{return err}
        return writeInstalledVersion(root,version)
    })
    if e != nil {
        return e
    }
    logf("PATCH VERIFIED:''',1),
('logf("Starting the updated browser using the normal user profile.")','if os.Getenv("HWIGOAT_AUTOMATIC")=="1"{return nil}\n\tlogf("Starting the updated browser using the normal user profile.")',1),
('unlock, err := acquireSetupLock(root)','if handleUpdateMode(root){return}\n\tautomatic:=len(os.Args)==2&&os.Args[1]=="--automatic"\n\tif automatic{_ = os.Setenv("HWIGOAT_AUTOMATIC","1")}\n\tunlock, err := acquireSetupLock(root)',1),
("_, _ = bufio.NewReader(os.Stdin).ReadString('\\n')","if !automatic{_, _ = bufio.NewReader(os.Stdin).ReadString('\\n')}",3),
('logf("HWIGOAT RUST %s | Windows x64 precompiled in-place patch installer", version)','if automatic && !newer(version,recordedVersion(root)){logf("Automatic update no longer newer; skipped");return}\n\tlogf("HWIGOAT RUST %s | Windows x64 precompiled in-place patch installer", version)',1)
])
for name in ("update.go","update_test.go"):
    shutil.copyfile(here/name,root/name)
