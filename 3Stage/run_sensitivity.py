import time
from data_loader import SupplyChainData
from dynamic_scm_milp import SupplyChainModel

BASE_PERIOD_DAYS = 12

def solve_one(m, mode, num_stages=3):
    """
    Run model once with given m, mode, and num_stages.
    Returns: (data, model, objective_value, cpu_time)
    """
    data = SupplyChainData(m=m, mode=mode, num_stages=num_stages)
    model = SupplyChainModel(data)

    start_time = time.time()
    model.create_variables()
    model.add_constraints()
    model.set_objective()
    success = model.solve()
    end_time = time.time()

    duration = end_time - start_time
    
    if success:
        obj_val = model.solver.Objective().Value()
    else:
        obj_val = float('inf')

    return data, model, obj_val, duration

def print_purchasing_plan_comparison(model_pm, model_pmd, T, m):
    """
    Print purchasing plan comparison between Pm and Pmd
    """
    plan_pm = model_pm.get_purchasing_plan()
    plan_pmd = model_pmd.get_purchasing_plan()
    
    print(f"\n{'='*80}")
    print(f"PURCHASING PLAN COMPARISON (m={m}, T={T})")
    print(f"{'='*80}")
    
    # Header
    print(f"{'Period':<8} | {'--- Pm ---':<35} | {'--- Pmd ---':<35}")
    print(f"{'':8} | {'Sup1_1':<8} {'Sup1_2':<8} {'Sup2':<6} {'Sup3':<6} | {'Sup1_1':<8} {'Sup1_2':<8} {'Sup2':<6} {'Sup3':<6}")
    print("-" * 80)
    
    for t in range(T):
        vals_pm = plan_pm[t]
        vals_pmd = plan_pmd[t]
        print(f"{t+1:<8} | {vals_pm[0]:<8.0f} {vals_pm[1]:<8.0f} {vals_pm[2]:<6.0f} {vals_pm[3]:<6.0f} | "
              f"{vals_pmd[0]:<8.0f} {vals_pmd[1]:<8.0f} {vals_pmd[2]:<6.0f} {vals_pmd[3]:<6.0f}")
    print("-" * 80)

def run_analysis():
    """
    Table 13 style: 3-stage model with m=1,2 for both Pm and Pmd
    """
    m_values = [1, 2]  # Paper Table 13 uses m=1,2 for 3-stage
    num_stages = 3

    print("=" * 110)
    print(f"3-STAGE MODEL SENSITIVITY ANALYSIS (Pm vs Pmd)")
    print("=" * 110)
    print(
        f"{'m':<3} | {'Len/Per(d)':<10} | {'Periods':<7} | "
        f"{'Cost_Pm':>12} | {'CPU_Pm(s)':>10} | "
        f"{'Cost_Pmd':>12} | {'CPU_Pmd(s)':>10}"
    )
    print("-" * 110)

    results = []

    for m in m_values:
        data_pm, model_pm, obj_pm, cpu_pm = solve_one(m, mode='Pm', num_stages=num_stages)
        data_pmd, model_pmd, obj_pmd, cpu_pmd = solve_one(m, mode='Pmd', num_stages=num_stages)

        T = data_pm.T
        len_per = BASE_PERIOD_DAYS / m

        print(
            f"{m:<3} | {len_per:<10.2f} | {T:<7} | "
            f"{obj_pm:>12,.0f} | {cpu_pm:>10.4f} | "
            f"{obj_pmd:>12,.0f} | {cpu_pmd:>10.4f}"
        )

        results.append({
            'm': m,
            'T': T,
            'len_per': len_per,
            'model_pm': model_pm,
            'model_pmd': model_pmd,
            'obj_pm': obj_pm,
            'obj_pmd': obj_pmd
        })

    print("-" * 110)
    print()

    # Cost Breakdown
    print("=" * 110)
    print("COST BREAKDOWN FOR EACH m")
    print("=" * 110)
    
    for res in results:
        m = res['m']
        T = res['T']
        model_pm = res['model_pm']
        model_pmd = res['model_pmd']
        
        breakdown_pm = model_pm.get_cost_breakdown()
        breakdown_pmd = model_pmd.get_cost_breakdown()
        
        print(f"\n{'='*60}")
        print(f"m = {m} | Periods = {T} | 3-STAGE MODEL")
        print(f"{'='*60}")
        print(f"{'Cost Component':<20} | {'Pm':>15} | {'Pmd':>15} | {'Diff':>12}")
        print("-" * 60)
        
        components = ['purchasing', 'production', 'holding', 'transport', 'total']
        labels = ['Purchasing', 'Production', 'Holding', 'Transport', 'TOTAL']
        
        for comp, label in zip(components, labels):
            val_pm = breakdown_pm[comp]
            val_pmd = breakdown_pmd[comp]
            diff = val_pmd - val_pm
            print(f"{label:<20} | {val_pm:>15,.0f} | {val_pmd:>15,.0f} | {diff:>+12,.0f}")
        
        print("-" * 60)

    # Purchasing Plan
    print("\n" + "=" * 110)
    print("PURCHASING PLANS FOR EACH m")
    print("=" * 110)
    
    for res in results:
        m = res['m']
        T = res['T']
        model_pm = res['model_pm']
        model_pmd = res['model_pmd']
        print_purchasing_plan_comparison(model_pm, model_pmd, T, m)

    print("\n" + "=" * 110)
    print("DONE 3-STAGE SENSITIVITY ANALYSIS.")
    print("=" * 110)

if __name__ == "__main__":
    run_analysis()