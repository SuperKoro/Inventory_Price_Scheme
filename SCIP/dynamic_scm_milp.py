from ortools.linear_solver import pywraplp
from data_loader import SupplyChainData 

class SupplyChainModel:
    def __init__(self, data):
        self.data = data
        self.solver = pywraplp.Solver.CreateSolver('SCIP')
        if not self.solver:
            raise Exception("SCIP backend not found.")
        self.infinity = self.solver.infinity()
        
        # Variables Storage
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

        # Freight Rates (Dùng ACTUAL)
        transport_intervals = self.data.freight_actual 
        for t in range(T):
            for k in range(1, self.data.K):
                for e, _ in enumerate(transport_intervals):
                    self.f_freight[k, t, e] = self.solver.BoolVar(f'f_{k}_{t}_{e}')
                    self.y_freight[k, t, e] = self.solver.NumVar(0, self.infinity, f'y_fr_{k}_{t}_{e}')
    '''ép plan giống trong paper
    def force_paper_plan(self):
        """
        Hàm dùng để DEBUG/VALIDATE.
        Ép buộc model phải mua đúng số lượng như Table 7 trong paper.
        """
        print("\n!!! WARNING: FORCING PURCHASING PLAN FROM PAPER !!!")
        
        # Dictionary lưu kế hoạch mục tiêu: (Period_index, Supplier_index): Quantity
        # Period 0 = Kỳ 1, Period 4 = Kỳ 5
        # Sup 0 = Sup1_Off1, Sup 1 = Sup1_Off2, Sup 2 = Sup2, Sup 3 = Sup3
        target_plan = {
            (0, 0): 270, # Kỳ 1, Sup1_Off1
            (1, 0): 180, # Kỳ 2, Sup1_Off1
            (1, 2): 60,  # Kỳ 2, Sup2
            (2, 3): 400, # Kỳ 3, Sup3
            (3, 1): 140, # Kỳ 4, Sup1_Off2
        }

        # Duyệt qua tất cả các biến q và ép giá trị
        for t in range(self.data.T):
            for j_idx in range(len(self.data.suppliers)):
                # Lấy giá trị target, nếu không có trong dict thì mặc định là 0
                target_qty = target_plan.get((t, j_idx), 0)
                
                # Thêm ràng buộc cứng: q == target_qty
                self.solver.Add(self.q[j_idx, t] == target_qty)
                
                if target_qty > 0:
                    print(f"  -> Forced q[{j_idx}, {t}] = {target_qty}")
    '''
    def add_constraints(self):
        print("Adding constraints...")
        T = self.data.T
        
        # 1. SUPPLIER
        for j_idx, supplier in enumerate(self.data.suppliers):
            total_purchased_cumulative = 0
            for t in range(T):
                qty = self.q[j_idx, t]
                # Min Order
                self.solver.Add(qty >= supplier['min_order'] * self.z[j_idx, t])
                self.solver.Add(qty <= supplier['max_order_per_order'] * self.z[j_idx, t])
                # Capacity Cumulative
                total_purchased_cumulative += qty
                self.solver.Add(total_purchased_cumulative <= supplier['cumulative_capacity'][t])
                
                # --- CHẶN MUA (Logic Offer hết hạn) ---
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
        # ... (Sau đoạn FREIGHT RATE) ...

        # --- 4. ENDING INVENTORY TARGET (QUAN TRỌNG: SỬA LỖI 135K -> 141K) ---
        # Bắt buộc Stage 4 phải còn dư 100 đơn vị vào cuối kỳ 5 như bài báo yêu cầu
        self.solver.Add(self.i[4, T-1] == 100) 
        
        # (Tùy chọn) Ép các Stage khác về 0 cho sạch hệ thống
        for k in range(1, 4): 
            self.solver.Add(self.i[k, T-1] == 0)

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

        # 3. FREIGHT RATE
        intervals = self.data.freight_actual
        for t in range(T):
            for k in range(1, self.data.K):
                self.solver.Add(sum(self.y_freight[k, t, e] for e in range(len(intervals))) == self.y[k, t])
                self.solver.Add(sum(self.f_freight[k, t, e] for e in range(len(intervals))) <= 1)
                for e, iv in enumerate(intervals):
                    self.solver.Add(self.y_freight[k, t, e] >= iv['min'] * self.f_freight[k, t, e])
                    self.solver.Add(self.y_freight[k, t, e] <= iv['max'] * self.f_freight[k, t, e])

        # --- 4. ENDING INVENTORY TARGET (QUAN TRỌNG NHẤT) ---
        self.solver.Add(self.i[4, T-1] == 100) # Stage 4 phải còn 100
        for k in range(1, 4): self.solver.Add(self.i[k, T-1] == 0)


    def set_objective(self):
        print("Setting objective function...")
        T = self.data.T
        total = 0
        
        # 1. Purchasing Cost (Giá mua)
        for j_idx, supplier in enumerate(self.data.suppliers):
            intervals = supplier['price_intervals']
            for g, interval in enumerate(intervals):
                base_cost = 0
                for pg in range(g):
                    w = intervals[pg]['max_q'] - (0 if pg==0 else intervals[pg-1]['max_q'])
                    base_cost += w * intervals[pg]['price']
                total += (self.s_price[j_idx, g] * base_cost + self.r_price[j_idx, g] * interval['price'])
            
            # Ordering Costs (Phí đặt hàng)
            is_selected = sum(self.s_price[j_idx, g] for g in range(len(intervals)))
            total += supplier['primary_cost'] * is_selected
            for t in range(T): total += supplier['secondary_cost'] * self.z[j_idx, t]

        # 2. Production Cost (Phí sản xuất)
        for t in range(T):
            total += self.data.prod_fixed_cost[t] * self.w_prod[t]
            total += self.data.prod_var_cost[t] * self.x[t]

        # 3. Holding Cost (Phí tồn kho tại kho)
        for t in range(T):
            for k in range(1, self.data.K + 1):
                total += self.data.holding_cost[t] * self.i[k, t]

        # 4. In-Transit Holding Cost (Phí tồn kho trên đường) 
        # Hàng đang đi từ Stage k sang k+1 cũng bị tính phí giữ hàng nếu lead time > 0
        for t in range(T):
            for k in range(1, self.data.K): # k=1,2,3
                if k < self.data.K:
                    # Lấy lead time của cung đường này
                    lt = self.data.lead_times.get((k, k+1), 0)
                    if lt > 0:
                        # Phí = Lượng hàng * Phí đơn vị * Số kỳ trễ
                        # Giả sử phí giữ hàng trên đường = phí giữ hàng tại kho (holding_cost[t])
                        total += self.y[k, t] * self.data.holding_cost[t] * lt

        # 5. Transportation Cost (Cước vận chuyển)
        transport_intervals = self.data.freight_actual
        for t in range(T):
            for k in range(1, self.data.K):
                for e, iv in enumerate(transport_intervals):
                    total += iv['fixed_cost'] * self.f_freight[k, t, e]
                    total += iv['var_cost_per_unit'] * self.y_freight[k, t, e]

        self.solver.Minimize(total)
    def solve(self):
        print("Solving...")
        status = self.solver.Solve()
        if status == pywraplp.Solver.OPTIMAL:
            obj_val = self.solver.Objective().Value()
            print("Objective value = ", obj_val)

        # ========== BREAKDOWN CHI PHÍ ==========
        T = self.data.T
        purch = 0.0
        prod = 0.0
        hold = 0.0
        transp = 0.0

        # 1. Purchasing + Ordering cost
        for j_idx, supplier in enumerate(self.data.suppliers):
            intervals = supplier['price_intervals']

            # incremental discount phần nguyên liệu
            for g, interval in enumerate(intervals):
                base_cost = 0.0
                for pg in range(g):
                    w = intervals[pg]['max_q'] - (0 if pg == 0 else intervals[pg-1]['max_q'])
                    base_cost += w * intervals[pg]['price']
                purch += (self.s_price[j_idx, g].solution_value() * base_cost +
                          self.r_price[j_idx, g].solution_value() * interval['price'])

            # primary + secondary ordering
            is_selected = sum(self.s_price[j_idx, g].solution_value()
                              for g in range(len(intervals)))
            purch += supplier['primary_cost'] * is_selected

            for t in range(T):
                purch += supplier['secondary_cost'] * self.z[j_idx, t].solution_value()

        # 2. Production cost
        for t in range(T):
            prod += (self.data.prod_fixed_cost[t] * self.w_prod[t].solution_value() +
                     self.data.prod_var_cost[t] * self.x[t].solution_value())

        # 3. Holding cost (tồn kho tại các kho)
        for t in range(T):
            for k in range(1, self.data.K + 1):
                hold += self.data.holding_cost[t] * self.i[k, t].solution_value()

        # 4. Transportation cost
        transport_intervals = self.data.freight_actual
        for t in range(T):
            for k in range(1, self.data.K):
                for e, iv in enumerate(transport_intervals):
                    transp += (iv['fixed_cost'] * self.f_freight[k, t, e].solution_value() +
                               iv['var_cost_per_unit'] * self.y_freight[k, t, e].solution_value())

        print("COST BREAKDOWN:")
        print(f"  Purchasing:   {purch}")
        print(f"  Production:   {prod}")
        print(f"  Holding:      {hold}")
        print(f"  Transport:    {transp}")
        print(f"  Sum check:    {purch + prod + hold + transp}")
        print("===================================")
        # ========== HẾT BREAKDOWN ==========

        # Phần in purchasing plan như cũ
        print("------------------------------")
        print("PURCHASING PLAN:")
        print("Per  Sup1_1   Sup1_2   Sup2   Sup3")
        for t in range(T):
            q1_1 = self.q[0, t].solution_value()
            q1_2 = self.q[1, t].solution_value()
            q2   = self.q[2, t].solution_value()
            q3   = self.q[3, t].solution_value()
            print(f"{t+1:<4}{int(round(q1_1)):>8}{int(round(q1_2)):>8}"
                  f"{int(round(q2)):>8}{int(round(q3)):>8}")
        


'''     
    def solve(self):
        print("Solving...")
        status = self.solver.Solve()
        if status == pywraplp.Solver.OPTIMAL:
            print(f'Objective value = {self.solver.Objective().Value()}')
            print("-" * 30)
            print("PURCHASING PLAN:")
            print(f"{'Per':<4} {'Sup1_1':<8} {'Sup1_2':<8} {'Sup2':<6} {'Sup3':<6}")
            for t in range(self.data.T):
                vals = [self.q[j, t].solution_value() for j in range(len(self.data.suppliers))]
                print(f"{t+1:<4} {vals[0]:<8.0f} {vals[1]:<8.0f} {vals[2]:<6.0f} {vals[3]:<6.0f}")
        else:
            print('No optimal solution found.')
'''
#'''
if __name__ == "__main__":
    model = SupplyChainModel(SupplyChainData())
    model.create_variables()
    model.add_constraints()
    model.set_objective()
    model.solve()

#'''
'''# ép plan giống trong paper
if __name__ == "__main__":
    data = SupplyChainData()
    model = SupplyChainModel(data)
    
    
    model.create_variables()
    model.add_constraints()
    
    model.set_objective()
    
    model.force_paper_plan()  # <--- THÊM DÒNG NÀY
    
    model.solve()
'''