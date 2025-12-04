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
        self.w_prod_group = {}
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
            
            # Production (Sub-period)
            self.x[t] = self.solver.NumVar(0, self.infinity, f'x_{t}')
            self.w_prod[t] = self.solver.BoolVar(f'w_prod_{t}')
            
            # Inventory & Transport
            for k in range(1, self.data.K + 1):
                self.i[k, t] = self.solver.NumVar(0, self.data.inventory_capacity, f'i_{k}_{t}')    
                if k < self.data.K:
                    self.y[k, t] = self.solver.NumVar(0, self.infinity, f'y_{k}_{t}')
                    self.w_trans[k, t] = self.solver.BoolVar(f'w_trans_{k}_{t}')

        # 2. Variable theo kỳ gốc (Base Period) cho Production Setup
        for t_base in range(self.data.base_T):
            self.w_prod_group[t_base] = self.solver.BoolVar(f'w_prod_group_{t_base}')

        # 3. Pricing Scheme
        for j_idx, supplier in enumerate(self.data.suppliers):
            for g, _ in enumerate(supplier['price_intervals']):
                self.s_price[j_idx, g] = self.solver.BoolVar(f's_{j_idx}_{g}')
                self.r_price[j_idx, g] = self.solver.NumVar(0, self.infinity, f'r_{j_idx}_{g}')

        # 4. Freight Rates (CONDITIONAL based on number of stages)
        transport_intervals = self.data.freight_actual 
        for t in range(T):
            # Determine which stages need freight variables
            if self.data.K == 4:
                freight_stages = [3]  # leg 3 -> 4
            elif self.data.K == 3:
                freight_stages = [2]  # leg 2 -> 3
            else:
                freight_stages = []
            
            for k in freight_stages:
                for e, _ in enumerate(transport_intervals):
                    self.f_freight[k, t, e] = self.solver.BoolVar(f'f_{k}_{t}_{e}')
                    self.y_freight[k, t, e] = self.solver.NumVar(0, self.infinity, f'y_fr_{k}_{t}_{e}')


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

        # 2. PRODUCTION CONSTRAINTS
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

        # 3. FLOW BALANCE (CONDITIONAL FOR 3-STAGE vs 4-STAGE)
        for t in range(T):
            # ===== Stage 1: Mfg =====
            in_1 = sum(self.q[j, t] for j in range(len(self.data.suppliers)))
            prev_1 = self.data.initial_inventory[1] if t == 0 else self.i[1, t-1]
            self.solver.Add(in_1 + prev_1 == self.x[t] + self.i[1, t])

            # ===== Stage 2: Local WH (same for both 3 & 4 stage) =====
            prev_2 = self.data.initial_inventory[2] if t == 0 else self.i[2, t-1]
            self.solver.Add(self.x[t] + prev_2 == self.y[2, t] + self.i[2, t])
            self.solver.Add(self.y[2, t] <= self.data.trans_capacity[t] * self.w_trans[2, t])

            if self.data.K == 4:
                # ----- Case 4 stage -----
                # Stage 3: Regional WH 1 (intermediate, with shipping to next stage)
                in_3 = 0
                lt = self.data.lead_times[(2, 3)]
                if t >= lt:
                    in_3 = self.y[2, t - lt]
                prev_3 = self.data.initial_inventory[3] if t == 0 else self.i[3, t-1]
                self.solver.Add(in_3 + prev_3 == self.y[3, t] + self.i[3, t])
                self.solver.Add(self.y[3, t] <= self.data.trans_capacity[t] * self.w_trans[3, t])

                # Stage 4: Regional WH 2 / Customer
                prev_4 = self.data.initial_inventory[4] if t == 0 else self.i[4, t-1]
                self.solver.Add(self.y[3, t] + prev_4 == self.data.demand[t] + self.i[4, t])

            elif self.data.K == 3:
                # ----- Case 3 stage -----
                # Stage 3: Regional WH / Customer (final stage, no further shipping)
                in_3 = 0
                lt = self.data.lead_times[(2, 3)]
                if t >= lt:
                    in_3 = self.y[2, t - lt]
                prev_3 = self.data.initial_inventory[3] if t == 0 else self.i[3, t-1]
                self.solver.Add(in_3 + prev_3 == self.data.demand[t] + self.i[3, t])

        # 4. FREIGHT RATE (CONDITIONAL)
        intervals = self.data.freight_actual
        for t in range(T):
            if self.data.K == 4:
                freight_stages = [3]     # leg 3 -> 4
            elif self.data.K == 3:
                freight_stages = [2]     # leg 2 -> 3
            else:
                freight_stages = []

            for k in freight_stages:
                self.solver.Add(sum(self.y_freight[k, t, e] for e in range(len(intervals))) == self.y[k, t])
                self.solver.Add(sum(self.f_freight[k, t, e] for e in range(len(intervals))) <= 1)
                for e, iv in enumerate(intervals):
                    self.solver.Add(self.y_freight[k, t, e] >= iv['min'] * self.f_freight[k, t, e])
                    self.solver.Add(self.y_freight[k, t, e] <= iv['max'] * self.f_freight[k, t, e])

        # 5. ENDING INVENTORY TARGET (Generic for K stages)
        final_stage = self.data.K
        self.solver.Add(self.i[final_stage, T-1] == 100)
        for k in range(1, final_stage):
            self.solver.Add(self.i[k, T-1] == 0)

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

        # 2. Production Cost
        for t_base in range(self.data.base_T):
            fixed_cost = self.data.prod_fixed_cost[t_base * m]
            total += fixed_cost * self.w_prod_group[t_base]
            
        for t in range(T):
            total += self.data.prod_var_cost[t] * self.x[t]

        # 3. Holding Cost (CONDITIONAL for in-transit inventory)
        for t in range(T):
            for k in range(1, self.data.K + 1):
                total += self.data.holding_cost[t] * self.i[k, t]

            if self.data.K == 4:
                intransit_stages = [2, 3]
            elif self.data.K == 3:
                intransit_stages = [2]
            else:
                intransit_stages = []

            for k in intransit_stages:
                total += self.y[k, t] * self.data.holding_cost[t]
            
        # 4. Transportation Cost (CONDITIONAL)
        transport_intervals = self.data.freight_actual
        for t in range(T):
            if self.data.K == 4:
                freight_stages = [3]
            elif self.data.K == 3:
                freight_stages = [2]
            else:
                freight_stages = []
                
            for k in freight_stages:
                for e, iv in enumerate(transport_intervals):
                    total += iv['fixed_cost'] * self.f_freight[k, t, e]
                    total += iv['var_cost_per_unit'] * self.y_freight[k, t, e]

        self.solver.Minimize(total)

    def solve(self):
        print("Solving...")
        status = self.solver.Solve()
        if status == pywraplp.Solver.OPTIMAL:
            obj_val = self.solver.Objective().Value()
            print(f"Objective value = {obj_val:,.0f}")
            return True
        else:
            print('No optimal solution found.')
            return False

    def get_cost_breakdown(self):
        """
        Return dict with breakdown cost: purchasing, production, holding, transport
        """
        T = self.data.T
        m = self.data.m
        purch, prod, hold, transp = 0.0, 0.0, 0.0, 0.0

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

        # 2. Production Cost
        for t_base in range(self.data.base_T):
            fixed_cost = self.data.prod_fixed_cost[t_base * m]
            prod += fixed_cost * self.w_prod_group[t_base].solution_value()
        for t in range(T):
            prod += self.data.prod_var_cost[t] * self.x[t].solution_value()

        # 3. Holding Cost (CONDITIONAL)
        for t in range(T):
            for k in range(1, self.data.K + 1):
                hold += self.data.holding_cost[t] * self.i[k, t].solution_value()

            if self.data.K == 4:
                intransit_stages = [2, 3]
            elif self.data.K == 3:
                intransit_stages = [2]
            else:
                intransit_stages = []

            for k in intransit_stages:
                hold += self.y[k, t].solution_value() * self.data.holding_cost[t]

        # 4. Transportation Cost (CONDITIONAL)
        intervals = self.data.freight_actual
        for t in range(T):
            if self.data.K == 4:
                freight_stages = [3]
            elif self.data.K == 3:
                freight_stages = [2]
            else:
                freight_stages = []
                
            for k in freight_stages:
                for e, iv in enumerate(intervals):
                    transp += (iv['fixed_cost'] * self.f_freight[k, t, e].solution_value() +
                               iv['var_cost_per_unit'] * self.y_freight[k, t, e].solution_value())

        return {
            'purchasing': purch,
            'production': prod,
            'holding': hold,
            'transport': transp,
            'total': purch + prod + hold + transp
        }

    def get_purchasing_plan(self):
        """
        Return dict with purchasing plan per period per supplier
        Format: { t: [qty_sup0, qty_sup1, ...], ... }
        """
        T = self.data.T
        plan = {}
        for t in range(T):
            plan[t] = [self.q[j, t].solution_value() for j in range(len(self.data.suppliers))]
        return plan

    def print_detailed_results(self):
        """
        Print detailed results including breakdown cost and purchasing plan
        """
        breakdown = self.get_cost_breakdown()
        plan = self.get_purchasing_plan()
        T = self.data.T

        print("-" * 40)
        print("COST BREAKDOWN:")
        print(f"  Purchasing:   {breakdown['purchasing']:,.0f}")
        print(f"  Production:   {breakdown['production']:,.0f}")
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
    # Test 3-stage
    data = SupplyChainData(m=1, mode='Pm', num_stages=3)
    model = SupplyChainModel(data)
    model.create_variables()
    model.add_constraints()
    model.set_objective()
    if model.solve():
        model.print_detailed_results()
