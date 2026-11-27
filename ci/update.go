package main

import (
 "crypto/ed25519"
 "encoding/base64"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "io"
 "net/http"
 "os"
 "os/exec"
 "path/filepath"
 "sort"
 "strconv"
 "strings"
 "time"
)

// The public key is embedded by CI. Empty or invalid key disables automatic updates.
// The private signing key is never distributed.
var updatePublicKey string
const releaseBase = "https://github.com/hwigoat/Hwigoat-Rust/releases/download/"
const releaseAPI = "https://api.github.com/repos/hwigoat/Hwigoat-Rust/releases?per_page=30"
type manifest struct { Version string; SHA256 string; Size int64; File string }
type release struct { Tag_name string; Draft bool; Assets []struct{ Name string } }
const maxUpdate = 128 << 20
var updateClient = &http.Client{Timeout: 3*time.Minute, CheckRedirect: func(r *http.Request, via []*http.Request)error{
 h:=r.URL.Hostname()
 if r.URL.Scheme!="https"||r.URL.User!=nil||len(via)>8||!(h=="github.com"||h=="api.github.com"||h=="release-assets.githubusercontent.com"||h=="objects.githubusercontent.com"){return errors.New("untrusted update redirect")}
 return nil
}}
func parseVersion(s string)([3]uint64,bool){
 var v [3]uint64
 p:=strings.Split(s,".")
 if len(p)!=3{return v,false}
 for i,x:=range p{n,e:=strconv.ParseUint(x,10,32);if e!=nil||strconv.FormatUint(n,10)!=x{return v,false};v[i]=n}
 return v,true
}
func newer(a,b string)bool{
 x,ok:=parseVersion(a);y,ok2:=parseVersion(b)
 if !ok||!ok2{return false}
 for i:=range x{if x[i]!=y[i]{return x[i]>y[i]}}
 return false
}
func trustedKey() (ed25519.PublicKey,error){
 b,e:=base64.StdEncoding.DecodeString(strings.TrimSpace(updatePublicKey))
 if e!=nil||len(b)!=ed25519.PublicKeySize{return nil,errors.New("Automatic updates disabled: official signing key not configured.")}
 return ed25519.PublicKey(b),nil
}
func installerName(v string)string{return "Hwigoat_Rust_Setup_v"+v+"_x64.exe"}
func verifyManifest(data,sig []byte,key ed25519.PublicKey,floor string)(manifest,error){
 var m manifest
 if len(data)>8192||len(key)!=ed25519.PublicKeySize{return m,errors.New("invalid manifest or key")}
 s,e:=base64.StdEncoding.DecodeString(strings.TrimSpace(string(sig)))
 if e!=nil||!ed25519.Verify(key,data,s){return m,errors.New("update signature invalid")}
 if e=json.Unmarshal(data,&m);e!=nil{return m,e}
 h,e:=hex.DecodeString(m.SHA256)
 if !newer(m.Version,floor)||m.File!=installerName(m.Version)||e!=nil||len(h)!=32||m.Size<=0||m.Size>maxUpdate{return m,errors.New("invalid or non-newer signed update")}
 return m,nil
}
func fetchUpdate(url string,limit int64)([]byte,error){
 req,e:=http.NewRequest("GET",url,nil);if e!=nil{return nil,e}
 req.Header.Set("User-Agent","Hwigoat-Rust-Update/"+version)
 r,e:=updateClient.Do(req);if e!=nil{return nil,e};defer r.Body.Close()
 if r.StatusCode!=200{return nil,fmt.Errorf("update server HTTP %d",r.StatusCode)}
 if r.ContentLength>limit{return nil,errors.New("update exceeds size limit")}
 b,e:=io.ReadAll(io.LimitReader(r.Body,limit+1));if e!=nil{return nil,e}
 if int64(len(b))>limit||(r.ContentLength>=0&&r.ContentLength!=int64(len(b))){return nil,errors.New("incomplete or oversized download")}
 return b,nil
}
func writeSmall(root,name,value string)error{
 f,e:=os.CreateTemp(root,".update-");if e!=nil{return e}
 path:=f.Name();defer os.Remove(path)
 _,e=f.WriteString(value);if e==nil{e=f.Sync()};ce:=f.Close();if e!=nil{return e};if ce!=nil{return ce}
 return moveReplace(path,filepath.Join(root,name))
}
func writeInstalledVersion(root,v string)error{return writeSmall(root,"installed-version.txt",v)}
func installedVersion(root string)string{
 b,e:=os.ReadFile(filepath.Join(root,"installed-version.txt"));if e==nil{v:=strings.TrimSpace(string(b));if _,ok:=parseVersion(v);ok&&newer(v,version){return v}}
 return version
}
func updateStatus(root,s string){_ = writeSmall(root,"update-status.txt",s)}
func pending(root string,key ed25519.PublicKey,floor string)(manifest,string,error){
 dir:=filepath.Join(root,"pending-update")
 data,e:=os.ReadFile(filepath.Join(dir,"update.json"));if e!=nil{return manifest{},"",e}
 sig,e:=os.ReadFile(filepath.Join(dir,"update.sig"));if e!=nil{return manifest{},"",e}
 m,e:=verifyManifest(data,sig,key,floor);if e!=nil{return m,"",e}
 path:=filepath.Join(dir,m.File)
 st,e:=os.Stat(path);if e!=nil{return m,"",e};if st.Size()!=m.Size{return m,"",errors.New("update size mismatch")}
 if e=verifyHash(path,m.SHA256);e!=nil{return m,"",e}
 return m,path,nil
}
func checkUpdate(root string,key ed25519.PublicKey)error{
 floor:=installedVersion(root)
 if m,_,e:=pending(root,key,floor);e==nil{updateStatus(root,"Update "+m.Version+" ready. Close the browser normally to apply.");return nil}
 updateStatus(root,"Checking official GitHub releases...")
 raw,e:=fetchUpdate(releaseAPI,2<<20);if e!=nil{return e}
 var releases []release;if e=json.Unmarshal(raw,&releases);e!=nil{return e}
 sort.SliceStable(releases,func(i,j int)bool{return newer(strings.TrimPrefix(releases[i].Tag_name,"v"),strings.TrimPrefix(releases[j].Tag_name,"v"))})
 for _,r:=range releases{
  v:=strings.TrimPrefix(r.Tag_name,"v")
  if r.Draft||r.Tag_name!="v"+v||!newer(v,floor){continue}
  files:=map[string]bool{};for _,a:=range r.Assets{files[a.Name]=true}
  if !files["update.json"]||!files["update.sig"]||!files[installerName(v)]{continue}
  prefix:=releaseBase+r.Tag_name+"/"
  data,e:=fetchUpdate(prefix+"update.json",8192);if e!=nil{return e}
  sig,e:=fetchUpdate(prefix+"update.sig",1024);if e!=nil{return e}
  m,e:=verifyManifest(data,sig,key,floor);if e!=nil{return e};if m.Version!=v{return errors.New("release tag mismatch")}
  updateStatus(root,"Downloading verified release "+v+"...")
  bin,e:=fetchUpdate(prefix+m.File,m.Size);if e!=nil{return e}
  if int64(len(bin))!=m.Size{return errors.New("update size mismatch")}
  stage,e:=os.MkdirTemp(root,".pending-");if e!=nil{return e};defer os.RemoveAll(stage)
  path:=filepath.Join(stage,m.File)
  if e=os.WriteFile(path,bin,0700);e!=nil{return e}
  if e=verifyHash(path,m.SHA256);e!=nil{return e}
  if e=os.WriteFile(filepath.Join(stage,"update.json"),data,0600);e!=nil{return e}
  if e=os.WriteFile(filepath.Join(stage,"update.sig"),sig,0600);e!=nil{return e}
  dir:=filepath.Join(root,"pending-update")
  if e=os.RemoveAll(dir);e!=nil{return e}
  if e=os.Rename(stage,dir);e!=nil{return e}
  updateStatus(root,"Update "+v+" ready. Close the browser normally to apply.")
  return nil
 }
 updateStatus(root,"No newer signed release found.");return nil
}
func applyUpdate(root string,key ed25519.PublicKey,pid string)error{
 n,e:=strconv.ParseUint(pid,10,32);if e!=nil||n==0{return errors.New("invalid browser process ID")}
 // Wait without terminating any process. The installer also checks for a reopened browser.
 c:=exec.Command("powershell.exe","-NoProfile","-NonInteractive","-Command",fmt.Sprintf("if(Get-Process -Id %d -ErrorAction SilentlyContinue){Wait-Process -Id %d -Timeout 25 -ErrorAction Stop}",n,n))
 if e=c.Run();e!=nil{return errors.New("browser not closed; update deferred")}
 m,path,e:=pending(root,key,installedVersion(root));if os.IsNotExist(e){return nil};if e!=nil{return e}
 updateStatus(root,"Installing signed update "+m.Version+"...")
 c=exec.Command(path,"--automatic")
 c.Dir=root
 c.Env=envWith(os.Environ(),"HWIGOAT_AUTOMATIC=1")
 if e=c.Run();e!=nil{return fmt.Errorf("update failed; previous browser retained if rollback succeeded: %w",e)}
 // The signed installer must have recorded the new version.
 b,e:=os.ReadFile(filepath.Join(root,"installed-version.txt"));if e!=nil||strings.TrimSpace(string(b))!=m.Version{return errors.New("update not confirmed; see install.log")}
 updateStatus(root,"Installed "+m.Version+". Start Hwigoat Rust again.")
 return os.RemoveAll(filepath.Join(root,"pending-update"))
}
func handleUpdateMode(root string)bool{
 if len(os.Args)<2||(os.Args[1]!="--check"&&os.Args[1]!="--apply"){return false}
 key,e:=trustedKey();if e!=nil{updateStatus(root,e.Error());return true}
 unlock,e:=acquireSetupLock(filepath.Join(root,"update-agent-lock"))
 if e!=nil{return true};defer unlock()
 if os.Args[1]=="--check"{e=checkUpdate(root,key)}else if len(os.Args)==3{e=applyUpdate(root,key,os.Args[2])}else{e=errors.New("missing process ID")}
 if e!=nil{updateStatus(root,"Update deferred: "+e.Error())}
 return true
}
