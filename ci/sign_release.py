"""Sign the exact installer bytes via a small detached Ed25519 manifest."""
import base64, hashlib, json, os, re, sys
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
v=sys.argv[1]
if not re.fullmatch(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)",v):
    raise SystemExit("Invalid version")
d=Path(sys.argv[2])
p=d/f"Hwigoat_Rust_Setup_v{v}_x64.exe"
key=Ed25519PrivateKey.from_private_bytes(base64.b64decode(os.environ["UPDATE_SIGNING_KEY"],validate=True))
public=key.public_key().public_bytes(Encoding.Raw,PublicFormat.Raw)
expected=base64.b64decode(os.environ["UPDATE_PUBLIC_KEY"],validate=True)
if public!=expected:
    raise SystemExit("Public key mismatch: refusing to sign")
data=p.read_bytes()
if not 0<len(data)<=128*1024*1024:
    raise SystemExit("Invalid installer size")
manifest=json.dumps(dict(Version=v,SHA256=hashlib.sha256(data).hexdigest(),Size=len(data),File=p.name),separators=(",",":")).encode()
(d/"update.json").write_bytes(manifest)
(d/"update.sig").write_bytes(base64.b64encode(key.sign(manifest)))
print("Signed manifest created for",p.name)
