from ortools.linear_solver import pywraplp
from data_loader import SupplyChainData 

class SupplyChainModel:
    def __init__(self, data):
        self.data = data
        self.solver = pywraplp.Solver.CreateSolver('SCIP')
        if not self.solver:
            raise Exception("SCIP backend not found.")
        self.infinity = self.solver.infinity()
        
        self.q, self.z = {}, {}
        self.x, self.w_prod = {}, {}
        self.y, self.w_trans = {}, {}
        self.i = {}
        self.s_price, self.r_price = {}, {}
        self.f_freight, self.y_freight = {}, {}

    def create_variables(self):
        print("Creating variables...")
        T = self.data.T
        for t in range(T):
            # Purchasing
            for j_idx, supplier in enumerate(self.data.suppliers):
                self.q[j_idx, t] = self.solver.NumVar(0, self.infinity, f'q_{j_idx}_{t}')
                self.z[j_idx, t] = self.solver.BoolVar(f'z_{j_idx}_{t}')
            # Production
            self.x[t] = self.solver.NumVar(0, self.infinity, f'x_{t}')
            self.w_prod[t] = self.solver.BoolVar(f'w_prod_{t}')
            # Inventory & Transport
            for k in range(1, self.data.K + 1):
                self.i[k, t] = self.solver.NumVar(0, self.data.inventory_capacity, f'i_{k}_{t}')
                if k < self.data.K:
                    self.y[k, t] = self.solver.NumVar(0, self.infinity, f'y_{k}_{t}')
                    self.w_trans[k, t] = self.solver.BoolVar(f'w_trans_{k}_{t}')

        # Pricing Scheme
        for j_idx, supplier in enumerate(self.data.suppliers):
            for g, _ in enumerate(supplier['price_intervals']):
                self.s_price[j_idx, g] = self.solver.BoolVar(f's_{j_idx}_{g}')
                self.r_price[j_idx, g] = self.solver.NumVar(0, self.infinity, f'r_{j_idx}_{g}')

        # Freight Rates (Chỉ tạo biến cho Stage 3->4, tức là k=3)
        transport_intervals = self.data.freight_actual 
        for t in range(T):
            for k in range(3, self.data.K): 
                for e, _ in enumerate(transport_intervals):
                    self.f_freight[k, t, e] = self.solver.BoolVar(f'f_{k}_{t}_{e}')
                    self.y_freight[k, t, e] = self.solver.NumVar(0, self.infinity, f'y_fr_{k}_{t}_{e}')

    def add_constraints(self):
        print("Adding constraints...")
        T = self.data.T
        
        # 1. SUPPLIER
        for j_idx, supplier in enumerate(self.data.suppliers):
            total_purchased_cumulative = 0
            for t in range(T):
                qty = self.q[j_idx, t]
                # Min Order & Max Order
                self.solver.Add(qty >= supplier['min_order'] * self.z[j_idx, t])
                self.solver.Add(qty <= self.data.global_max_order_size * self.z[j_idx, t])
                
                # Capacity
                total_purchased_cumulative += qty
                self.solver.Add(total_purchased_cumulative <= supplier['cumulative_capacity'][t])
                
                # CHẶN MUA (Logic Offer hết hạn)
                if t > 0:
                    added_cap = supplier['cumulative_capacity'][t] - supplier['cumulative_capacity'][t-1]
                    if added_cap <= 0: self.solver.Add(qty == 0)
                else:
                    if supplier['cumulative_capacity'][0] == 0: self.solver.Add(qty == 0)

            # Pricing Linearization
            total_qty_horizon = sum(self.q[j_idx, t] for t in range(T))
            intervals = supplier['price_intervals']
            self.solver.Add(sum(self.s_price[j_idx, g] for g in range(len(intervals))) <= 1)
            
            expr_qty = 0
            for g, interval in enumerate(intervals):
                lower = 0 if g == 0 else intervals[g-1]['max_q']
                width = interval['max_q'] - lower
                self.solver.Add(self.r_price[j_idx, g] <= width * self.s_price[j_idx, g])
                expr_qty += (self.s_price[j_idx, g] * lower + self.r_price[j_idx, g])
            self.solver.Add(total_qty_horizon == expr_qty)

        # 2. FLOW BALANCE
        for t in range(T):
            # Stage 1
            in_1 = sum(self.q[j, t] for j in range(len(self.data.suppliers)))
            prev_1 = self.data.initial_inventory[1] if t == 0 else self.i[1, t-1]
            self.solver.Add(in_1 + prev_1 == self.x[t] + self.i[1, t])
            self.solver.Add(self.x[t] <= self.data.prod_capacity[t] * self.w_prod[t])

            # Stage 2
            prev_2 = self.data.initial_inventory[2] if t == 0 else self.i[2, t-1]
            self.solver.Add(self.x[t] + prev_2 == self.y[2, t] + self.i[2, t])
            self.solver.Add(self.y[2, t] <= self.data.trans_capacity[t] * self.w_trans[2, t])

            # Stage 3 (Lead Time = 1)
            in_3 = 0
            lt = self.data.lead_times[(2,3)]
            if t >= lt: in_3 = self.y[2, t - lt]
            prev_3 = self.data.initial_inventory[3] if t == 0 else self.i[3, t-1]
            self.solver.Add(in_3 + prev_3 == self.y[3, t] + self.i[3, t])
            self.solver.Add(self.y[3, t] <= self.data.trans_capacity[t] * self.w_trans[3, t])

            # Stage 4
            prev_4 = self.data.initial_inventory[4] if t == 0 else self.i[4, t-1]
            self.solver.Add(self.y[3, t] + prev_4 == self.data.demand[t] + self.i[4, t])

        # 3. FREIGHT RATE (Chỉ K=3)
        intervals = self.data.freight_actual
        for t in range(T):
            for k in range(3, self.data.K):
                self.solver.Add(sum(self.y_freight[k, t, e] for e in range(len(intervals))) == self.y[k, t])
                self.solver.Add(sum(self.f_freight[k, t, e] for e in range(len(intervals))) <= 1)
                for e, iv in enumerate(intervals):
                    self.solver.Add(self.y_freight[k, t, e] >= iv['min'] * self.f_freight[k, t, e])
                    self.solver.Add(self.y_freight[k, t, e] <= iv['max'] * self.f_freight[k, t, e])

        # 4. ENDING INVENTORY TARGET
        self.solver.Add(self.i[4, T-1] == 100)
        for k in range(1, 4): self.solver.Add(self.i[k, T-1] == 0)

    def set_objective(self):
        print("Setting objective function...")
        T = self.data.T
        total = 0
        
        # 1. Purchasing
        for j_idx, supplier in enumerate(self.data.suppliers):
            intervals = supplier['price_intervals']
            for g, interval in enumerate(intervals):
                base_cost = 0
                for pg in range(g):
                    w = intervals[pg]['max_q'] - (0 if pg==0 else intervals[pg-1]['max_q'])
                    base_cost += w * intervals[pg]['price']
                total += (self.s_price[j_idx, g] * base_cost + self.r_price[j_idx, g] * interval['price'])
            
            is_selected = sum(self.s_price[j_idx, g] for g in range(len(intervals)))
            total += supplier['primary_cost'] * is_selected
            for t in range(T): total += supplier['secondary_cost'] * self.z[j_idx, t]

        # 2. Production
        for t in range(T):
            total += self.data.prod_fixed_cost[t] * self.w_prod[t]
            total += self.data.prod_var_cost[t] * self.x[t]

        # 3. Holding (CẬP NHẬT: Tính đủ các thành phần ẩn)
        # A. Phí tồn kho đầu kỳ (Initial Inventory tại Stage 4)
        total += 100 * 6 
        
        for t in range(T):
            # B. Tồn kho tại các kho (Node Inventory)
            for k in range(1, self.data.K + 1):
                total += self.data.holding_cost[t] * self.i[k, t]
            
            # C. Tồn kho dòng chảy (Flow Inventory)
            # Stage 2->3: Hàng đi trên đường (Transit), leadtime > 0
            lt_23 = self.data.lead_times.get((2, 3), 0)
            if lt_23 > 0:
                total += self.y[2, t] * self.data.holding_cost[t] * lt_23

            # Stage 1->2: Hàng luân chuyển nội bộ (WIP). 
            # Paper tính phí giữ hàng cho cả dòng này dù leadtime=0.
            total += self.y[1, t] * self.data.holding_cost[t] * 1

        # 4. Transportation (Chỉ tính cho k=3)
        transport_intervals = self.data.freight_actual
        for t in range(T):
            for k in range(3, self.data.K): 
                for e, iv in enumerate(transport_intervals):
                    total += iv['fixed_cost'] * self.f_freight[k, t, e]
                    total += iv['var_cost_per_unit'] * self.y_freight[k, t, e]

        self.solver.Minimize(total)

    def solve(self):
        print("Solving...")
        status = self.solver.Solve()
        if status == pywraplp.Solver.OPTIMAL:
            obj_val = self.solver.Objective().Value()
            print(f"Objective value = {obj_val}")

            # ========== BREAKDOWN CẬP NHẬT ==========
            T = self.data.T
            purch, prod, hold, transp = 0.0, 0.0, 0.0, 0.0

            # Purch
            for j_idx, supplier in enumerate(self.data.suppliers):
                intervals = supplier['price_intervals']
                for g, interval in enumerate(intervals):
                    base_cost = 0.0
                    for pg in range(g):
                        w = intervals[pg]['max_q'] - (0 if pg==0 else intervals[pg-1]['max_q'])
                        base_cost += w * intervals[pg]['price']
                    purch += (self.s_price[j_idx, g].solution_value() * base_cost +
                              self.r_price[j_idx, g].solution_value() * interval['price'])
                is_selected = sum(self.s_price[j_idx, g].solution_value() for g in range(len(intervals)))
                purch += supplier['primary_cost'] * is_selected
                for t in range(T): purch += supplier['secondary_cost'] * self.z[j_idx, t].solution_value()

            # Prod
            for t in range(T):
                prod += (self.data.prod_fixed_cost[t] * self.w_prod[t].solution_value() +
                         self.data.prod_var_cost[t] * self.x[t].solution_value())

            # Hold (Cập nhật logic hiển thị)
            hold += 100 * 6
            for t in range(T):
                for k in range(1, self.data.K + 1):
                    hold += self.data.holding_cost[t] * self.i[k, t].solution_value()
                # Transit Stage 2->3
                hold += self.y[2, t].solution_value() * self.data.holding_cost[t] * 1
                # WIP Stage 1->2
                hold += self.y[1, t].solution_value() * self.data.holding_cost[t] * 1

            # Transp (Chỉ k=3)
            intervals = self.data.freight_actual
            for t in range(T):
                for k in range(3, self.data.K):
                    for e, iv in enumerate(intervals):
                        transp += (iv['fixed_cost'] * self.f_freight[k, t, e].solution_value() +
                                   iv['var_cost_per_unit'] * self.y_freight[k, t, e].solution_value())

            print("-" * 30)
            print("COST BREAKDOWN:")
            print(f"  Purchasing:   {purch:,.0f}")
            print(f"  Production:   {prod:,.0f}")
            print(f"  Holding:      {hold:,.0f} (Target: ~13,450)")
            print(f"  Transport:    {transp:,.0f} (Target: ~10,374)")
            print(f"  Sum check:    {purch + prod + hold + transp:,.0f}")
            print("===================================")

            print("PURCHASING PLAN:")
            print(f"{'Per':<4} {'Sup1_1':<8} {'Sup1_2':<8} {'Sup2':<6} {'Sup3':<6}")
            for t in range(T):
                vals = [self.q[j, t].solution_value() for j in range(len(self.data.suppliers))]
                print(f"{t+1:<4} {vals[0]:<8.0f} {vals[1]:<8.0f} {vals[2]:<6.0f} {vals[3]:<6.0f}")
        else:
            print('No optimal solution found.')
            
if __name__ == "__main__":
    model = SupplyChainModel(SupplyChainData())
    model.create_variables()
    model.add_constraints()
    model.set_objective()
    model.solve()