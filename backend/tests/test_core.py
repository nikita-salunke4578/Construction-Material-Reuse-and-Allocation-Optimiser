from types import SimpleNamespace
from app.safety import assess_material
from app.optimizer import optimise

def mat(**kw):
    d=dict(material_type="Concrete rubble",condition="verified",contamination=False,painted=False,treated=False,building_year=2018,lab_verified=False,quality="Good",quantity=10,reserved_quantity=0,unit="tonnes",lat=18.52,lng=73.85,id=1,title="Concrete",supplier=None,location="Pune")
    d.update(kw); return SimpleNamespace(**d)
def dem(**kw):
    d=dict(material_type="Concrete rubble",intended_use="recharge pit",min_quality="Fair",quantity=8,unit="tonnes",lat=18.6,lng=73.9,deadline=__import__('datetime').date.today(),id=1,title="Recharge pit",buyer=None,location="Pune")
    d.update(kw); return SimpleNamespace(**d)
def test_contaminated_blocked(): assert assess_material(mat(contamination=True),"rural road base")["status"]=="blocked"
def test_old_unverified_restricted_for_recharge(): assert assess_material(mat(building_year=1990),"recharge pit")["status"]=="restricted"
def test_old_material_allowed_other_use(): assert assess_material(mat(building_year=1990),"road sub-base")["safe_for_use"]
def test_optimizer_respects_supply_and_demand():
    results,_=optimise([mat(quantity=4)],[dem(quantity=8)])
    assert sum(x["quantity"] for x in results)<=4.001
    results,_=optimise([mat(quantity=10)],[dem(quantity=3)])
    assert sum(x["quantity"] for x in results)<=3.001
def test_optimizer_excludes_unsafe():
    results,_=optimise([mat(contamination=True)],[dem()]); assert results==[]

from app.inventory import reserve_stock, deliver_stock
def test_inventory_reservation_and_delivery():
    m=mat(quantity=10,reserved_quantity=0)
    reserve_stock(m,7)
    assert m.reserved_quantity==7 and m.quantity==10
    try: reserve_stock(m,4); assert False, "over-allocation should fail"
    except ValueError: pass
    deliver_stock(m,7)
    assert m.quantity==3 and m.reserved_quantity==0
def test_delivery_requires_reservation():
    m=mat(quantity=5,reserved_quantity=0)
    try: deliver_stock(m,2); assert False, "unreserved delivery should fail"
    except ValueError: pass
