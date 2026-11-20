from datetime import date, timedelta
from .models import User, Material, Demand
from .security import hash_password

LOCATIONS = [
 ("Pune",18.5204,73.8567),("Pimpri-Chinchwad",18.6298,73.7997),("Hinjawadi",18.5912,73.7389),("Hadapsar",18.5089,73.9260),("Talegaon",18.7350,73.6750),("Chakan",18.7606,73.8636),("Lonavala",18.7546,73.4062),("Baramati",18.1517,74.5777),("Satara",17.6805,74.0183),("Nashik",19.9975,73.7898),("Kolhapur",16.7050,74.2433),("Ahmednagar",19.0948,74.7480),("Saswad",18.3430,74.0310),("Shirur",18.8270,74.3740),("Khed",18.8400,73.8900)]

def seed(db):
    if db.query(User).count(): return
    suppliers=[]; buyers=[]
    for i in range(5):
        u=User(name=["Aarav Infra Materials","Deccan Salvage Co.","GreenBuild Traders","Pune Demolition Works","Sahyadri Reclaim"][i],email=f"supplier{i+1}@demo.reuse",password_hash=hash_password("Demo@123"),role="supplier",organisation=f"Supplier {i+1}")
        db.add(u); suppliers.append(u)
    for i in range(4):
        u=User(name=["Pune Smart Works","JalSakhi Foundation","GramVikas Collective","Maharashtra Rural Works"][i],email=f"buyer{i+1}@demo.reuse",password_hash=hash_password("Demo@123"),role="buyer",organisation=f"Buyer {i+1}")
        db.add(u); buyers.append(u)
    admin=User(name="Platform Administrator",email="admin@demo.reuse",password_hash=hash_password("Demo@123"),role="admin",organisation="Reuse Platform")
    db.add(admin); db.flush()
    for i in range(18):
        loc=LOCATIONS[i%len(LOCATIONS)]; types=["Concrete rubble","Bricks","Natural stone","Steel","Timber","Pavers","Soil","Concrete rubble","Bricks","Natural stone","Steel","Timber","Pavers","Soil","Concrete rubble","Bricks","Gypsum","Treated timber"]
        flags=i in (14,16,17); old=i in (5,12)
        db.add(Material(supplier_id=suppliers[i%len(suppliers)].id,title=f"{types[i]} recovery lot #{i+1:02d}",material_type=types[i],description=f"Recovered {types[i].lower()} from a documented site clearance. Synthetic demonstration record.",quantity=[22,14,18,8,11,30,45][i%7],unit="tonnes",quality=["Good","Excellent","Fair"][i%3],condition="unverified" if i in (5,12,16) else "verified",building_year=1996 if old else 2014+i%10,contamination=i==14,painted=i==17,treated=i==17,lab_verified=i in (2,8),lat=loc[1],lng=loc[2],location=loc[0],price_per_unit=450+i*22,image_url=""))
    db.flush()
    uses=["recharge pit","farm bund","rural road base","municipal footpath","landscaping","farm pond","recharge pit","road sub-base","community works","irrigation"]
    types=["Concrete rubble","Bricks","Natural stone","Steel","Timber","Pavers","Soil","Concrete rubble","Bricks","Natural stone","Steel","Pavers"]
    for i in range(12):
        loc=LOCATIONS[(i*3+2)%len(LOCATIONS)]
        db.add(Demand(buyer_id=buyers[i%len(buyers)].id,title=["Recharge pit network","Village road strengthening","Community footpath","Farm bund restoration","Municipal drainage works"][i%5],material_type=types[i],quantity=[12,8,16,5,20,7][i%6],unit="tonnes",min_quality=["Fair","Good"][i%2],intended_use=uses[i%len(uses)],deadline=date.today()+timedelta(days=5+i*2),lat=loc[1],lng=loc[2],location=loc[0]))
    db.commit()
