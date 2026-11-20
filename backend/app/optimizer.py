from math import radians, sin, cos, asin, sqrt
from datetime import date
from .safety import assess_material, quality_rank

def distance_km(a_lat,a_lng,b_lat,b_lng):
    dlat=radians(b_lat-a_lat); dlng=radians(b_lng-a_lng)
    x=sin(dlat/2)**2+cos(radians(a_lat))*cos(radians(b_lat))*sin(dlng/2)**2
    return 6371*2*asin(sqrt(x))

def optimise(materials, demands, monsoon_priority=25):
    """MILP maximises fulfilled demand while penalising cost, distance and emissions.
    PuLP/CBC is used when available; deterministic constrained fallback keeps API usable.
    """
    candidates=[]
    for m in materials:
        for d in demands:
            if m.material_type.lower()!=d.material_type.lower() or m.unit!=d.unit: continue
            safety=assess_material(m,d.intended_use)
            if not safety["safe_for_use"] or quality_rank(m.quality)<quality_rank(d.min_quality): continue
            qty=max(0,m.quantity-m.reserved_quantity)
            if qty<=0 or getattr(d,"optimizer_quantity",d.quantity)<=0: continue
            dist=distance_km(m.lat,m.lng,d.lat,d.lng)
            days=(d.deadline-date.today()).days
            if days < 0: continue
            # Road-distance proxy and rate assumptions are disclosed as estimates.
            road_km=dist*1.28
            rate=24.0 # INR / tonne-km, synthetic demo assumption
            cost=road_km*rate
            kgco2=road_km*0.12 # kg CO2e / tonne-km, estimated factor
            urgency=max(0,1-min(days,30)/30)
            monsoon_bonus=(monsoon_priority/100)*urgency*0.18
            score=1.0 + monsoon_bonus - (cost/10000)*0.18 - (kgco2/100)*0.12
            candidates.append((m,d,qty,dist,cost,kgco2,score))
    results=[]
    try:
        import pulp
        prob=pulp.LpProblem("circular_material_allocation",pulp.LpMaximize)
        xs={i:pulp.LpVariable(f"x_{i}",lowBound=0) for i in range(len(candidates))}
        prob += pulp.lpSum(xs[i]*candidates[i][6] for i in xs)
        for m in materials:
            ids=[i for i,c in enumerate(candidates) if c[0].id==m.id]
            if ids: prob += pulp.lpSum(xs[i] for i in ids) <= max(0,m.quantity-m.reserved_quantity)
        for d in demands:
            ids=[i for i,c in enumerate(candidates) if c[1].id==d.id]
            if ids: prob += pulp.lpSum(xs[i] for i in ids) <= getattr(d,"optimizer_quantity",d.quantity)
        prob.solve(pulp.PULP_CBC_CMD(msg=False, timeLimit=8))
        for i,x in xs.items():
            q=float(pulp.value(x) or 0)
            if q>0.001:
                m,d,_,dist,cost,co2,score=candidates[i]
                results.append({"material_id":m.id,"demand_id":d.id,"quantity":round(q,3),"distance_km":round(dist*1.28,1),"transport_cost":round(cost*q,2),"emissions_kg":round(co2*q,2),"score":round(score,4),"material_title":m.title,"demand_title":d.title,"supplier":m.supplier.name if m.supplier else "Supplier","buyer":d.buyer.name if d.buyer else "Buyer","supplier_location":m.location,"buyer_location":d.location,"supplier_lat":m.lat,"supplier_lng":m.lng,"buyer_lat":d.lat,"buyer_lng":d.lng})
        return results,"PuLP mixed-integer linear optimisation (CBC)"
    except Exception:
        # Greedy fallback retains all inventory/demand constraints.
        remaining_m={m.id:max(0,m.quantity-m.reserved_quantity) for m in materials}; remaining_d={d.id:getattr(d,"optimizer_quantity",d.quantity) for d in demands}
        for m,d,_,dist,cost,co2,score in sorted(candidates,key=lambda c:(-c[6],c[4])):
            q=min(remaining_m[m.id],remaining_d[d.id])
            if q<=0: continue
            remaining_m[m.id]-=q; remaining_d[d.id]-=q
            results.append({"material_id":m.id,"demand_id":d.id,"quantity":round(q,3),"distance_km":round(dist*1.28,1),"transport_cost":round(cost*q,2),"emissions_kg":round(co2*q,2),"score":round(score,4),"material_title":m.title,"demand_title":d.title,"supplier":m.supplier.name if m.supplier else "Supplier","buyer":d.buyer.name if d.buyer else "Buyer","supplier_location":m.location,"buyer_location":d.location,"supplier_lat":m.lat,"supplier_lng":m.lng,"buyer_lat":d.lat,"buyer_lng":d.lng})
        return results,"Deterministic constrained greedy fallback (PuLP unavailable)"
