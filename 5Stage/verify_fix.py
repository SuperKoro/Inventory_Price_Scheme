from dynamic_scm_milp import SupplyChainModel
from data_loader import SupplyChainData

print("=" * 70)
print("VERIFYING 5-STAGE FIX")
print("=" * 70)

data = SupplyChainData(m=1, mode='Pm', num_stages=5)
model = SupplyChainModel(data)
model.create_variables()
model.add_constraints()
model.set_objective()
success = model.solve()

if success:
    breakdown = model.get_cost_breakdown()
    
    print("\n[OK] Model solved successfully!")
    print("\nCOST BREAKDOWN:")
    print(f"  Purchasing:      {breakdown['purchasing']:>10,.0f}")
    print(f"  Prod Site 1:     {breakdown['production_site1']:>10,.0f}")
    print(f"  Prod Site 2:     {breakdown['production_site2']:>10,.0f}")
    print(f"  Prod TOTAL:      {breakdown['production']:>10,.0f}")
    print(f"  Holding:         {breakdown['holding']:>10,.0f}")
    print(f"  Transport:       {breakdown['transport']:>10,.0f}")
    print(f"  TOTAL:           {breakdown['total']:>10,.0f}")
    
    # Check if the bug is fixed
    print("\n" + "=" * 70)
    if breakdown['purchasing'] > 0 and breakdown['production_site1'] > 0:
        print("[PASS] BUG FIXED! Site 2 now requires input from Site 1")
        print(f"   - Purchasing from suppliers: {breakdown['purchasing']:,.0f}")
        print(f"   - Production at Site 1: {breakdown['production_site1']:,.0f}")
        print(f"   - Production at Site 2: {breakdown['production_site2']:,.0f}")
    else:
        print("[FAIL] Bug still exists - Site 2 producing without input!")
        print(f"   - Purchasing: {breakdown['purchasing']:,.0f}")
        print(f"   - Prod Site 1: {breakdown['production_site1']:,.0f}")
        print(f"   - Prod Site 2: {breakdown['production_site2']:,.0f}")
    print("=" * 70)
else:
    print("[ERROR] Model failed to solve!")
