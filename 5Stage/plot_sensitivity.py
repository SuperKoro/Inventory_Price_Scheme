"""
Script tạo biểu đồ cho Sensitivity Analysis:
1. Cost Breakdown Chart (Line chart với markers)
2. Cumulative Order Quantity Chart (Bar chart)
3. Production Split Chart (cho 5-stage với 2 sites)

Hỗ trợ cả 4-stage và 5-stage models
"""

import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
from data_loader import SupplyChainData
from dynamic_scm_milp import SupplyChainModel

def collect_data(num_stages=4):
    """
    Chạy model và thu thập dữ liệu cho tất cả m và cả 2 mode (Pm, Pmd)
    
    Args:
        num_stages: 4 hoặc 5 (số stage của model)
    """
    m_values = [1, 2, 3, 4] if num_stages == 4 else [1, 2]  # 5-stage chỉ test m=1,2
    results = {'Pm': {}, 'Pmd': {}}
    
    for mode in ['Pm', 'Pmd']:
        results[mode] = {
            'num_stages': num_stages,
            'm_values': m_values,
            'purchasing': [],
            'production': [],
            'holding': [],
            'transport': [],
            'total': [],
            'sup1_off1': [],  # Supplier 1 Offer 1
            'sup1_off2': [],  # Supplier 1 Offer 2
            'sup2': [],       # Supplier 2
            'sup3': []        # Supplier 3
        }
        
        # Thêm production split cho 5-stage
        if num_stages == 5:
            results[mode]['production_site1'] = []
            results[mode]['production_site2'] = []
        
        for m in m_values:
            print(f"Running {num_stages}-stage: m={m}, mode={mode}...")
            data = SupplyChainData(m=m, mode=mode, num_stages=num_stages)
            model = SupplyChainModel(data)
            model.create_variables()
            model.add_constraints()
            model.set_objective()
            
            if model.solve():
                # Lấy Cost Breakdown
                breakdown = model.get_cost_breakdown()
                results[mode]['purchasing'].append(breakdown['purchasing'])
                results[mode]['production'].append(breakdown['production'])
                results[mode]['holding'].append(breakdown['holding'])
                results[mode]['transport'].append(breakdown['transport'])
                results[mode]['total'].append(breakdown['total'])
                
                # Production split cho 5-stage
                if num_stages == 5:
                    results[mode]['production_site1'].append(breakdown['production_site1'])
                    results[mode]['production_site2'].append(breakdown['production_site2'])
                
                # Lấy Purchasing Plan và tính tổng cho mỗi supplier
                plan = model.get_purchasing_plan()
                T = data.T
                
                # Tổng mua từ mỗi supplier trong toàn bộ horizon
                sum_sup = [0, 0, 0, 0]  # [Sup1_Off1, Sup1_Off2, Sup2, Sup3]
                for t in range(T):
                    for j in range(4):
                        sum_sup[j] += plan[t][j]
                
                results[mode]['sup1_off1'].append(sum_sup[0])
                results[mode]['sup1_off2'].append(sum_sup[1])
                results[mode]['sup2'].append(sum_sup[2])
                results[mode]['sup3'].append(sum_sup[3])
            else:
                # Nếu không tìm được nghiệm
                keys = ['purchasing', 'production', 'holding', 'transport', 'total',
                       'sup1_off1', 'sup1_off2', 'sup2', 'sup3']
                if num_stages == 5:
                    keys.extend(['production_site1', 'production_site2'])
                for key in keys:
                    results[mode][key].append(0)
    
    return results

def plot_cost_breakdown(results, mode, ax=None):
    """
    Vẽ biểu đồ Cost Breakdown giống Figure trong paper
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(10, 7))
    
    m_values = results[mode]['m_values']
    num_stages = results[mode]['num_stages']
    
    # Plot các đường với markers
    ax.plot(m_values, results[mode]['purchasing'], 'b-d', label='Purchasing', 
            markersize=8, linewidth=2, markerfacecolor='white', markeredgewidth=2)
    ax.plot(m_values, results[mode]['production'], 'g-s', label='Production', 
            markersize=8, linewidth=2, markerfacecolor='green')
    ax.plot(m_values, results[mode]['transport'], 'y-*', label='Transportation', 
            markersize=10, linewidth=2, markerfacecolor='yellow', markeredgecolor='olive')
    ax.plot(m_values, results[mode]['holding'], 'm-o', label='Inventory', 
            markersize=8, linewidth=2, markerfacecolor='purple')
    ax.plot(m_values, results[mode]['total'], 'r-^', label='Total', 
            markersize=10, linewidth=2, markerfacecolor='lightcoral', markeredgecolor='red')
    
    # Cấu hình trục
    ax.set_xlabel('m', fontsize=14, fontweight='bold')
    ax.set_ylabel('Cost ($)', fontsize=12)
    ax.set_xticks(m_values)
    ax.set_xlim(0.5, max(m_values) + 0.5)
    
    # Thêm grid và legend
    ax.grid(True, alpha=0.3)
    ax.legend(loc='best', fontsize=10)
    ax.set_title(f'Cost Breakdown - {mode} ({num_stages}-Stage)', fontsize=14, fontweight='bold')
    
    # Hiển thị trục y dạng scientific notation
    ax.ticklabel_format(axis='y', style='scientific', scilimits=(4,4))
    
    return ax

def plot_production_split(results, mode, ax=None):
    """
    Vẽ biểu đồ phân tách production giữa Site 1 và Site 2 (chỉ cho 5-stage)
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(10, 7))
    
    if results[mode]['num_stages'] != 5:
        ax.text(0.5, 0.5, 'Production split only available for 5-stage', 
                ha='center', va='center', transform=ax.transAxes, fontsize=14)
        return ax
    
    m_values = results[mode]['m_values']
    x = np.array(m_values)
    width = 0.35
    
    # Vẽ stacked bar chart
    bars1 = ax.bar(x, results[mode]['production_site1'], width, 
                   label='Site 1 (Mfg1)', color='steelblue')
    bars2 = ax.bar(x, results[mode]['production_site2'], width, 
                   bottom=results[mode]['production_site1'],
                   label='Site 2 (Mfg2)', color='lightgreen')
    
    # Cấu hình trục
    ax.set_xlabel('m', fontsize=14, fontweight='bold')
    ax.set_ylabel('Production Cost ($)', fontsize=12)
    ax.set_xticks(m_values)
    ax.set_xlim(0.5, max(m_values) + 0.5)
    
    # Thêm legend và title
    ax.legend(loc='upper right', fontsize=10)
    ax.set_title(f'Production Split - {mode} (5-Stage)', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')
    
    return ax

def plot_purchasing_strategy(results, mode, ax=None):
    """
    Vẽ biểu đồ Cumulative Order Quantity theo supplier giống Figure 10
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(10, 7))
    
    m_values = results[mode]['m_values']
    num_stages = results[mode]['num_stages']
    x = np.array(m_values)
    width = 0.2  # Độ rộng mỗi cột
    
    # Vẽ các cột cho mỗi supplier
    bars1 = ax.bar(x - 1.5*width, results[mode]['sup1_off1'], width, 
                   label='Supplier 1 Offer 1', color='black')
    bars2 = ax.bar(x - 0.5*width, results[mode]['sup1_off2'], width, 
                   label='Supplier 1 Offer 2', color='gray')
    bars3 = ax.bar(x + 0.5*width, results[mode]['sup2'], width, 
                   label='Supplier 2', color='lightgray')
    bars4 = ax.bar(x + 1.5*width, results[mode]['sup3'], width, 
                   label='Supplier 3', color='white', edgecolor='black')
    
    # Cấu hình trục
    ax.set_xlabel('m', fontsize=14, fontweight='bold')
    ax.set_ylabel('Cumulative Order Quantity (units)', fontsize=12)
    ax.set_xticks(m_values)
    ax.set_xlim(0.5, max(m_values) + 0.5)
    
    # Thêm legend
    ax.legend(loc='upper right', fontsize=10)
    ax.set_title(f'Purchasing Strategies - {mode} ({num_stages}-Stage)', 
                 fontsize=12, fontweight='bold')
    
    # Thêm grid ngang
    ax.set_axisbelow(True)
    ax.grid(True, alpha=0.3, axis='y')
    
    return ax

def plot_total_cost_comparison(results, ax=None):
    """
    Vẽ biểu đồ so sánh Total Cost giữa Pm và Pmd
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(10, 7))
    
    m_values = results['Pm']['m_values']
    num_stages = results['Pm']['num_stages']
    
    # Plot đường Pm (xanh dương với markers tròn)
    ax.plot(m_values, results['Pm']['total'], 'b-o', label='Pm', 
            markersize=10, linewidth=2.5, markerfacecolor='white', 
            markeredgewidth=2, markeredgecolor='blue')
    
    # Plot đường Pmd (đỏ/cam với markers vuông)
    ax.plot(m_values, results['Pmd']['total'], 'r-s', label='Pmd', 
            markersize=10, linewidth=2.5, markerfacecolor='lightgreen',
            markeredgewidth=2, markeredgecolor='red')
    
    # Cấu hình trục
    ax.set_xlabel('m', fontsize=14, fontweight='bold')
    ax.set_ylabel('Cost ($)', fontsize=12)
    ax.set_xticks(m_values)
    ax.set_xlim(0.5, max(m_values) + 0.5)
    
    # Thêm grid và legend
    ax.grid(True, alpha=0.3)
    ax.legend(loc='upper right', fontsize=12)
    ax.set_title(f'Total Cost Comparison: Pm vs Pmd ({num_stages}-Stage)', 
                 fontsize=14, fontweight='bold')
    
    # Hiển thị trục y dạng scientific notation
    ax.ticklabel_format(axis='y', style='scientific', scilimits=(5,5))
    
    return ax

def create_all_plots(results, prefix=''):
    """
    Tạo tất cả các biểu đồ và lưu thành file
    
    Args:
        results: dữ liệu từ collect_data()
        prefix: tiền tố cho tên file (vd: '4stage_' hoặc '5stage_')
    """
    num_stages = results['Pm']['num_stages']
    
    # ===== Figure 1: Cost Breakdown cho Pm =====
    fig1, ax1 = plt.subplots(figsize=(10, 7))
    plot_cost_breakdown(results, 'Pm', ax1)
    fig1.tight_layout()
    fig1.savefig(f'{prefix}cost_breakdown_Pm.png', dpi=150, bbox_inches='tight')
    print(f"Saved: {prefix}cost_breakdown_Pm.png")
    
    # ===== Figure 2: Cost Breakdown cho Pmd =====
    fig2, ax2 = plt.subplots(figsize=(10, 7))
    plot_cost_breakdown(results, 'Pmd', ax2)
    fig2.tight_layout()
    fig2.savefig(f'{prefix}cost_breakdown_Pmd.png', dpi=150, bbox_inches='tight')
    print(f"Saved: {prefix}cost_breakdown_Pmd.png")
    
    # ===== Figure 3: Purchasing Strategy cho Pm =====
    fig3, ax3 = plt.subplots(figsize=(10, 7))
    plot_purchasing_strategy(results, 'Pm', ax3)
    fig3.tight_layout()
    fig3.savefig(f'{prefix}purchasing_strategy_Pm.png', dpi=150, bbox_inches='tight')
    print(f"Saved: {prefix}purchasing_strategy_Pm.png")
    
    # ===== Figure 4: Purchasing Strategy cho Pmd =====
    fig4, ax4 = plt.subplots(figsize=(10, 7))
    plot_purchasing_strategy(results, 'Pmd', ax4)
    fig4.tight_layout()
    fig4.savefig(f'{prefix}purchasing_strategy_Pmd.png', dpi=150, bbox_inches='tight')
    print(f"Saved: {prefix}purchasing_strategy_Pmd.png")
    
    # ===== Figure 5: Production Split (chỉ cho 5-stage) =====
    if num_stages == 5:
        fig5, (ax5a, ax5b) = plt.subplots(1, 2, figsize=(16, 7))
        plot_production_split(results, 'Pm', ax5a)
        plot_production_split(results, 'Pmd', ax5b)
        fig5.suptitle('Production Split: Site 1 vs Site 2 (5-Stage)', 
                     fontsize=16, fontweight='bold')
        fig5.tight_layout()
        fig5.savefig(f'{prefix}production_split.png', dpi=150, bbox_inches='tight')
        print(f"Saved: {prefix}production_split.png")
    
    # ===== Figure 6: So sánh Pm vs Pmd (Cost Breakdown) =====
    fig6, (ax6a, ax6b) = plt.subplots(1, 2, figsize=(16, 7))
    plot_cost_breakdown(results, 'Pm', ax6a)
    plot_cost_breakdown(results, 'Pmd', ax6b)
    fig6.suptitle(f'Cost Breakdown Comparison: Pm vs Pmd ({num_stages}-Stage)', 
                  fontsize=16, fontweight='bold')
    fig6.tight_layout()
    fig6.savefig(f'{prefix}cost_breakdown_comparison.png', dpi=150, bbox_inches='tight')
    print(f"Saved: {prefix}cost_breakdown_comparison.png")
    
    # ===== Figure 7: So sánh Pm vs Pmd (Purchasing Strategy) =====
    fig7, (ax7a, ax7b) = plt.subplots(1, 2, figsize=(16, 7))
    plot_purchasing_strategy(results, 'Pm', ax7a)
    plot_purchasing_strategy(results, 'Pmd', ax7b)
    fig7.suptitle(f'Purchasing Strategy Comparison: Pm vs Pmd ({num_stages}-Stage)', 
                  fontsize=16, fontweight='bold')
    fig7.tight_layout()
    fig7.savefig(f'{prefix}purchasing_strategy_comparison.png', dpi=150, bbox_inches='tight')
    print(f"Saved: {prefix}purchasing_strategy_comparison.png")
    
    # ===== Figure 8: Total Cost Comparison (Pm vs Pmd trên cùng 1 đồ thị) =====
    fig8, ax8 = plt.subplots(figsize=(10, 7))
    plot_total_cost_comparison(results, ax8)
    fig8.tight_layout()
    fig8.savefig(f'{prefix}total_cost_Pm_vs_Pmd.png', dpi=150, bbox_inches='tight')
    print(f"Saved: {prefix}total_cost_Pm_vs_Pmd.png")

def print_summary(results):
    """
    In tóm tắt dữ liệu
    """
    num_stages = results['Pm']['num_stages']
    print("\n" + "="*80)
    print(f"{num_stages}-STAGE MODEL SUMMARY DATA")
    print("="*80)
    
    for mode in ['Pm', 'Pmd']:
        print(f"\n--- {mode} ---")
        print(f"{'m':<5} {'Purchasing':>12} {'Production':>12} {'Holding':>12} {'Transport':>12} {'Total':>12}")
        print("-"*70)
        for i, m in enumerate(results[mode]['m_values']):
            print(f"{m:<5} {results[mode]['purchasing'][i]:>12,.0f} "
                  f"{results[mode]['production'][i]:>12,.0f} "
                  f"{results[mode]['holding'][i]:>12,.0f} "
                  f"{results[mode]['transport'][i]:>12,.0f} "
                  f"{results[mode]['total'][i]:>12,.0f}")
        
        # Production split cho 5-stage
        if num_stages == 5:
            print(f"\n{'m':<5} {'Site 1':>12} {'Site 2':>12} {'Total Prod':>12}")
            print("-"*50)
            for i, m in enumerate(results[mode]['m_values']):
                print(f"{m:<5} {results[mode]['production_site1'][i]:>12,.0f} "
                      f"{results[mode]['production_site2'][i]:>12,.0f} "
                      f"{results[mode]['production'][i]:>12,.0f}")
        
        print(f"\n{'m':<5} {'Sup1_Off1':>12} {'Sup1_Off2':>12} {'Sup2':>12} {'Sup3':>12} {'Total':>12}")
        print("-"*70)
        for i, m in enumerate(results[mode]['m_values']):
            total_qty = (results[mode]['sup1_off1'][i] + results[mode]['sup1_off2'][i] + 
                        results[mode]['sup2'][i] + results[mode]['sup3'][i])
            print(f"{m:<5} {results[mode]['sup1_off1'][i]:>12,.0f} "
                  f"{results[mode]['sup1_off2'][i]:>12,.0f} "
                  f"{results[mode]['sup2'][i]:>12,.0f} "
                  f"{results[mode]['sup3'][i]:>12,.0f} "
                  f"{total_qty:>12,.0f}")

if __name__ == "__main__":
    import sys
    
    # Cho phép chọn stage từ command line: python plot_sensitivity.py 5
    if len(sys.argv) > 1:
        num_stages = int(sys.argv[1])
    else:
        # Mặc định chạy cả 4-stage và 5-stage
        num_stages = None
    
    if num_stages is None:
        # Chạy cả 2 loại
        for K in [4, 5]:
            print("\n" + "="*80)
            print(f"PROCESSING {K}-STAGE MODEL")
            print("="*80)
            
            print(f"\nCollecting data from {K}-stage models...")
            results = collect_data(num_stages=K)
            
            print_summary(results)
            
            print(f"\nGenerating plots for {K}-stage...")
            create_all_plots(results, prefix=f'{K}stage_')
            
            print(f"\n{'='*80}")
            print(f"DONE {K}-STAGE! All plots have been saved with prefix '{K}stage_'")
            print("="*80)
    else:
        # Chạy 1 loại cụ thể
        print(f"\nCollecting data from {num_stages}-stage models...")
        results = collect_data(num_stages=num_stages)
        
        print_summary(results)
        
        print(f"\nGenerating plots for {num_stages}-stage...")
        create_all_plots(results, prefix=f'{num_stages}stage_')
        
        print("\n" + "="*80)
        print(f"DONE! All {num_stages}-stage plots have been saved.")
        print("="*80)
