from ortools.linear_solver import pywraplp
from data_loader import SupplyChainData 

class SupplyChainModel:
    def __init__(self, data):
        self.data = data
        self.solver = pywraplp.Solver.CreateSolver('SCIP')
        if not self.solver:
            raise Exception("SCIP backend not found.")
        self.infinity = self.solver.infinity()
        
        # Khai báo biến
        self.q, self.z = {}, {}
        self.x, self.w_prod = {}, {}
        self.w_prod_group = {} # Setup cho nhóm kỳ gốc site 1
        
        # Production site 2 (stage 3) - chỉ dùng cho K=5
        self.x2, self.w_prod2 = {}, {}
        self.w_prod2_group = {}
        
        self.y, self.w_trans = {}, {}
        self.i = {}
        self.s_price, self.r_price = {}, {}
        self.f_freight, self.y_freight = {}, {}

    def create_variables(self):
        print("Creating variables...")
        T = self.data.T 
        
        # 1. Variables theo kỳ con (Sub-periods)
        for t in range(T):
            # Purchasing
            for j_idx, supplier in enumerate(self.data.suppliers):
                self.q[j_idx, t] = self.solver.NumVar(0, self.infinity, f'q_{j_idx}_{t}')
                self.z[j_idx, t] = self.solver.BoolVar(f'z_{j_idx}_{t}')
            
            # Production Site 1 (Sub-period)
            self.x[t] = self.solver.NumVar(0, self.infinity, f'x_{t}')
            self.w_prod[t] = self.solver.BoolVar(f'w_prod_{t}')
            
            # Production Site 2 (Sub-period) - luôn tạo nhưng chỉ dùng khi K=5
            self.x2[t] = self.solver.NumVar(0, self.infinity, f'x2_{t}')
            self.w_prod2[t] = self.solver.BoolVar(f'w_prod2_{t}')
            
            # Inventory & Transport
            for k in range(1, self.data.K + 1):
                self.i[k, t] = self.solver.NumVar(0, self.data.inventory_capacity, f'i_{k}_{t}')    
                if k < self.data.K:
                    self.y[k, t] = self.solver.NumVar(0, self.infinity, f'y_{k}_{t}')
                    self.w_trans[k, t] = self.solver.BoolVar(f'w_trans_{k}_{t}')

        # 2. Variable theo kỳ gốc (Base Period) cho Production Setup
        for t_base in range(self.data.base_T):
            self.w_prod_group[t_base] = self.solver.BoolVar(f'w_prod_group_{t_base}')
            self.w_prod2_group[t_base] = self.solver.BoolVar(f'w_prod2_group_{t_base}')

        # 3. Pricing Scheme
        for j_idx, supplier in enumerate(self.data.suppliers):
            for g, _ in enumerate(supplier['price_intervals']):
                self.s_price[j_idx, g] = self.solver.BoolVar(f's_{j_idx}_{g}')
                self.r_price[j_idx, g] = self.solver.NumVar(0, self.infinity, f'r_{j_idx}_{g}')

        # 4. Freight Rates - điều chỉnh theo K
        transport_intervals = self.data.freight_actual 
        for t in range(T):
            # Cho 4-stage: freight ở leg 3 (stage 3->4)
            # Cho 5-stage: freight ở leg 2,4 (stage 2->3, 4->5)
            if self.data.K == 4:
                freight_legs = [3]
            elif self.data.K == 5:
                freight_legs = [2, 4]
            else:
                freight_legs = []
            
            for k in freight_legs:
                for e, _ in enumerate(transport_intervals):
                    self.f_freight[k, t, e] = self.solver.BoolVar(f'f_{k}_{t}_{e}')
                    self.y_freight[k, t, e] = self.solver.NumVar(0, self.infinity, f'y_fr_{k}_{t}_{e}')
        
        
        print(f"Total variables: {self.solver.NumVariables()}")

    def add_constraints(self):
        print("Adding constraints...")
        T = self.data.T
        m = self.data.m
        
        # 1. SUPPLIER
        for j_idx, supplier in enumerate(self.data.suppliers):
            total_purchased_cumulative = 0
            for t in range(T):
                qty = self.q[j_idx, t]
                self.solver.Add(qty >= supplier['min_order'] * self.z[j_idx, t])
                self.solver.Add(qty <= self.data.global_max_order_size * self.z[j_idx, t])
                
                total_purchased_cumulative += qty
                self.solver.Add(total_purchased_cumulative <= supplier['cumulative_capacity'][t])
                
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

        # 2. PRODUCTION CONSTRAINTS - Site 1
        for t_base in range(self.data.base_T):
            start_sub = t_base * m
            end_sub = (t_base + 1) * m
            base_cap = self.data.prod_capacity[start_sub] 
            
            cumulative_prod = 0
            for t_sub in range(start_sub, end_sub):
                cumulative_prod += self.x[t_sub]
                self.solver.Add(self.x[t_sub] <= base_cap * self.w_prod[t_sub])
            
            self.solver.Add(cumulative_prod <= base_cap)

            sum_w_sub = sum(self.w_prod[t_sub] for t_sub in range(start_sub, end_sub))
            self.solver.Add(sum_w_sub <= m * self.w_prod_group[t_base])
            for t_sub in range(start_sub, end_sub):
                self.solver.Add(self.w_prod[t_sub] <= self.w_prod_group[t_base])
        
        # 2b. PRODUCTION CONSTRAINTS - Site 2 (chỉ cho K=5)
        if self.data.K == 5:
            for t_base in range(self.data.base_T):
                start_sub = t_base * m
                end_sub = (t_base + 1) * m
                base_cap2 = self.data.prod2_capacity[start_sub]
                
                cumulative_prod2 = 0
                for t_sub in range(start_sub, end_sub):
                    cumulative_prod2 += self.x2[t_sub]
                    self.solver.Add(self.x2[t_sub] <= base_cap2 * self.w_prod2[t_sub])
                
                self.solver.Add(cumulative_prod2 <= base_cap2)

                sum_w_sub2 = sum(self.w_prod2[t_sub] for t_sub in range(start_sub, end_sub))
                self.solver.Add(sum_w_sub2 <= m * self.w_prod2_group[t_base])
                for t_sub in range(start_sub, end_sub):
                    self.solver.Add(self.w_prod2[t_sub] <= self.w_prod2_group[t_base])
        else:
            # Nếu không phải 5-stage, fix x2 = 0
            for t in range(T):
                self.solver.Add(self.x2[t] == 0)

        # 3. FLOW BALANCE - rẽ nhánh theo K
        for t in range(T):
            num_sup = len(self.data.suppliers)
            
            if self.data.K == 4:
                # ===== 4-STAGE FLOW (giữ nguyên logic cũ) =====
                # Stage 1
                in_1 = sum(self.q[j, t] for j in range(num_sup))
                prev_1 = self.data.initial_inventory[1] if t == 0 else self.i[1, t-1]
                self.solver.Add(in_1 + prev_1 == self.x[t] + self.i[1, t])

                # Stage 2
                prev_2 = self.data.initial_inventory[2] if t == 0 else self.i[2, t-1]
                self.solver.Add(self.x[t] + prev_2 == self.y[2, t] + self.i[2, t])
                self.solver.Add(self.y[2, t] <= self.data.trans_capacity[t] * self.w_trans[2, t])

                # Stage 3 (Lead Time)
                in_3 = 0
                lt = self.data.lead_times[(2,3)]
                if t >= lt: in_3 = self.y[2, t - lt]
                prev_3 = self.data.initial_inventory[3] if t == 0 else self.i[3, t-1]
                self.solver.Add(in_3 + prev_3 == self.y[3, t] + self.i[3, t])
                self.solver.Add(self.y[3, t] <= self.data.trans_capacity[t] * self.w_trans[3, t])

                # Stage 4
                prev_4 = self.data.initial_inventory[4] if t == 0 else self.i[4, t-1]
                self.solver.Add(self.y[3, t] + prev_4 == self.data.demand[t] + self.i[4, t])
            
            elif self.data.K == 5:
                # ===== 5-STAGE FLOW =====
                # Stage 1 - Mfg1
                in_1 = sum(self.q[j, t] for j in range(num_sup))
                prev_1 = self.data.initial_inventory[1] if t == 0 else self.i[1, t-1]
                self.solver.Add(in_1 + prev_1 == self.x[t] + self.i[1, t])

                # Stage 2 - WH1
                prev_2 = self.data.initial_inventory[2] if t == 0 else self.i[2, t-1]
                self.solver.Add(self.x[t] + prev_2 == self.y[2, t] + self.i[2, t])
                self.solver.Add(self.y[2, t] <= self.data.trans_capacity[t] * self.w_trans[2, t])

                # Stage 3 - Mfg2 (Site 2 CHỈ xử lý bán thành phẩm từ Site 1)
                lt_23 = self.data.lead_times[(2, 3)]
                in_3 = 0
                if t >= lt_23:
                    in_3 = self.y[2, t - lt_23]
                prev_3 = self.data.initial_inventory[3] if t == 0 else self.i[3, t-1]
                
                # CONSTRAINT: Site 2 production output = shipment to WH2
                self.solver.Add(self.y[3, t] == self.x2[t])
                
                # FLOW BALANCE: Input (từ WH1) = Production consumed + Inventory
                # Site 2 chỉ có thể sản xuất khi có bán thành phẩm từ Site 1
                self.solver.Add(in_3 + prev_3 == self.x2[t] + self.i[3, t])
                self.solver.Add(self.y[3, t] <= self.data.trans_capacity[t] * self.w_trans[3, t])

                # Stage 4 - WH2
                lt_34 = self.data.lead_times.get((3, 4), 0)
                in_4 = 0
                if t >= lt_34:
                    in_4 = self.y[3, t - lt_34]
                prev_4 = self.data.initial_inventory[4] if t == 0 else self.i[4, t-1]
                self.solver.Add(in_4 + prev_4 == self.y[4, t] + self.i[4, t])
                self.solver.Add(self.y[4, t] <= self.data.trans_capacity[t] * self.w_trans[4, t])

                # Stage 5 - Customer
                lt_45 = self.data.lead_times.get((4, 5), 0)
                in_5 = 0
                if t >= lt_45:
                    in_5 = self.y[4, t - lt_45]
                prev_5 = self.data.initial_inventory[5] if t == 0 else self.i[5, t-1]
                self.solver.Add(in_5 + prev_5 == self.data.demand[t] + self.i[5, t])

        # 4. FREIGHT RATE - điều chỉnh theo K
        intervals = self.data.freight_actual
        for t in range(T):
            if self.data.K == 4:
                freight_legs = [3]
            elif self.data.K == 5:
                freight_legs = [2, 4]
            else:
                freight_legs = []
            
            for k in freight_legs:
                self.solver.Add(sum(self.y_freight[k, t, e] for e in range(len(intervals))) == self.y[k, t])
                self.solver.Add(sum(self.f_freight[k, t, e] for e in range(len(intervals))) <= 1)
                for e, iv in enumerate(intervals):
                    self.solver.Add(self.y_freight[k, t, e] >= iv['min'] * self.f_freight[k, t, e])
                    self.solver.Add(self.y_freight[k, t, e] <= iv['max'] * self.f_freight[k, t, e])

        # 5. ENDING INVENTORY TARGET - generic cho K stages
        final_stage = self.data.K
        self.solver.Add(self.i[final_stage, T-1] == 100)
        for k in range(1, final_stage):
            self.solver.Add(self.i[k, T-1] == 0)
        
        print(f"Total constraints: {self.solver.NumConstraints()}")

    def set_objective(self):
        print("Setting objective function...")
        T = self.data.T
        m = self.data.m
        total = 0
        
        # 1. Purchasing Cost
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
            
            for t in range(T): 
                total += supplier['secondary_cost'] * self.z[j_idx, t]

        # 2. Production Cost - Site 1
        for t_base in range(self.data.base_T):
            fixed_cost = self.data.prod_fixed_cost[t_base * m]
            total += fixed_cost * self.w_prod_group[t_base]
            
        for t in range(T):
            total += self.data.prod_var_cost[t] * self.x[t]
        
        # 2b. Production Cost - Site 2 (chỉ cho K=5)
        if self.data.K == 5:
            for t_base in range(self.data.base_T):
                fixed_cost2 = self.data.prod2_fixed_cost[t_base * m]
                total += fixed_cost2 * self.w_prod2_group[t_base]
            
            for t in range(T):
                total += self.data.prod2_var_cost[t] * self.x2[t]

        # 3. Holding Cost
        for t in range(T):
            # Tồn kho tại các stage
            for k in range(1, self.data.K + 1):
                total += self.data.holding_cost[t] * self.i[k, t]
            
            # In-transit inventory
            if self.data.K == 4:
                intransit_legs = [2, 3]
            elif self.data.K == 5:
                intransit_legs = [2, 4]
            else:
                intransit_legs = []
            
            for k in intransit_legs:
                total += self.y[k, t] * self.data.holding_cost[t]
            
        # 4. Transportation Cost
        transport_intervals = self.data.freight_actual
        for t in range(T):
            if self.data.K == 4:
                freight_legs = [3]
            elif self.data.K == 5:
                freight_legs = [2, 4]
            else:
                freight_legs = []
            
            for k in freight_legs:
                for e, iv in enumerate(transport_intervals):
                    total += iv['fixed_cost'] * self.f_freight[k, t, e]
                    total += iv['var_cost_per_unit'] * self.y_freight[k, t, e]

        self.solver.Minimize(total)

    def solve(self):
        print("Solving...")
        status = self.solver.Solve()
        self.cpu_time = self.solver.WallTime() / 1000.0  # Convert ms to seconds
        if status == pywraplp.Solver.OPTIMAL:
            obj_val = self.solver.Objective().Value()
            print(f"Objective value = {obj_val:,.0f}")
            print(f"CPU time = {self.cpu_time:.2f}s")
            return True
        else:
            print('No optimal solution found.')
            return False
    
    def get_objective_value(self):
        return self.solver.Objective().Value()

    def get_cost_breakdown(self):
        """
        Trả về dict chứa breakdown cost: purchasing, production, holding, transport
        """
        T = self.data.T
        m = self.data.m
        purch, prod1, prod2, hold, transp = 0.0, 0.0, 0.0, 0.0, 0.0

        # 1. Purchasing Cost
        for j_idx, supplier in enumerate(self.data.suppliers):
            intervals = supplier['price_intervals']
            for g, interval in enumerate(intervals):
                base_cost = 0.0
                for pg in range(g):
                    w = intervals[pg]['max_q'] - (0 if pg == 0 else intervals[pg-1]['max_q'])
                    base_cost += w * intervals[pg]['price']
                purch += (self.s_price[j_idx, g].solution_value() * base_cost +
                          self.r_price[j_idx, g].solution_value() * interval['price'])
            
            is_selected = sum(self.s_price[j_idx, g].solution_value() for g in range(len(intervals)))
            purch += supplier['primary_cost'] * is_selected
            for t in range(T):
                purch += supplier['secondary_cost'] * self.z[j_idx, t].solution_value()

        # 2. Production Cost - Site 1
        for t_base in range(self.data.base_T):
            fixed_cost = self.data.prod_fixed_cost[t_base * m]
            prod1 += fixed_cost * self.w_prod_group[t_base].solution_value()
        for t in range(T):
            prod1 += self.data.prod_var_cost[t] * self.x[t].solution_value()
        
        # 2b. Production Cost - Site 2
        if self.data.K == 5:
            for t_base in range(self.data.base_T):
                fixed_cost2 = self.data.prod2_fixed_cost[t_base * m]
                prod2 += fixed_cost2 * self.w_prod2_group[t_base].solution_value()
            for t in range(T):
                prod2 += self.data.prod2_var_cost[t] * self.x2[t].solution_value()

        # 3. Holding Cost
        for t in range(T):
            for k in range(1, self.data.K + 1):
                hold += self.data.holding_cost[t] * self.i[k, t].solution_value()
            
            if self.data.K == 4:
                intransit_legs = [2, 3]
            elif self.data.K == 5:
                intransit_legs = [2, 4]
            else:
                intransit_legs = []
            
            for k in intransit_legs:
                hold += self.y[k, t].solution_value() * self.data.holding_cost[t]

        # 4. Transportation Cost
        intervals = self.data.freight_actual
        for t in range(T):
            if self.data.K == 4:
                freight_legs = [3]
            elif self.data.K == 5:
                freight_legs = [2, 4]
            else:
                freight_legs = []
            
            for k in freight_legs:
                for e, iv in enumerate(intervals):
                    transp += (iv['fixed_cost'] * self.f_freight[k, t, e].solution_value() +
                               iv['var_cost_per_unit'] * self.y_freight[k, t, e].solution_value())

        production_total = prod1 + prod2
        return {
            'purchasing': purch,
            'production': production_total,
            'production_site1': prod1,
            'production_site2': prod2,
            'holding': hold,
            'transport': transp,
            'total': purch + production_total + hold + transp
        }

    def get_purchasing_plan(self):
        """
        Trả về dict chứa purchasing plan theo từng kỳ và supplier
        Format: { t: [qty_sup0, qty_sup1, ...], ... }
        """
        T = self.data.T
        plan = {}
        for t in range(T):
            plan[t] = [self.q[j, t].solution_value() for j in range(len(self.data.suppliers))]
        return plan

    def print_detailed_results(self):
        """
        In kết quả chi tiết bao gồm breakdown cost và purchasing plan
        """
        breakdown = self.get_cost_breakdown()
        plan = self.get_purchasing_plan()
        T = self.data.T

        print("-" * 40)
        print("COST BREAKDOWN:")
        print(f"  Purchasing:   {breakdown['purchasing']:,.0f}")
        print(f"  Production:   {breakdown['production']:,.0f}")
        if self.data.K == 5:
            print(f"    - Site 1:   {breakdown['production_site1']:,.0f}")
            print(f"    - Site 2:   {breakdown['production_site2']:,.0f}")
        print(f"  Holding:      {breakdown['holding']:,.0f}")
        print(f"  Transport:    {breakdown['transport']:,.0f}")
        print(f"  Total:        {breakdown['total']:,.0f}")
        print("-" * 40)

        print("PURCHASING PLAN:")
        print(f"{'Per':<4} {'Sup1_1':<8} {'Sup1_2':<8} {'Sup2':<6} {'Sup3':<6}")
        for t in range(T):
            vals = plan[t]
            print(f"{t+1:<4} {vals[0]:<8.0f} {vals[1]:<8.0f} {vals[2]:<6.0f} {vals[3]:<6.0f}")
        print("=" * 40)

if __name__ == "__main__":
    # Test chạy với 4-stage
    print("=== Testing 4-stage ===")
    model4 = SupplyChainModel(SupplyChainData(m=1, mode='Pm', num_stages=4))
    model4.create_variables()
    model4.add_constraints()
    model4.set_objective()
    if model4.solve():
        model4.print_detailed_results()
    
    print("\n" + "="*60 + "\n")
    
    # Test chạy với 5-stage
    print("=== Testing 5-stage ===")
    model5 = SupplyChainModel(SupplyChainData(m=1, mode='Pm', num_stages=5))
    model5.create_variables()
    model5.add_constraints()
    model5.set_objective()
    if model5.solve():
        model5.print_detailed_results()