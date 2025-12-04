from dynamic_scm_milp import SupplyChainModel
from data_loader import SupplyChainData

print("=" * 70)
print("DEBUG: 5-STAGE FLOW")
print("=" * 70)

data = SupplyChainData(m=1, mode='Pm', num_stages=5)
model = SupplyChainModel(data)
model.create_variables()
model.add_constraints()
model.set_objective()
success = model.solve()

if success:
    breakdown = model.get_cost_breakdown()
    print("\nCOST BREAKDOWN:")
    for key, val in breakdown.items():
        print(f"  {key:20s}: {val:>12,.0f}")
    
    print("\n" + "=" * 70)
    print("PRODUCTION QUANTITIES:")
    print("=" * 70)
    print(f"{'Period':<8} {'Site1 (x)':<12} {'Site2 (x2)':<12} {'Demand':<10}")
    print("-" * 70)
    for t in range(data.T):
        x_val = model.x[t].solution_value()
        x2_val = model.x2[t].solution_value()
        dem = data.demand[t]
        print(f"{t+1:<8} {x_val:<12.1f} {x2_val:<12.1f} {dem:<10.0f}")
    
    print("\n" + "=" * 70)
    print("PURCHASING FROM SUPPLIERS:")
    print("=" * 70)
    print(f"{'Period':<8} {'Sup1_1':<10} {'Sup1_2':<10} {'Sup2':<10} {'Sup3':<10}")
    print("-" * 70)
    total_purch = [0, 0, 0, 0]
    for t in range(data.T):
        vals = [model.q[j, t].solution_value() for j in range(4)]
        for j in range(4):
            total_purch[j] += vals[j]
        print(f"{t+1:<8} {vals[0]:<10.1f} {vals[1]:<10.1f} {vals[2]:<10.1f} {vals[3]:<10.1f}")
    print("-" * 70)
    print(f"{'TOTAL':<8} {total_purch[0]:<10.1f} {total_purch[1]:<10.1f} {total_purch[2]:<10.1f} {total_purch[3]:<10.1f}")
    
    print("\n" + "=" * 70)
    print("INVENTORY LEVELS:")
    print("=" * 70)
    print(f"{'Period':<8} {'i[1]':<10} {'i[2]':<10} {'i[3]':<10} {'i[4]':<10} {'i[5]':<10}")
    print("-" * 70)
    for t in range(data.T):
        vals = [model.i[k, t].solution_value() for k in range(1, 6)]
        print(f"{t+1:<8} {vals[0]:<10.1f} {vals[1]:<10.1f} {vals[2]:<10.1f} {vals[3]:<10.1f} {vals[4]:<10.1f}")
