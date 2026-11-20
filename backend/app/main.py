from datetime import datetime
from pathlib import Path
import csv, io, re, os, json, urllib.request
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, update
from .database import Base, engine, get_db
from .models import User, Material, Demand, Allocation, AuditLog
from .schemas import LoginIn, RegisterIn, MaterialIn, DemandIn, OptimiseIn, StatusIn
from .security import hash_password, verify_password, create_token, current_user, roles
from .optimizer import optimise
from .safety import assess_material
from .seed import seed

Base.metadata.create_all(bind=engine)
app=FastAPI(title="Construction Material Reuse & Allocation Optimiser",version="1.0.0")
app.add_middleware(CORSMiddleware,allow_origins=["http://localhost:5173","http://127.0.0.1:5173"],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])
Path("uploads").mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
@app.on_event("startup")
def startup():
    db=next(get_db())
    try: seed(db)
    finally: db.close()

def user_dict(u): return {"id":u.id,"name":u.name,"email":u.email,"role":u.role,"organisation":u.organisation}
def material_dict(m):
    return {"id":m.id,"supplier_id":m.supplier_id,"supplier":m.supplier.name,"title":m.title,"material_type":m.material_type,"description":m.description,"quantity":m.quantity,"reserved_quantity":m.reserved_quantity,"available_quantity":m.available_quantity,"unit":m.unit,"quality":m.quality,"condition":m.condition,"building_year":m.building_year,"contamination":m.contamination,"painted":m.painted,"treated":m.treated,"lab_verified":m.lab_verified,"lat":m.lat,"lng":m.lng,"location":m.location,"price_per_unit":m.price_per_unit,"image_url":m.image_url,"passport":assess_material(m)}
def demand_dict(d): return {"id":d.id,"buyer_id":d.buyer_id,"buyer":d.buyer.name,"title":d.title,"material_type":d.material_type,"quantity":d.quantity,"unit":d.unit,"min_quality":d.min_quality,"intended_use":d.intended_use,"deadline":d.deadline.isoformat(),"lat":d.lat,"lng":d.lng,"location":d.location,"status":d.status}
def allocation_dict(a): return {"id":a.id,"material_id":a.material_id,"demand_id":a.demand_id,"material_title":a.material.title,"demand_title":a.demand.title,"supplier":a.material.supplier.name,"buyer":a.demand.buyer.name,"quantity":a.quantity,"distance_km":a.distance_km,"transport_cost":a.transport_cost,"emissions_kg":a.emissions_kg,"status":a.status,"supplier_location":a.material.location,"buyer_location":a.demand.location,"supplier_lat":a.material.lat,"supplier_lng":a.material.lng,"buyer_lat":a.demand.lat,"buyer_lng":a.demand.lng,"created_at":a.created_at.isoformat()}

@app.get("/api/health")
def health(): return {"status":"ok","database":"sqlite","synthetic_demo_data":True}
@app.post("/api/auth/register")
def register(payload:RegisterIn,db:Session=Depends(get_db)):
    if payload.role not in {"supplier","buyer"}: raise HTTPException(400,"Role must be supplier or buyer")
    if db.query(User).filter_by(email=payload.email.lower()).first(): raise HTTPException(409,"Email already registered")
    u=User(name=payload.name,email=payload.email.lower(),password_hash=hash_password(payload.password),role=payload.role,organisation=payload.organisation); db.add(u); db.commit(); db.refresh(u)
    return {"access_token":create_token(u),"token_type":"bearer","user":user_dict(u)}
@app.post("/api/auth/login")
def login(payload:LoginIn,db:Session=Depends(get_db)):
    u=db.query(User).filter_by(email=payload.email.lower()).first()
    if not u or not verify_password(payload.password,u.password_hash): raise HTTPException(401,"Incorrect email or password")
    return {"access_token":create_token(u),"token_type":"bearer","user":user_dict(u)}
@app.get("/api/auth/me")
def me(u:User=Depends(current_user)): return user_dict(u)
@app.get("/api/demo-accounts")
def demo_accounts(): return [{"role":r,"email":f"{r}@demo.reuse" if r=="admin" else f"{r}1@demo.reuse","password":"Demo@123"} for r in ["supplier","buyer","admin"]]

@app.get("/api/dashboard")
def dashboard(db:Session=Depends(get_db),u:User=Depends(current_user)):
    mats=db.query(Material).all(); demands=db.query(Demand).all(); allocs=db.query(Allocation).all()
    delivered=[a for a in allocs if a.status=="Delivered"]
    def scope_material(m): return u.role in {"admin","buyer"} or (u.role=="supplier" and m.supplier_id==u.id)
    def scope_demand(d): return u.role in {"admin","supplier"} or (u.role=="buyer" and d.buyer_id==u.id)
    recent=db.query(Allocation).options(joinedload(Allocation.material).joinedload(Material.supplier),joinedload(Allocation.demand).joinedload(Demand.buyer)).order_by(Allocation.updated_at.desc()).limit(8).all()
    return {"stats":{"available_tonnes":round(sum(m.available_quantity for m in mats if scope_material(m)),1),"open_demands":sum(1 for d in demands if d.status=="Open" and scope_demand(d)),"active_allocations":sum(1 for a in allocs if a.status not in {"Delivered","Cancelled"}),"delivered_tonnes":round(sum(a.quantity for a in delivered),1),"landfill_diverted_tonnes":round(sum(a.quantity for a in delivered),1),"virgin_material_replacement_tonnes":round(sum(a.quantity for a in delivered),1),"money_saved_inr":round(sum(a.quantity*650 for a in delivered),0),"co2_avoided_kg":round(sum(max(0,a.quantity*85-a.emissions_kg) for a in delivered),1),"virtual_water_saved_l":round(sum(a.quantity*1200 for a in delivered),0)},"material_mix":[{"name":t,"tonnes":round(sum(m.available_quantity for m in mats if m.material_type==t and scope_material(m)),1)} for t in sorted(set(m.material_type for m in mats))],"delivered_mix":[{"name":t,"tonnes":round(sum(a.quantity for a in delivered if a.material.material_type==t),1)} for t in sorted(set(a.material.material_type for a in delivered))],"allocation_trend":[{"month":m,"delivered":sum(a.quantity for a in delivered if a.updated_at.strftime("%b")==m)} for m in ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]],"recent_transactions":[allocation_dict(a) for a in recent],"synthetic_demo_data":True,"environmental_factors":"Estimated demonstration factors; not verified lifecycle assessment values."}

@app.get("/api/materials")
def list_materials(q:str="",db:Session=Depends(get_db),u:User=Depends(current_user)):
    query=db.query(Material).options(joinedload(Material.supplier))
    if u.role=="supplier": query=query.filter(Material.supplier_id==u.id)
    if q: query=query.filter((Material.title.ilike(f"%{q}%"))|(Material.material_type.ilike(f"%{q}%"))|(Material.location.ilike(f"%{q}%")))
    return [material_dict(m) for m in query.order_by(Material.created_at.desc()).all()]
@app.post("/api/materials")
def create_material(payload:MaterialIn,db:Session=Depends(get_db),u:User=Depends(roles("supplier","admin"))):
    m=Material(**payload.model_dump(),supplier_id=u.id); db.add(m); db.commit(); db.refresh(m); db.add(AuditLog(actor_id=u.id,action="MATERIAL_CREATED",details=f"Material #{m.id}: {m.title}")); db.commit(); return material_dict(m)
@app.put("/api/materials/{mid}")
def update_material(mid:int,payload:MaterialIn,db:Session=Depends(get_db),u:User=Depends(roles("supplier","admin"))):
    m=db.get(Material,mid)
    if not m or (u.role!="admin" and m.supplier_id!=u.id): raise HTTPException(404,"Material not found")
    data=payload.model_dump()
    if data["quantity"] < m.reserved_quantity: raise HTTPException(409,"Quantity cannot be lower than already reserved stock")
    for k,v in data.items(): setattr(m,k,v)
    db.commit(); db.refresh(m); return material_dict(m)
@app.delete("/api/materials/{mid}")
def delete_material(mid:int,db:Session=Depends(get_db),u:User=Depends(roles("supplier","admin"))):
    m=db.get(Material,mid)
    if not m or (u.role!="admin" and m.supplier_id!=u.id): raise HTTPException(404,"Material not found")
    if m.reserved_quantity>0: raise HTTPException(409,"Cannot delete material with reserved stock")
    db.delete(m); db.commit(); return {"deleted":True}
@app.post("/api/uploads")
def upload_image(file:UploadFile=File(...),u:User=Depends(roles("supplier","admin"))):
    if file.content_type not in {"image/jpeg","image/png","image/webp"}: raise HTTPException(415,"Only JPEG, PNG and WebP images are allowed")
    if file.size and file.size>5_000_000: raise HTTPException(413,"Image must be 5 MB or smaller")
    ext={"image/jpeg":".jpg","image/png":".png","image/webp":".webp"}[file.content_type]; name=f"{datetime.utcnow().timestamp():.0f}-{re.sub('[^a-zA-Z0-9]','',file.filename or 'image')[:24]}{ext}"
    path=Path("uploads")/name; path.write_bytes(file.file.read()); return {"url":f"/uploads/{name}"}

@app.get("/api/demands")
def list_demands(db:Session=Depends(get_db),u:User=Depends(current_user)):
    q=db.query(Demand).options(joinedload(Demand.buyer))
    if u.role=="buyer": q=q.filter(Demand.buyer_id==u.id)
    return [demand_dict(d) for d in q.order_by(Demand.deadline).all()]
@app.post("/api/demands")
def create_demand(payload:DemandIn,db:Session=Depends(get_db),u:User=Depends(roles("buyer","admin"))):
    d=Demand(**payload.model_dump(),buyer_id=u.id); db.add(d); db.commit(); db.refresh(d); db.add(AuditLog(actor_id=u.id,action="DEMAND_CREATED",details=f"Demand #{d.id}: {d.title}")); db.commit(); return demand_dict(d)

@app.post("/api/ai/parse-material")
def parse_material(payload:dict,u:User=Depends(roles("supplier","admin"))):
    description=str(payload.get("description", ""))[:4000]
    # Optional LLM extraction; deterministic parser remains the offline-safe fallback.
    if os.getenv("AI_PROVIDER", "deterministic").lower()=="openai" and os.getenv("OPENAI_API_KEY"):
        try:
            prompt=("Extract a construction material listing from the text. Return JSON only with keys title, material_type, description, quantity, unit, quality, condition. Allowed material_type values: Concrete rubble, Bricks, Natural stone, Steel, Timber, Pavers, Soil, Gypsum, Treated timber. Never infer chemical safety, contamination absence, or lab verification. If uncertain use condition=unverified. Text: "+description)
            req=urllib.request.Request("https://api.openai.com/v1/chat/completions",data=json.dumps({"model":os.getenv("OPENAI_MODEL","gpt-4o-mini"),"messages":[{"role":"user","content":prompt}],"response_format":{"type":"json_object"},"temperature":0}).encode(),headers={"Authorization":"Bearer "+os.environ["OPENAI_API_KEY"],"Content-Type":"application/json"})
            with urllib.request.urlopen(req,timeout=12) as response: data=json.loads(response.read())
            extracted=json.loads(data["choices"][0]["message"]["content"])
            extracted.update({"extraction_mode":"llm","notice":"Review every extracted field. LLM extraction does not establish chemical safety or laboratory verification."})
            return extracted
        except Exception:
            pass
    types={"concrete rubble":["concrete","rubble","demolition waste"],"Bricks":["brick","bricks"],"Natural stone":["stone","granite","basalt"],"Steel":["steel","rebar","metal"],"Timber":["timber","wood"],"Pavers":["paver","paving blocks"],"Soil":["soil","excavated earth"]}
    low=description.lower(); kind=next((k for k,words in types.items() if any(w in low for w in words)),"Concrete rubble")
    qty=re.search(r"(\d+(?:\.\d+)?)\s*(tonnes?|tons?|kg|cubic metres?|m3)",low)
    quantity=float(qty.group(1)) if qty else 10
    unit="tonnes"
    if qty and qty.group(2)=="kg": quantity=quantity/1000
    elif qty and qty.group(2) in {"cubic metres","m3"}: unit="m³"
    quality=next((q for q in ["Excellent","Good","Fair","Poor"] if q.lower() in low),"Good")
    return {"title":f"Recovered {kind}","material_type":kind,"description":description,"quantity":quantity,"unit":unit,"quality":quality,"condition":"unverified" if any(w in low for w in ["unknown","untested","not sure"]) else "verified","extraction_mode":"deterministic_fallback","notice":"Review every extracted field. This assistant does not establish chemical safety or laboratory verification."}

@app.post("/api/optimise")
def run_optimiser(payload:OptimiseIn,db:Session=Depends(get_db),u:User=Depends(roles("admin"))):
    materials=db.query(Material).options(joinedload(Material.supplier)).all(); demands=db.query(Demand).options(joinedload(Demand.buyer)).filter(Demand.status=="Open").all()
    for d in demands:
        committed=db.query(func.coalesce(func.sum(Allocation.quantity),0)).filter(Allocation.demand_id==d.id,Allocation.status.in_(["Confirmed","In Transit","Delivered"])).scalar() or 0
        d.optimizer_quantity=max(0,d.quantity-float(committed))
    results,method=optimise(materials,demands)
    # Proposed allocations are replaced on each run; only unconfirmed proposals may be replaced.
    db.query(Allocation).filter(Allocation.status=="Proposed").delete(synchronize_session=False); db.commit()
    out=[]
    for r in results:
        a=Allocation(material_id=r["material_id"],demand_id=r["demand_id"],quantity=r["quantity"],distance_km=r["distance_km"],transport_cost=r["transport_cost"],emissions_kg=r["emissions_kg"],status="Proposed",monsoon_priority=0)
        db.add(a); db.flush(); out.append(a)
    db.add(AuditLog(actor_id=u.id,action="OPTIMISATION_RUN",details=f"{len(out)} proposed matches")); db.commit()
    return {"allocations":[allocation_dict(a) for a in out],"count":len(out),"method":method,"assumptions":"Road distance is estimated as 1.28 × straight-line distance; transport rate ₹24/tonne-km; emissions 0.12 kg CO₂e/tonne-km. Synthetic demo assumptions, not carrier quotes or audited factors."}
@app.get("/api/allocations")
def list_allocations(db:Session=Depends(get_db),u:User=Depends(current_user)):
    q=db.query(Allocation).options(joinedload(Allocation.material).joinedload(Material.supplier),joinedload(Allocation.demand).joinedload(Demand.buyer))
    if u.role=="supplier": q=q.join(Material).filter(Material.supplier_id==u.id)
    elif u.role=="buyer": q=q.join(Demand).filter(Demand.buyer_id==u.id)
    return [allocation_dict(a) for a in q.order_by(Allocation.updated_at.desc()).all()]
@app.patch("/api/allocations/{aid}/status")
def update_status(aid:int,payload:StatusIn,db:Session=Depends(get_db),u:User=Depends(roles("admin"))):
    allowed={"Proposed":"Confirmed","Confirmed":"In Transit","In Transit":"Delivered"}
    a=db.query(Allocation).options(joinedload(Allocation.material),joinedload(Allocation.demand)).filter_by(id=aid).with_for_update().first()
    if not a: raise HTTPException(404,"Allocation not found")
    if allowed.get(a.status)!=payload.status: raise HTTPException(409,f"Invalid transition: {a.status} cannot move to {payload.status}")
    m=a.material
    if payload.status=="Confirmed":
        result=db.execute(update(Material).where(Material.id==m.id,Material.quantity-Material.reserved_quantity>=a.quantity).values(reserved_quantity=Material.reserved_quantity+a.quantity))
        if result.rowcount!=1: raise HTTPException(409,"Insufficient available inventory; another allocation may have reserved it")
        db.refresh(m)
    if payload.status=="Delivered":
        result=db.execute(update(Material).where(Material.id==m.id,Material.reserved_quantity>=a.quantity,Material.quantity>=a.quantity).values(reserved_quantity=Material.reserved_quantity-a.quantity,quantity=Material.quantity-a.quantity))
        if result.rowcount!=1: raise HTTPException(409,"Reservation ledger mismatch")
        db.refresh(m)
    a.status=payload.status; a.updated_at=datetime.utcnow()
    db.add(AuditLog(actor_id=u.id,allocation_id=a.id,action=f"ALLOCATION_{payload.status.upper().replace(' ','_')}",details=f"{a.quantity} {m.unit} of {m.title}")); db.commit(); db.refresh(a); return allocation_dict(a)
@app.get("/api/audit")
def audit(db:Session=Depends(get_db),u:User=Depends(roles("admin"))):
    return [{"id":x.id,"action":x.action,"details":x.details,"created_at":x.created_at.isoformat()} for x in db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(100).all()]
@app.get("/api/impact/export.csv")
def export_impact(db:Session=Depends(get_db),u:User=Depends(current_user)):
    delivered=db.query(Allocation).filter(Allocation.status=="Delivered").all(); out=io.StringIO(); w=csv.writer(out); w.writerow(["allocation_id","material","demand","quantity_tonnes","distance_km","transport_cost_inr","estimated_co2_avoided_kg","estimated_money_saved_inr","estimated_virtual_water_saved_l"])
    for a in delivered: w.writerow([a.id,a.material.title,a.demand.title,a.quantity,a.distance_km,a.transport_cost,round(max(0,a.quantity*85-a.emissions_kg),2),round(a.quantity*650,2),round(a.quantity*1200,2)])
    return StreamingResponse(iter([out.getvalue()]),media_type="text/csv",headers={"Content-Disposition":"attachment; filename=impact-report.csv"})
