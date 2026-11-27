"""1.0.5 UX, InPrivate and update lifecycle improvements."""
from pathlib import Path
import sys
root=Path(sys.argv[1])
def edit(name, replacements):
    p=root/name
    s=p.read_text(encoding='utf-8')
    for old,new,count in replacements:
        if s.count(old)!=count: raise RuntimeError(f'{name}: expected {count} occurrences of {old[:100]!r}; got {s.count(old)}')
        s=s.replace(old,new)
    p.write_text(s,encoding='utf-8')
for name in ('project/Cargo.toml','project/src/ui.html','test_ui.py','setup.go','make_brand.py'):
    p=root/name
    s=p.read_text(encoding='utf-8')
    assert '1.0.4' in s,name
    p.write_text(s.replace('1.0.4','1.0.5'),encoding='utf-8')
edit('make_brand.py',[('0x40000','0x50000',2)])
edit('project/src/main.rs',[
('ICoreWebView2_19, ICoreWebView2_8','ICoreWebView2_19, ICoreWebView2_13, ICoreWebView2_8',1),
('let id=t.id;let p=self.proxy.clone();','let id=t.id;let private=t.private;let requested=t.entry.url.clone();let p=self.proxy.clone();',1),
('let builder=WebViewBuilder::new_with_web_context(&mut self.ctx).with_incognito(t.private);let builder=if t.private{builder}else{builder.with_environment(self.chrome.environment())};','let builder=if private{WebViewBuilder::new().with_incognito(true)}else{WebViewBuilder::new_with_web_context(&mut self.ctx).with_environment(self.chrome.environment())};',1),
('}else{builder.with_url(&t.entry.url)};','}else if private{builder.with_url("about:blank")}else{builder.with_url(&requested)};',1),
('if auth_url(&u)||(from_auth&&(u=="about:blank"||allowed(&u))){return NewWindowResponse::Allow;}','if !private&&(auth_url(&u)||(from_auth&&(u=="about:blank"||allowed(&u)))){return NewWindowResponse::Allow;}',1),
('Ok(v)=>{trace("Content WebView created");','''Ok(v)=>{
    if private {
        // Never navigate a private tab until the runtime confirms an InPrivate controller.
        if !in_private(&v){self.notice="Private mode unavailable. Update Microsoft WebView2 Runtime.".into();self.panel=true;self.layout();self.sync();return;}
        if let Err(e)=v.load_url(&requested){self.notice=format!("Private navigation failed: {e}");}
    }
    trace("Content WebView created");''',1),
('fn quiet_view(v:&WebView)->bool{','''fn in_private(v:&WebView)->bool{
    let Ok(core)=v.webview().cast::<ICoreWebView2_13>() else{return false;};
    let Ok(profile)=(unsafe{core.Profile()}) else{return false;};
    let mut enabled=Default::default();
    unsafe{profile.IsInPrivateModeEnabled(&mut enabled)}.is_ok()&&enabled.as_bool()
}
fn is_last_close(count:usize,first:Option<u64>,requested:u64)->bool{count==1&&first==Some(requested)}
fn quiet_view(v:&WebView)->bool{''',1),
('"panel":self.panel,"shortcuts":self.saved.shortcuts,','"panel":self.panel,"private_active":active.map(|t|t.private).unwrap_or(false),"update_status":if self.panel{update_status()}else{String::new()},"shortcuts":self.saved.shortcuts,',1),
('fn finish_save(&mut self){','''fn exit_clean(&mut self,last_tab:bool,updates:bool){
    let apply=updates&&self.saved.auto_update&&self.tabs.iter().all(|t|t.downloads==0);
    if last_tab{self.tabs.clear();self.active=0;}
    self.finish_save();
    if apply{let _=update_agent("--apply");}
}
fn finish_save(&mut self){''',1),
('fn command(&mut self,c:Command){self.notice.clear();match c.action.as_str(){','''fn command(&mut self,c:Command){
    // Settings is an overlay, not a navigation in the site underneath it.
    if c.action=="panel_close"||(c.action=="back"&&self.panel){
        if self.panel{self.panel=false;self.show();self.save();if let Some(v)=self.tabs.get(self.active).and_then(|t|t.view.as_ref()){let _=v.focus();}}
        return;
    }
    self.notice.clear();match c.action.as_str(){''',1),
('"panel"=>self.panel=!self.panel,','"panel"=>{self.panel=!self.panel;if self.panel{let _=self.chrome.focus();}},',1),
('if smoke.is_none()&&launch_mark.is_none()&&app.saved.auto_update{let _=update_agent("--check");}', '''let mut next_update=Instant::now();
    let mut next_update_status=Instant::now();''',1),
('app.finish_save();if smoke.is_none()&&app.saved.auto_update&&app.tabs.iter().all(|t|t.downloads==0){let _=update_agent("--apply");}*flow=ControlFlow::Exit;return;', 'app.exit_clean(false,smoke.is_none());*flow=ControlFlow::Exit;return;',2),
('"window_close"=>{app.exit_clean(false,smoke.is_none());*flow=ControlFlow::Exit;return;},','''"window_close"=>{app.exit_clean(false,smoke.is_none());*flow=ControlFlow::Exit;return;},
                            "close" if is_last_close(app.tabs.len(),app.tabs.first().map(|t|t.id),c.id)=>{app.exit_clean(true,true);*flow=ControlFlow::Exit;return;},''',1),
('let deadline=if auto{Some(app.save_due.map(|d|d.min(next_release)).unwrap_or(next_release))}else{app.save_due};','''let mut deadline=if auto{Some(app.save_due.map(|d|d.min(next_release)).unwrap_or(next_release))}else{app.save_due};
                let now=Instant::now();
                if app.saved.auto_update{
                    if now>=next_update{let _=update_agent("--check");next_update=now+Duration::from_secs(1800);}
                    deadline=Some(deadline.map(|d|d.min(next_update)).unwrap_or(next_update));
                }else{next_update=now;}
                if app.panel{
                    if now>=next_update_status{app.sync();next_update_status=now+Duration::from_secs(2);}
                    deadline=Some(deadline.map(|d|d.min(next_update_status)).unwrap_or(next_update_status));
                }else{next_update_status=now;}''',1),
('mod tests {','''mod tests {
    #[test] fn last_tab_close_policy(){assert!(super::is_last_close(1,Some(42),42));assert!(!super::is_last_close(2,Some(42),42));assert!(!super::is_last_close(1,Some(42),43));assert!(!super::is_last_close(0,None,42));}
''',1)
])
edit('project/src/ui.html',[
('</style><body>','''#privateBadge{font-size:11px;font-weight:600;white-space:nowrap;color:var(--text)}#privateBadge[hidden]{display:none}
.tab.private-tab.active{box-shadow:inset 0 2px 0 #8f84bc}
#privateButton[aria-pressed=true]{background:var(--hover);box-shadow:inset 0 0 0 1px var(--line)}
#updateState{white-space:pre-wrap;overflow-wrap:anywhere;color:var(--muted);font-size:12px;line-height:1.5}
</style><body>''',1),
('<div id="dragArea"','<button class="icon" id="privateButton" title="새 시크릿 탭 (Ctrl+Shift+N)" aria-label="새 시크릿 탭" aria-pressed="false" data-a="private" data-icon="private"></button><div id="dragArea"',1),
('<span id="siteIcon" data-icon="globe"></span>','<span id="siteIcon" data-icon="globe"></span><span id="privateBadge" hidden>시크릿</span>',1),
('<button class="primary" data-a="panel">웹페이지로 돌아가기</button>','<button class="primary" data-a="panel_close">웹페이지로 돌아가기</button>',1),
('<button data-a="private">시크릿 탭</button>','<button data-a="private">새 시크릿 탭</button>',1),
('<p id="panelNotice" role="status"></p>','''<p id="panelNotice" role="status"></p><p class="subtle">시크릿 탭은 일반 프로필과 분리된 WebView2 InPrivate 모드를 사용합니다. 방문 기록·세션 복원에 저장되지 않습니다. 다운로드한 파일은 남으며 웹사이트 및 네트워크 관리자는 활동을 볼 수 있습니다.</p>''',1),
('<button data-a="update_status">업데이트 상태</button></div>','<button data-a="update_status">업데이트 상태</button></div><p id="updateState" role="status">업데이트 확인 중</p>',1),
('공식 서명된 업데이트만 내려받고 정상 종료 후 적용합니다. 다음 실행에 새 버전을 사용합니다.','실행할 때와 실행 중 30분마다 공식 업데이트를 확인합니다. 서명된 파일만 자동 다운로드하고 정상 종료 후 적용합니다. 다음 실행에 새 버전을 사용합니다.',1),
('state=s;$("updateToggle").setAttribute("aria-pressed",String(s.auto_update!==false));','''state=s;$("updateToggle").setAttribute("aria-pressed",String(s.auto_update!==false));
$('updateState').textContent=s.update_status||'아직 업데이트 확인 기록이 없습니다.';
$('privateBadge').hidden=!s.private_active;
$('privateButton').setAttribute('aria-pressed',String(!!s.private_active));
$('siteIcon').replaceChildren(icon(s.private_active?'private':'globe'));
$('address').setAttribute('aria-label',s.private_active?'시크릿 주소창':'주소창');
$('address').placeholder=s.private_active?'시크릿 검색 또는 URL 입력':'Google 검색 또는 URL 입력';
''',1),
("div.className='tab'+(t.id===s.active?' active':'');","div.className='tab'+(t.id===s.active?' active':'')+(t.private?' private-tab':'');",1),
("if(e.key==='Escape'&&state.panel)send('panel')","if(e.key==='Escape'&&state.panel){e.preventDefault();send('panel_close');}",1),
("document.addEventListener('keydown',e=>{if(e.ctrlKey",'''document.addEventListener('keydown',e=>{
if(e.ctrlKey&&e.shiftKey&&e.key.toLowerCase()==='n'){e.preventDefault();send('private');return;}
if(state.panel&&e.altKey&&e.key==='ArrowLeft'){e.preventDefault();send('panel_close');return;}
if(state.panel&&e.key==='BrowserBack'){e.preventDefault();send('panel_close');return;}
if(e.ctrlKey''',1),
('});function announceReady(){','''});document.addEventListener('mouseup',e=>{if(state.panel&&e.button===3){e.preventDefault();send('panel_close');}});function announceReady(){''',1)
])
edit('test_ui.py',[
("    page.locator('#address').fill('test query')",'''    # Settings back and incognito controls use explicit, non-toggle commands.
    render(panel=True)
    page.locator('[data-a=back]').click()
    assert page.evaluate('messages.at(-1).action')=='back'
    page.locator('[data-a=panel_close]').click()
    assert page.evaluate('messages.at(-1).action')=='panel_close'
    page.keyboard.press('Alt+ArrowLeft')
    assert page.evaluate('messages.at(-1).action')=='panel_close'
    page.keyboard.press('Escape')
    assert page.evaluate('messages.at(-1).action')=='panel_close'
    render(panel=False)
    page.locator('#privateButton').click()
    assert page.evaluate('messages.at(-1).action')=='private'
    page.keyboard.press('Control+Shift+n')
    assert page.evaluate('messages.at(-1).action')=='private'
    regular_tabs=state['tabs']
    render(tabs=[dict(id=7,title='Private',url='https://example.org/',private=True,sleep=False,low=False)],active=7,private_active=True)
    assert page.locator('#privateBadge').is_visible()
    assert page.locator('#tabs .private-tab').count()==1
    page.locator('#tabs .close').click()
    assert page.evaluate('messages.at(-1).action')=='close' and page.evaluate('messages.at(-1).id')==7
    render(tabs=regular_tabs,active=1,private_active=False,url='https://www.naver.com/')
    assert not page.locator('#privateBadge').is_visible()
    render(panel=True,update_status='Update 1.0.6 ready')
    assert page.locator('#updateState').inner_text()=='Update 1.0.6 ready'
    render(panel=False,update_status='')
    page.locator('#address').fill('test query')''',1)
])
edit('update.go',[
('unlock,e:=acquireSetupLock(filepath.Join(root,"update-agent-lock"))\n if e!=nil{return true};defer unlock()','''unlock,e:=acquireSetupLock(filepath.Join(root,"update-agent-lock"))
 // A normal close can race with the background download. Wait for that agent
 // rather than dropping the apply request. A second check still exits promptly.
 if e!=nil&&os.Args[1]=="--apply"{
  deadline:=time.Now().Add(5*time.Minute)
  for e!=nil&&time.Now().Before(deadline){time.Sleep(500*time.Millisecond);unlock,e=acquireSetupLock(filepath.Join(root,"update-agent-lock"))}
 }
 if e!=nil{if os.Args[1]=="--apply"{updateStatus(root,"Update deferred: another update is still running.")};return true};defer unlock()''',1)
])
