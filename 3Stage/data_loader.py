class SupplyChainData:
    def __init__(self, m=1, mode='Pm', num_stages=4):
        self.m = m
        self.mode = mode
        
        # ====== NEW: cho phép chọn số stage ======
        self.K = num_stages  # thay vì self.K = 4
        
        # --- 1. THAM SỐ GỐC (BASE PARAMETERS - m=1) ---
        self.base_T = 5  # Lưu lại số kỳ gốc để dùng trong Model
        
        base_demand = [100, 200, 250, 300, 200]
        base_holding_cost = [5, 5, 5, 6, 6]
        base_prod_fixed = [2500, 2500, 3000, 3000, 3500]
        base_prod_var   = [10, 10, 12, 12, 13]
        
        base_prod_cap = [270] * self.base_T
        base_trans_cap = [300] * self.base_T
        
        # --- 2. BIẾN ĐỔI DỮ LIỆU ---
        self.T = self.base_T * m 
        
        # A. Xử lý Nhu cầu (Demand)
        self.demand = [0] * self.T
        if m == 1:
            self.demand = base_demand
        else:
            for t_old in range(self.base_T):
                val = base_demand[t_old]
                if mode == 'Pm':
                    idx = (t_old + 1) * m - 1 
                    self.demand[idx] = val
                elif mode == 'Pmd':
                    dist_val = val / m
                    for sub in range(m):
                        self.demand[t_old * m + sub] = dist_val

        # B. Xử lý Chi phí & Năng lực
        
        # 1. Holding cost: Vẫn chia m
        self.holding_cost = []
        for h in base_holding_cost:
            self.holding_cost.extend([h / m] * m)
            
        # 2. Production Fixed Cost: KHÔNG CHIA m
        # Model sẽ dùng biến w_group để tính phí này 1 lần cho cả nhóm
        self.prod_fixed_cost = []
        for f in base_prod_fixed:
            self.prod_fixed_cost.extend([f] * m) 
            
        # 3. Production Variable Cost: Giữ nguyên
        self.prod_var_cost = []
        for v in base_prod_var:
            self.prod_var_cost.extend([v] * m)

        # 4. Production Capacity: KHÔNG CHIA m Ở ĐÂY
        # Để nguyên giá trị gốc, Model sẽ ràng buộc: Sum(sub_periods) <= Base_Cap
        self.prod_capacity = []
        for c in base_prod_cap:
            self.prod_capacity.extend([c] * m)
            
        # 5. Transport Capacity: Giữ nguyên logic cũ (chia m)
        self.trans_capacity = []
        for c in base_trans_cap:
            self.trans_capacity.extend([c / m] * m)
            
        self.inventory_capacity = 400

        # D. Xử lý Lead Time + tồn kho đầu kỳ theo số stage
        if self.K == 4:
            # Case gốc 4 stage (như Section 5)
            self.lead_times = {
                (1, 2): 0,
                (2, 3): 1 * m,
                (3, 4): 0
            }
            self.initial_inventory = {1: 0, 2: 0, 3: 0, 4: 100}
        
        elif self.K == 3:
            # Case 3 stage: Mfg (1) -> Local (2) -> Regional/Customer (3)
            # Giữ lead time 1 period trên tuyến 2 -> 3 như paper
            self.lead_times = {
                (1, 2): 0,
                (2, 3): 1 * m
            }
            self.initial_inventory = {1: 0, 2: 0, 3: 100}
        
        else:
            raise ValueError(f"num_stages={self.K} is not supported.")

        # --- 3. DỮ LIỆU NHÀ CUNG CẤP ---
        self.global_min_order_first = 50
        self.global_min_order_later = 20
        self.global_max_order_size = 500

        def expand_cap(arr_cap, m_factor):
            new_arr = []
            for val in arr_cap:
                new_arr.extend([val] * m_factor) 
            return new_arr

        sup1_off1_cap = [300, 450, 450, 450, 450]
        sup1_off2_cap = [0, 0, 50, 150, 400]
        sup2_cap      = [200, 400, 650, 900, 1200]
        sup3_cap      = [100, 100, 400, 400, 1000]

        # QUAN TRỌNG: KHÔNG CHIA NHỎ CHI PHÍ CỐ ĐỊNH CỦA SUPPLIER
        self.suppliers = [
            {
                "name": "Sup1_Offer1",
                "cumulative_capacity": expand_cap(sup1_off1_cap, m),
                "primary_cost": 550,
                "secondary_cost": 1000,
                "min_order": 50,
                "price_intervals": [{"max_q": 50, "price": 95}, {"max_q": 150, "price": 80}, {"max_q": 300, "price": 70}, {"max_q": 450, "price": 60}]
            },
            {
                "name": "Sup1_Offer2",
                "cumulative_capacity": expand_cap(sup1_off2_cap, m),
                "primary_cost": 550,
                "secondary_cost": 1000,
                "min_order": 50,
                "price_intervals": [{"max_q": 150, "price": 95}, {"max_q": 250, "price": 80}, {"max_q": 400, "price": 70}]
            },
            {
                "name": "Sup2",
                "cumulative_capacity": expand_cap(sup2_cap, m),
                "primary_cost": 500,
                "secondary_cost": 1000,
                "min_order": 50,
                "price_intervals": [{"max_q": 200, "price": 120}, {"max_q": 400, "price": 100}, {"max_q": 650, "price": 85}, {"max_q": 900, "price": 70}, {"max_q": 1200, "price": 60}]
            },
            {
                "name": "Sup3",
                "cumulative_capacity": expand_cap(sup3_cap, m),
                "primary_cost": 600,
                "secondary_cost": 1050,
                "min_order": 50,
                "price_intervals": [{"max_q": 100, "price": 110}, {"max_q": 400, "price": 80}, {"max_q": 1000, "price": 60}]
            }
        ]

        # --- 4. CƯỚC VẬN CHUYỂN (Giữ nguyên) ---
        self.freight_actual = [
            {"min": 1,   "max": 31,  "fixed_cost": 519,  "var_cost_per_unit": 0.0},
            {"min": 32,  "max": 48,  "fixed_cost": 0.0,  "var_cost_per_unit": 16.2},
            {"min": 49,  "max": 62,  "fixed_cost": 789,  "var_cost_per_unit": 0.0},
            {"min": 63,  "max": 112, "fixed_cost": 0.0,  "var_cost_per_unit": 12.5},
            {"min": 113, "max": 124, "fixed_cost": 1411, "var_cost_per_unit": 0.0},
            {"min": 125, "max": 254, "fixed_cost": 0.0,  "var_cost_per_unit": 11.3},
            {"min": 255, "max": 312, "fixed_cost": 2780, "var_cost_per_unit": 0.0}
        ]