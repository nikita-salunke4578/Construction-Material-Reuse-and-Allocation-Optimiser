import os, json, base64, hmac, hashlib
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from .database import get_db
from .models import User

SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me-please-32-chars").encode()
bearer = HTTPBearer(auto_error=False)
def _b64(data): return base64.urlsafe_b64encode(data).rstrip(b"=").decode()
def _unb64(data): return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))
def hash_password(password):
    salt=os.urandom(16); digest=hashlib.pbkdf2_hmac("sha256",password.encode(),salt,240000)
    return "pbkdf2_sha256$240000$"+_b64(salt)+"$"+_b64(digest)
def verify_password(password, hashed):
    try:
        scheme,rounds,salt,digest=hashed.split("$")
        if scheme!="pbkdf2_sha256": return False
        actual=hashlib.pbkdf2_hmac("sha256",password.encode(),_unb64(salt),int(rounds))
        return hmac.compare_digest(actual,_unb64(digest))
    except Exception: return False
def create_token(user):
    header=_b64(json.dumps({"alg":"HS256","typ":"JWT"},separators=(",",":")).encode())
    payload=_b64(json.dumps({"sub":str(user.id),"role":user.role,"exp":int((datetime.now(timezone.utc)+timedelta(minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES","720")))).timestamp())},separators=(",",":")).encode())
    msg=f"{header}.{payload}".encode(); sig=_b64(hmac.new(SECRET_KEY,msg,hashlib.sha256).digest())
    return f"{header}.{payload}.{sig}"
def _decode(token):
    try:
        h,p,s=token.split("."); expected=_b64(hmac.new(SECRET_KEY,f"{h}.{p}".encode(),hashlib.sha256).digest())
        if not hmac.compare_digest(s,expected): raise ValueError()
        data=json.loads(_unb64(p))
        if int(data["exp"])<int(datetime.now(timezone.utc).timestamp()): raise ValueError()
        return data
    except Exception: raise HTTPException(401,"Invalid or expired token")
def current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer), db: Session = Depends(get_db)):
    if not credentials: raise HTTPException(401,"Authentication required")
    try: uid=int(_decode(credentials.credentials)["sub"])
    except (ValueError,KeyError): raise HTTPException(401,"Invalid or expired token")
    user=db.get(User,uid)
    if not user: raise HTTPException(401,"User no longer exists")
    return user
def roles(*allowed):
    def check(user: User = Depends(current_user)):
        if user.role not in allowed: raise HTTPException(403,"This action is not permitted for your role")
        return user
    return check
