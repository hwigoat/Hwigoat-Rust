package main
import("crypto/ed25519";"encoding/base64";"encoding/json";"strings";"testing")
func TestSignedManifest(t *testing.T){
 pub,priv,e:=ed25519.GenerateKey(nil);if e!=nil{t.Fatal(e)}
 m:=manifest{Version:"1.0.4",SHA256:strings.Repeat("a",64),Size:100,File:installerName("1.0.4")}
 b,_:=json.Marshal(m);s:=[]byte(base64.StdEncoding.EncodeToString(ed25519.Sign(priv,b)))
 if _,e=verifyManifest(b,s,pub,"1.0.3");e!=nil{t.Fatal(e)}
 if _,e=verifyManifest(b,s,pub,"1.0.4");e==nil{t.Fatal("accepted downgrade or duplicate")}
 altered:=append(append([]byte{},b...),byte(' '));if _,e=verifyManifest(altered,s,pub,"1.0.3");e==nil{t.Fatal("accepted tampering")}
 m.File="../other.exe";b,_=json.Marshal(m);s=[]byte(base64.StdEncoding.EncodeToString(ed25519.Sign(priv,b)))
 if _,e=verifyManifest(b,s,pub,"1.0.3");e==nil{t.Fatal("accepted unexpected file name")}
}
func TestVersionOrdering(t *testing.T){if !newer("1.0.10","1.0.3")||newer("1.0.3","1.0.10")||newer("1.00.4","1.0.3"){t.Fatal("incorrect version comparison")}}
