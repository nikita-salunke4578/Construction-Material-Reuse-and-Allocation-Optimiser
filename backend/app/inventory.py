"""Atomic inventory ledger operations; callers must hold the material row lock."""
def reserve_stock(material, quantity: float):
    available=max(0.0,float(material.quantity)-float(material.reserved_quantity))
    if quantity<=0 or available+1e-8<quantity:
        raise ValueError("Insufficient available inventory; another allocation may have reserved it")
    material.reserved_quantity+=quantity

def deliver_stock(material, quantity: float):
    if quantity<=0 or float(material.reserved_quantity)+1e-8<quantity:
        raise ValueError("Reservation ledger mismatch")
    material.reserved_quantity-=quantity
    material.quantity-=quantity
    if material.quantity < -1e-8: raise ValueError("Inventory quantity cannot become negative")
