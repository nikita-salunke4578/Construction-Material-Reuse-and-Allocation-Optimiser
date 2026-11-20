"""Conservative intended-use rules. A photo is never treated as a chemical test."""
WATER_USES = {"recharge pit", "farm pond", "irrigation", "water channel", "water harvesting", "farm or water-related"}
FARM_USES = {"farm", "farm bund", "agriculture", "farm pond", "irrigation", "recharge pit", "water channel", "water harvesting", "farm or water-related"}

def assess_material(m, intended_use: str | None = None):
    reasons=[]; use=(intended_use or "").strip().lower()
    flags = [("contaminated", getattr(m,"contamination",False)),("painted",getattr(m,"painted",False)),("chemically treated",getattr(m,"treated",False))]
    for label, yes in flags:
        if yes: reasons.append(f"Material is marked {label}; reuse is blocked pending specialist assessment")
    condition=getattr(m,"condition","verified")
    if condition=="restricted": reasons.append("Material is explicitly marked restricted")
    if condition in {"unknown","unverified"} and use in FARM_USES:
        reasons.append("Unverified material cannot be used for farm or water-related applications pending verification")
    year=getattr(m,"building_year",None)
    if year and year < 2000 and use in FARM_USES and not getattr(m,"lab_verified",False):
        reasons.append("Pre-2000 building material requires laboratory verification for farm or water-related applications")
    if use in WATER_USES and getattr(m,"material_type","").lower() in {"gypsum","plasterboard","painted timber","treated timber","asbestos cement"}:
        reasons.append("This material category is unsuitable for water-related applications")
    if reasons:
        return {"status":"blocked" if any(x in " ".join(reasons).lower() for x in ["contaminated","painted","chemically treated"]) else "restricted", "safe_for_use":False,"reasons":reasons,"image_assessment":"Images are visual references only and cannot detect chemical contamination, hazardous coatings or asbestos."}
    review=getattr(m,"condition","verified") in {"unknown","unverified"}
    return {"status":"review_required" if review else "verified", "safe_for_use":True,"reasons":["Documentation review recommended before use." if review else "No configured rule was triggered; verify documentation and site conditions before use."],"image_assessment":"Images are visual references only and cannot detect chemical contamination, hazardous coatings or asbestos."}

def quality_rank(q): return {"poor":0,"fair":1,"good":2,"excellent":3}.get((q or "").lower(),0)
