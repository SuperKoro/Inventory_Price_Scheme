from dynamic_scm_milp import SupplyChainModel
from data_loader import SupplyChainData

print("=" * 70)
print("QUICK TEST: 4-STAGE vs 5-STAGE")
print("=" * 70)

# Test 4-stage
print("\n[4-STAGE] Testing with m=1, mode=Pm...")
data4 = SupplyChainData(m=1, mode='Pm', num_stages=4)
model4 = SupplyChainModel(data4)
model4.create_variables()
model4.add_constraints()
model4.set_objective()
success4 = model4.solve()

if success4:
    breakdown4 = model4.get_cost_breakdown()
    print("\n4-STAGE RESULTS:")
    print(f"  Total Cost:  {breakdown4['total']:>12,.0f}")
    print(f"  Purchasing:  {breakdown4['purchasing']:>12,.0f}")
    print(f"  Production:  {breakdown4['production']:>12,.0f}")
    print(f"  Holding:     {breakdown4['holding']:>12,.0f}")
    print(f"  Transport:   {breakdown4['transport']:>12,.0f}")

# Test 5-stage
print("\n" + "=" * 70)
print("[5-STAGE] Testing with m=1, mode=Pm...")
data5 = SupplyChainData(m=1, mode='Pm', num_stages=5)
model5 = SupplyChainModel(data5)
model5.create_variables()
model5.add_constraints()
model5.set_objective()
success5 = model5.solve()

if success5:
    breakdown5 = model5.get_cost_breakdown()
    print("\n5-STAGE RESULTS:")
    print(f"  Total Cost:  {breakdown5['total']:>12,.0f}")
    print(f"  Purchasing:  {breakdown5['purchasing']:>12,.0f}")
    print(f"  Production:  {breakdown5['production']:>12,.0f}")
    print(f"    - Site 1:  {breakdown5['production_site1']:>12,.0f}")
    print(f"    - Site 2:  {breakdown5['production_site2']:>12,.0f}")
    print(f"  Holding:     {breakdown5['holding']:>12,.0f}")
    print(f"  Transport:   {breakdown5['transport']:>12,.0f}")

print("\n" + "=" * 70)
print("DONE!")
print("=" * 70)
