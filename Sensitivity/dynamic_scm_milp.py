from ortools.linear_solver import pywraplp
from data_loader import SupplyChainData 

class SupplyChainModel:
    def __init__(self, data):
        self.data = data
        self.solver = pywraplp.Solver.CreateSolver('SCIP')
        if not self.solver:
            raise Exception("SCIP backend not found.")
        self.infinity = self.solver.infinity()
        #khai báo decision variables
        self.q, self.z = {}, {}
        self.x, self.w_prod = {}, {}
        self.y, self.w_trans = {}, {}
        self.i = {}
        self.s_price, self.r_price = {}, {}
        self.f_freight, self.y_freight = {}, {}

    def create_variables(self):
        print("Creating variables...")
        T = self.data.T # thời gian t 
        for t in range(T):
            # Purchasing
            for j_idx, supplier in enumerate(self.data.suppliers): # khai báo các biến quyết định mua hàng
                # DECISION VARIABLE: q[j,t] (Số lượng mua). Biến liên tục (NumVar), >= 0.
                self.q[j_idx, t] = self.solver.NumVar(0, self.infinity, f'q_{j_idx}_{t}')
                # DECISION VARIABLE: z[j,t] (Biến nhị phân, 1 nếu mua, 0 nếu không mua)
                self.z[j_idx, t] = self.solver.BoolVar(f'z_{j_idx}_{t}')
            # Production
            self.x[t] = self.solver.NumVar(0, self.infinity, f'x_{t}') # DECISION VARIABLE: x[t] (Số lượng sản xuất). Biến liên tục (NumVar), >= 0.
            self.w_prod[t] = self.solver.BoolVar(f'w_prod_{t}') # DECISION VARIABLE: w_prod[t] (Biến nhị phân, 1 nếu sản xuất, 0 nếu không sản xuất)
            # Inventory & Transport
            for k in range(1, self.data.K + 1): # khai báo các biến quyết định tồn kho và vận chuyển
                # DECISION VARIABLE: i[k,t] (Mức tồn kho). Cận trên là inventory_capacity (PARAMETER).
                self.i[k, t] = self.solver.NumVar(0, self.data.inventory_capacity, f'i_{k}_{t}')    
                if k < self.data.K: # khai báo các biến quyết định vận chuyển
                    # DECISION VARIABLE: y[k,t] (Số lượng vận chuyển). Biến liên tục (NumVar), >= 0.
                    self.y[k, t] = self.solver.NumVar(0, self.infinity, f'y_{k}_{t}')
                    # DECISION VARIABLE: w_trans[k,t] (Biến nhị phân, 1 nếu vận chuyển, 0 nếu không vận chuyển)
                    self.w_trans[k, t] = self.solver.BoolVar(f'w_trans_{k}_{t}')

        # Pricing Scheme
        for j_idx, supplier in enumerate(self.data.suppliers): # khai báo các biến quyết định giá
            for g, _ in enumerate(supplier['price_intervals']):
                # DECISION VARIABLE: s_price[j_idx, g] (Biến nhị phân, 1 nếu chọn giá, 0 nếu không chọn giá)
                self.s_price[j_idx, g] = self.solver.BoolVar(f's_{j_idx}_{g}')
                # DECISION VARIABLE: r_price[j_idx, g] (Giá trị của giá)
                self.r_price[j_idx, g] = self.solver.NumVar(0, self.infinity, f'r_{j_idx}_{g}')

        # Freight Rates (Chỉ tạo biến cho Stage 3->4, tức là k=3)
        transport_intervals = self.data.freight_actual 
        for t in range(T):
            for k in range(3, self.data.K): 
                for e, _ in enumerate(transport_intervals):
                    self.f_freight[k, t, e] = self.solver.BoolVar(f'f_{k}_{t}_{e}')
                    self.y_freight[k, t, e] = self.solver.NumVar(0, self.infinity, f'y_fr_{k}_{t}_{e}')
    '''
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
            total_purchased_cumulative = 0 # Biến để tính cumulative purchased quantity
            for t in range(T):
                qty = self.q[j_idx, t]
                # CONSTRAINT: Số lượng mua >= Min Order * Biến chọn z
                # supplier['min_order'] là PARAMETER.
                self.solver.Add(qty >= supplier['min_order'] * self.z[j_idx, t])
                # CONSTRAINT: Số lượng mua <= Max Order * Biến chọn z
                self.solver.Add(qty <= self.data.global_max_order_size * self.z[j_idx, t])
                # CONSTRAINT: Tổng mua tích lũy <= Năng lực cung ứng tích lũy (PARAMETER)
                # Capacity
                total_purchased_cumulative += qty
                self.solver.Add(total_purchased_cumulative <= supplier['cumulative_capacity'][t])
                
                '''# CONSTRAINT: Logic chặn mua nếu offer hết hạn (Capacity không tăng)
                if t > 0:
                    added_cap = supplier['cumulative_capacity'][t] - supplier['cumulative_capacity'][t-1]
                    if added_cap <= 0: self.solver.Add(qty == 0)
                else:
                    if supplier['cumulative_capacity'][0] == 0: self.solver.Add(qty == 0)'''
                # CONSTRAINT: Tuyến tính hóa chi phí (Linearization)
                # Tổng lượng mua thực tế == Tổng lượng mua tính toán từ các khoảng giá
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
        # 3. Holding (CẬP NHẬT MỚI)
        # Lưu ý: Bài báo không tính phí holding cho Initial Inventory đầu kỳ 1 (t=0)
        # Chỉ tính i_k^t (cuối kỳ) và y_k^t (dòng chảy trong kỳ)
        for t in range(T):
            # A. Node Inventory (i_k^t)
            for k in range(1, self.data.K + 1):
                total += self.data.holding_cost[t] * self.i[k, t]
            
            # B. In-transit Inventory (y_k^t)
            # Theo bài báo Eq 15: k thuộc Kd = {2, 3}
            # Tức là tính cho y_2 (Stage 2->3) và y_3 (Stage 3->4)
            for k in [2, 3]: 
                total += self.y[k, t] * self.data.holding_cost[t]
            

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
            hhold = 0.0
            for t in range(T):
                # Node Inventory
                for k in range(1, self.data.K + 1):
                    hold += self.data.holding_cost[t] * self.i[k, t].solution_value()
                
                # In-transit Inventory (KD = {2, 3})
                # Stage 2->3 AND Stage 3->4
                for k in [2, 3]:
                    hold += self.y[k, t].solution_value() * self.data.holding_cost[t]

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
            print(f"  Holding:      {hold:,.0f}")
            print(f"  Transport:    {transp:,.0f}")
            print(f"  Sum check:    {purch + prod + hold + transp:,.0f}")
            print("===================================")

            print("PURCHASING PLAN:")
            print(f"{'Per':<4} {'Sup1_1':<8} {'Sup1_2':<8} {'Sup2':<6} {'Sup3':<6}")
            for t in range(T):
                vals = [self.q[j, t].solution_value() for j in range(len(self.data.suppliers))]
                print(f"{t+1:<4} {vals[0]:<8.0f} {vals[1]:<8.0f} {vals[2]:<6.0f} {vals[3]:<6.0f}")
        else:
            print('No optimal solution found.')
#'''
if __name__ == "__main__":
    model = SupplyChainModel(SupplyChainData())
    model.create_variables()
    model.add_constraints()
    model.set_objective()
    model.solve()
#'''
'''
if __name__ == "__main__":
    data = SupplyChainData()
    model = SupplyChainModel(data)
    
    # 1. Tạo biến & Ràng buộc cơ bản
    model.create_variables()
    model.add_constraints()
    
    # 2. Thiết lập mục tiêu
    model.set_objective()
    
    # 3. [VALIDATION STEP] Bật dòng này để ép kế hoạch giống Paper
    model.force_paper_plan()  # <--- THÊM DÒNG NÀY
    
    # 4. Giải
    model.solve()
'''