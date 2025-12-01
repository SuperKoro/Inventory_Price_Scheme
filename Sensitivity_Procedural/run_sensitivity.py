"""
PROCEDURAL VERSION - Sensitivity Analysis Runner
Chạy model với 4 giá trị m khác nhau
"""

import time
from dynamic_scm_procedural import run_single_scenario


def run_sensitivity_analysis():
    """Chạy sensitivity analysis với các giá trị m khác nhau"""
    m_values = [1, 2, 3, 4]
    results = []

    print("="*70)
    print("PROCEDURAL VERSION - Sensitivity Analysis")
    print("="*70)
    print(f"{'m':<3} | {'Model':<5} | {'Periods':<7} | {'Objective Cost':<15} | {'CPU Time (s)':<12}")
    print("-" * 70)

    for m in m_values:
        start_time = time.time()
        
        # Chạy model với m hiện tại
        obj_val, breakdown = run_single_scenario(m_value=m, mode='Pm', verbose=False)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Tính số periods
        T = 5 * m
        
        if obj_val is not None:
            print(f"{m:<3} | {'Pm':<5} | {T:<7} | {obj_val:>14,.0f} $ | {duration:>11.4f}")
            
            # In breakdown
            if breakdown:
                print(f"     └─ Purchasing:     {breakdown['purchasing']:>12,.0f} $")
                print(f"     └─ Production:     {breakdown['production']:>12,.0f} $")
                print(f"     └─ Holding:        {breakdown['holding']:>12,.0f} $")
                print(f"     └─ Transportation: {breakdown['transportation']:>12,.0f} $")
                print()
            
            results.append({
                'm': m,
                'periods': T,
                'objective': obj_val,
                'breakdown': breakdown,
                'time': duration
            })
        else:
            print(f"{m:<3} | {'Pm':<5} | {T:<7} | {'NO SOLUTION':>14} | {duration:>11.4f}")
            results.append({
                'm': m,
                'periods': T,
                'objective': None,
                'breakdown': None,
                'time': duration
            })

    print("-" * 70)
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    valid_results = [r for r in results if r['objective'] is not None]
    
    if valid_results:
        print(f"Total scenarios run: {len(results)}")
        print(f"Successful solves: {len(valid_results)}")
        print(f"\nCost comparison:")
        for r in valid_results:
            print(f"  m={r['m']} (T={r['periods']}): ${r['objective']:,.0f}")
        
        # Find best
        best = min(valid_results, key=lambda x: x['objective'])
        print(f"\n✅ Best configuration: m={best['m']} with cost ${best['objective']:,.0f}")
    else:
        print("❌ No successful solves found")
    
    print("="*70)
    
    return results


if __name__ == "__main__":
    results = run_sensitivity_analysis()
