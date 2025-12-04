from ortools.linear_solver import pywraplp
from data_loader import SupplyChainData


def create_solver():
    """Khởi tạo SCIP solver"""
    solver = pywraplp.Solver.CreateSolver('SCIP')
    if not solver:
        raise Exception("SCIP backend not found.")
    return solver


def create_variables(solver, data):
    """
    Tạo tất cả decision variables
    Returns: dict chứa tất cả variables
    """
    print("Creating variables...")
    T = data.T
    infinity = solver.infinity()
    
    # Khởi tạo dictionaries để lưu variables
    q, z = {}, {}
    x, w_prod = {}, {}
    y, w_trans = {}, {}
    i = {}
    s_price, r_price = {}, {}
    f_freight, y_freight = {}, {}
    
    for t in range(T):
        # Purchasing variables
        for j_idx, supplier in enumerate(data.suppliers):
            q[j_idx, t] = solver.NumVar(0, infinity, f'q_{j_idx}_{t}')
            z[j_idx, t] = solver.BoolVar(f'z_{j_idx}_{t}')
        
        # Production variables
        x[t] = solver.NumVar(0, infinity, f'x_{t}')
        w_prod[t] = solver.BoolVar(f'w_prod_{t}')
        
        # Inventory & Transport variables
        for k in range(1, data.K + 1):
            i[k, t] = solver.NumVar(0, data.inventory_capacity, f'i_{k}_{t}')
            if k < data.K:
                y[k, t] = solver.NumVar(0, infinity, f'y_{k}_{t}')
                w_trans[k, t] = solver.BoolVar(f'w_trans_{k}_{t}')

    # Pricing variables
    for j_idx, supplier in enumerate(data.suppliers):
        for g, _ in enumerate(supplier['price_intervals']):
            s_price[j_idx, g] = solver.BoolVar(f's_{j_idx}_{g}')
            r_price[j_idx, g] = solver.NumVar(0, infinity, f'r_{j_idx}_{g}')
    
    # Freight variables
    transport_intervals = data.freight_actual
    for t in range(T):
        for k in range(3, data.K):
            for e, _ in enumerate(transport_intervals):
                f_freight[k, t, e] = solver.BoolVar(f'f_{k}_{t}_{e}')
                y_freight[k, t, e] = solver.NumVar(0, infinity, f'y_fr_{k}_{t}_{e}')
    
    # Return tất cả variables trong 1 dict
    return {
        'q': q, 'z': z,
        'x': x, 'w_prod': w_prod,
        'y': y, 'w_trans': w_trans,
        'i': i,
        's_price': s_price, 'r_price': r_price,
        'f_freight': f_freight, 'y_freight': y_freight
    }


def add_supplier_constraints(solver, data, vars):
    """Thêm ràng buộc nhà cung cấp (Eq. 16-26)"""
    T = data.T
    q = vars['q']
    z = vars['z']
    s_price = vars['s_price']
    r_price = vars['r_price']
    
    for j_idx, supplier in enumerate(data.suppliers):
        total_purchased_cumulative = 0
        
        for t in range(T):
            qty = q[j_idx, t]
            
            # Eq. (18), (19): Order size constraints
            solver.Add(qty >= supplier['min_order'] * z[j_idx, t])
            solver.Add(qty <= data.global_max_order_size * z[j_idx, t])
            
            # Eq. (16), (17): Cumulative capacity
            total_purchased_cumulative += qty
            solver.Add(total_purchased_cumulative <= supplier['cumulative_capacity'][t])
            
            # Logic bổ sung: Chặn mua nếu offer hết hạn
            if t > 0:
                added_cap = supplier['cumulative_capacity'][t] - supplier['cumulative_capacity'][t-1]
                if added_cap <= 0:
                    solver.Add(qty == 0)
            else:
                if supplier['cumulative_capacity'][0] == 0:
                    solver.Add(qty == 0)
        
        # Eq. (21)-(26): Price break linearization
        total_qty_horizon = sum(q[j_idx, t] for t in range(T))
        intervals = supplier['price_intervals']
        
        # Eq. (21): Chọn tối đa 1 khoảng giá
        solver.Add(sum(s_price[j_idx, g] for g in range(len(intervals))) <= 1)
        
        # Eq. (22), (23): Quantity = sum of intervals
        expr_qty = 0
        for g, interval in enumerate(intervals):
            lower = 0 if g == 0 else intervals[g-1]['max_q']
            width = interval['max_q'] - lower
            solver.Add(r_price[j_idx, g] <= width * s_price[j_idx, g])
            expr_qty += (s_price[j_idx, g] * lower + r_price[j_idx, g])
        
        solver.Add(total_qty_horizon == expr_qty)


def add_flow_balance_constraints(solver, data, vars):
    """Thêm ràng buộc cân bằng dòng chảy (Eq. 27-30)"""
    T = data.T
    q = vars['q']
    x = vars['x']
    y = vars['y']
    i = vars['i']
    w_prod = vars['w_prod']
    w_trans = vars['w_trans']
    
    for t in range(T):
        # Eq. (27): Stage 1 - Manufacturing
        in_1 = sum(q[j, t] for j in range(len(data.suppliers)))
        prev_1 = data.initial_inventory[1] if t == 0 else i[1, t-1]
        solver.Add(in_1 + prev_1 == x[t] + i[1, t])
        
        # Eq. (31): Production capacity
        solver.Add(x[t] <= data.prod_capacity[t] * w_prod[t])
        
        # Eq. (28): Stage 2 - Local Warehouse
        prev_2 = data.initial_inventory[2] if t == 0 else i[2, t-1]
        solver.Add(x[t] + prev_2 == y[2, t] + i[2, t])
        
        # Eq. (32): Transportation capacity
        solver.Add(y[2, t] <= data.trans_capacity[t] * w_trans[2, t])
        
        # Eq. (29): Stage 3 - Regional Warehouse (với lead time)
        in_3 = 0
        lt = data.lead_times[(2, 3)]
        if t >= lt:
            in_3 = y[2, t - lt]
        prev_3 = data.initial_inventory[3] if t == 0 else i[3, t-1]
        solver.Add(in_3 + prev_3 == y[3, t] + i[3, t])
        solver.Add(y[3, t] <= data.trans_capacity[t] * w_trans[3, t])
        
        # Eq. (30): Stage 4 - Customer
        prev_4 = data.initial_inventory[4] if t == 0 else i[4, t-1]
        solver.Add(y[3, t] + prev_4 == data.demand[t] + i[4, t])


def add_freight_constraints(solver, data, vars):
    """Thêm ràng buộc cước vận chuyển (Eq. 34-37)"""
    T = data.T
    y = vars['y']
    f_freight = vars['f_freight']
    y_freight = vars['y_freight']
    
    intervals = data.freight_actual
    
    for t in range(T):
        for k in range(3, data.K):
            # Eq. (36): Tổng quantity trong các khoảng
            solver.Add(sum(y_freight[k, t, e] for e in range(len(intervals))) == y[k, t])
            
            # Eq. (37): Chọn tối đa 1 khoảng cước
            solver.Add(sum(f_freight[k, t, e] for e in range(len(intervals))) <= 1)
            
            for e, iv in enumerate(intervals):
                # Eq. (35): Lower bound
                solver.Add(y_freight[k, t, e] >= iv['min'] * f_freight[k, t, e])
                
                # Eq. (34): Upper bound
                solver.Add(y_freight[k, t, e] <= iv['max'] * f_freight[k, t, e])


def add_ending_inventory_constraints(solver, data, vars):
    """Ràng buộc tồn kho cuối kỳ (Eq. 33 + bổ sung)"""
    T = data.T
    i = vars['i']
    
    # Eq. (33): Inventory capacity (đã enforce trong domain)
    # Bổ sung: Target inventory cuối cùng
    solver.Add(i[4, T-1] == 100)  # Stage 4 phải còn 100 units
    for k in range(1, 4):
        solver.Add(i[k, T-1] == 0)  # Các stage khác về 0


def set_objective(solver, data, vars):
    """
    Định nghĩa hàm mục tiêu (Eq. 15)
    Min Z = (1) + (2) + (3) + (4) + (5)
    """
    print("Setting objective function...")
    T = data.T
    total = 0
    
    q = vars['q']
    z = vars['z']
    x = vars['x']
    y = vars['y']
    i = vars['i']
    w_prod = vars['w_prod']
    s_price = vars['s_price']
    r_price = vars['r_price']
    f_freight = vars['f_freight']
    y_freight = vars['y_freight']
    
    # (1) + (2): Purchasing & Ordering Costs
    for j_idx, supplier in enumerate(data.suppliers):
        intervals = supplier['price_intervals']
        
        # (1) Purchasing cost
        for g, interval in enumerate(intervals):
            base_cost = 0
            for pg in range(g):
                w = intervals[pg]['max_q'] - (0 if pg==0 else intervals[pg-1]['max_q'])
                base_cost += w * intervals[pg]['price']
            total += (s_price[j_idx, g] * base_cost + r_price[j_idx, g] * interval['price'])
        
        # (2) Ordering cost
        is_selected = sum(s_price[j_idx, g] for g in range(len(intervals)))
        total += supplier['primary_cost'] * is_selected
        for t in range(T):
            total += supplier['secondary_cost'] * z[j_idx, t]
    
    # (3): Production Cost
    for t in range(T):
        total += data.prod_fixed_cost[t] * w_prod[t]
        total += data.prod_var_cost[t] * x[t]
    
    # (4): Holding Cost
    for t in range(T):
        # Node inventory
        for k in range(1, data.K + 1):
            total += data.holding_cost[t] * i[k, t]
        
        # In-transit inventory (K_D = {2, 3})
        for k in [2, 3]:
            total += y[k, t] * data.holding_cost[t]
    
    # (5): Transportation Cost
    transport_intervals = data.freight_actual
    for t in range(T):
        for k in range(3, data.K):
            for e, iv in enumerate(transport_intervals):
                total += iv['fixed_cost'] * f_freight[k, t, e]
                total += iv['var_cost_per_unit'] * y_freight[k, t, e]
    
    solver.Minimize(total)


def solve_and_display(solver, data, vars):
    """Giải model và hiển thị kết quả"""
    print("Solving...")
    status = solver.Solve()
    
    if status == pywraplp.Solver.OPTIMAL:
        obj_val = solver.Objective().Value()
        print(f"Objective value = {obj_val}")
        
        # Cost breakdown
        T = data.T
        q = vars['q']
        z = vars['z']
        x = vars['x']
        y = vars['y']
        i = vars['i']
        w_prod = vars['w_prod']
        s_price = vars['s_price']
        r_price = vars['r_price']
        f_freight = vars['f_freight']
        y_freight = vars['y_freight']
        
        purch, prod, hold, transp = 0.0, 0.0, 0.0, 0.0
        
        # Calculate each cost component
        for j_idx, supplier in enumerate(data.suppliers):
            intervals = supplier['price_intervals']
            for g, interval in enumerate(intervals):
                base_cost = 0.0
                for pg in range(g):
                    w = intervals[pg]['max_q'] - (0 if pg==0 else intervals[pg-1]['max_q'])
                    base_cost += w * intervals[pg]['price']
                purch += (s_price[j_idx, g].solution_value() * base_cost +
                         r_price[j_idx, g].solution_value() * interval['price'])
            is_selected = sum(s_price[j_idx, g].solution_value() for g in range(len(intervals)))
            purch += supplier['primary_cost'] * is_selected
            for t in range(T):
                purch += supplier['secondary_cost'] * z[j_idx, t].solution_value()
        
        for t in range(T):
            prod += (data.prod_fixed_cost[t] * w_prod[t].solution_value() +
                    data.prod_var_cost[t] * x[t].solution_value())
        
        for t in range(T):
            for k in range(1, data.K + 1):
                hold += data.holding_cost[t] * i[k, t].solution_value()
            for k in [2, 3]:
                hold += y[k, t].solution_value() * data.holding_cost[t]
        
        intervals = data.freight_actual
        for t in range(T):
            for k in range(3, data.K):
                for e, iv in enumerate(intervals):
                    transp += (iv['fixed_cost'] * f_freight[k, t, e].solution_value() +
                              iv['var_cost_per_unit'] * y_freight[k, t, e].solution_value())
        
        print("-" * 30)
        print("COST BREAKDOWN:")
        print(f"  Purchasing:   {purch:,.0f}")
        print(f"  Production:   {prod:,.0f}")
        print(f"  Holding:      {hold:,.0f}")
        print(f"  Transport:    {transp:,.0f}")
        print(f"  Sum check:    {purch + prod + hold + transp:,.0f}")
        print("=" * 30)
        
        print("\nPURCHASING PLAN:")
        print(f"{'Per':<4} {'Sup1_1':<8} {'Sup1_2':<8} {'Sup2':<6} {'Sup3':<6}")
        for t in range(T):
            vals = [q[j, t].solution_value() for j in range(len(data.suppliers))]
            print(f"{t+1:<4} {vals[0]:<8.0f} {vals[1]:<8.0f} {vals[2]:<6.0f} {vals[3]:<6.0f}")
    else:
        print('No optimal solution found.')


# ============================================================
# MAIN FUNCTION - Entry point
# ============================================================
def main():
    """Main procedural workflow"""
    print("="*60)
    print("PROCEDURAL VERSION - Inventory MILP Model")
    print("="*60)
    
    # 1. Load data
    data = SupplyChainData()
    
    # 2. Create solver
    solver = create_solver()
    
    # 3. Create variables
    vars = create_variables(solver, data)
    
    # 4. Add constraints
    add_supplier_constraints(solver, data, vars)
    add_flow_balance_constraints(solver, data, vars)
    add_freight_constraints(solver, data, vars)
    add_ending_inventory_constraints(solver, data, vars)
    
    # 5. Set objective
    set_objective(solver, data, vars)
    
    # 6. Solve and display
    solve_and_display(solver, data, vars)
    
    print("\n✅ Procedural version completed!")


if __name__ == "__main__":
    main()
