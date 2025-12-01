"""
Script so sánh performance giữa SCIP và HiGHS solver
cho bài toán Inventory MILP
"""

import sys
import os
import time

# Add GE folder to path for SCIP model
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
ge_dir = os.path.join(parent_dir, 'GE')
sys.path.insert(0, ge_dir)

from data_loader import SupplyChainData
from dynamic_scm_milp import SupplyChainModel as SCIPModel

# Remove GE from path and add current dir for HiGHS model
sys.path.remove(ge_dir)

from dynamic_scm_highs import SupplyChainModelHiGHS


def run_scip_model():
    """Chạy SCIP model và thu thập kết quả"""
    print("=" * 70)
    print("RUNNING SCIP MODEL")
    print("=" * 70)
    
    data = SupplyChainData()
    model = SCIPModel(data)
    
    model.create_variables()
    model.add_constraints()
    model.set_objective()
    
    start_time = time.time()
    model.solve()
    solve_time = time.time() - start_time
    
    # Extract solution
    result = {
        'solver': 'SCIP',
        'solve_time': solve_time,
        'objective': model.solver.Objective().Value(),
        'purchasing_plan': []
    }
    
    # Get purchasing plan
    for t in range(data.T):
        row = [t + 1]
        for j in range(len(data.suppliers)):
            row.append(model.q[j, t].solution_value())
        result['purchasing_plan'].append(row)
    
    return result


def run_highs_model():
    """Chạy HiGHS model và thu thập kết quả"""
    print("\n" + "=" * 70)
    print("RUNNING HiGHS MODEL")
    print("=" * 70)
    
    data = SupplyChainData()
    model = SupplyChainModelHiGHS(data)
    
    model.create_variables()
    model.add_constraints()
    model.set_objective()
    
    start_time = time.time()
    model.solve()
    solve_time = time.time() - start_time
    
    # Extract solution
    result = {
        'solver': 'HiGHS',
        'solve_time': solve_time,
        'objective': model.solver.Objective().Value(),
        'purchasing_plan': []
    }
    
    # Get purchasing plan
    for t in range(data.T):
        row = [t + 1]
        for j in range(len(data.suppliers)):
            row.append(model.q[j, t].solution_value())
        result['purchasing_plan'].append(row)
    
    return result


def compare_results(scip_result, highs_result):
    """So sánh kết quả giữa 2 solvers"""
    print("\n" + "=" * 70)
    print("COMPARISON RESULTS")
    print("=" * 70)
    
    # Performance comparison
    print("\n📊 PERFORMANCE METRICS:")
    print(f"{'Metric':<25} {'SCIP':<20} {'HiGHS':<20}")
    print("-" * 65)
    print(f"{'Solve Time (s)':<25} {scip_result['solve_time']:<20.3f} {highs_result['solve_time']:<20.3f}")
    print(f"{'Objective Value':<25} {scip_result['objective']:<20.2f} {highs_result['objective']:<20.2f}")
    
    # Calculate difference
    diff = abs(scip_result['objective'] - highs_result['objective'])
    diff_pct = (diff / scip_result['objective']) * 100
    print(f"{'Absolute Difference':<25} {diff:<20.2f}")
    print(f"{'Percentage Difference':<25} {diff_pct:<20.6f}%")
    
    # Speed comparison
    if highs_result['solve_time'] < scip_result['solve_time']:
        speedup = (scip_result['solve_time'] / highs_result['solve_time'])
        print(f"\n⚡ HiGHS is {speedup:.2f}x FASTER than SCIP")
    else:
        speedup = (highs_result['solve_time'] / scip_result['solve_time'])
        print(f"\n⚡ SCIP is {speedup:.2f}x FASTER than HiGHS")
    
    # Purchasing plan comparison
    print("\n📦 PURCHASING PLAN COMPARISON:")
    print(f"\n{'Period':<10} {'Supplier':<15} {'SCIP':<15} {'HiGHS':<15} {'Diff':<10}")
    print("-" * 65)
    
    supplier_names = ['Sup1_Offer1', 'Sup1_Offer2', 'Sup2', 'Sup3']
    
    max_diff = 0
    for t in range(len(scip_result['purchasing_plan'])):
        scip_row = scip_result['purchasing_plan'][t]
        highs_row = highs_result['purchasing_plan'][t]
        
        for j in range(4):
            scip_val = scip_row[j + 1]
            highs_val = highs_row[j + 1]
            diff = abs(scip_val - highs_val)
            max_diff = max(max_diff, diff)
            
            period_str = f"Period {t+1}" if j == 0 else ""
            print(f"{period_str:<10} {supplier_names[j]:<15} {scip_val:<15.1f} {highs_val:<15.1f} {diff:<10.2f}")
        
        if t < len(scip_result['purchasing_plan']) - 1:
            print()
    
    # Verdict
    print("\n" + "=" * 70)
    print("🏆 VERDICT:")
    print("=" * 70)
    
    if diff_pct < 0.01:
        print(f"✅ Both solvers found IDENTICAL solutions (difference < 0.01%)")
    elif diff_pct < 0.1:
        print(f"✅ Solutions are virtually identical (difference = {diff_pct:.4f}%)")
    else:
        print(f"⚠️  Solutions differ by {diff_pct:.2f}%")
    
    if max_diff < 0.1:
        print(f"✅ Purchasing plans are IDENTICAL (max difference = {max_diff:.2f})")
    else:
        print(f"⚠️  Purchasing plans differ (max difference = {max_diff:.2f})")
    
    # Winner
    time_winner = "HiGHS" if highs_result['solve_time'] < scip_result['solve_time'] else "SCIP"
    cost_winner = "HiGHS" if highs_result['objective'] < scip_result['objective'] else "SCIP" if highs_result['objective'] > scip_result['objective'] else "TIE"
    
    print(f"\n⏱️  Faster Solver: {time_winner}")
    print(f"💰 Better Cost: {cost_winner}")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    print("🚀 Starting SCIP vs HiGHS Comparison...")
    print("Linear solver performance benchmark for Inventory MILP\n")
    
    # Run both models
    scip_result = run_scip_model()
    highs_result = run_highs_model()
    
    # Compare results
    compare_results(scip_result, highs_result)
    
    print("\n✅ Comparison complete!")
