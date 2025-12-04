class SupplyChainData:
    def __init__(self, m=1, mode='Pm'):
        self.m = m
        self.mode = mode
        
        # --- 1. THAM SỐ GỐC (BASE PARAMETERS - m=1) ---
        self.base_T = 5  # Lưu lại số kỳ gốc để dùng trong Model
        self.K = 4
        
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
                    # M^m: dồn hết nhu cầu vào sub-period CUỐI cùng của mỗi block
                    idx = (t_old + 1) * m - 1 
                    self.demand[idx] = val
                elif mode == 'Pmd':
                    # M^m_d ĐÚNG điều kiện Thm 3: chia đều nhu cầu
                    dist_val = val / m
                    for sub in range(m):
                        self.demand[t_old * m + sub] = dist_val
                elif mode == 'Pmd_nc':
                    # M^m_d SAI điều kiện: phân bố KHÔNG đều (vi phạm Theorem 3)
                    # Nhưng vẫn phủ toàn block để model khả thi
                    
                    # Định nghĩa weights theo từng m
                    # Gần uniform nhưng VẪN vi phạm điều kiện (không hoàn toàn đều)
                    if m == 2:
                        weights = [0.6, 0.4]  # so với uniform [0.5, 0.5]
                    elif m == 3:
                        weights = [0.4, 0.35, 0.25]  # so với uniform [0.333, 0.333, 0.333]
                    elif m == 4:
                        weights = [0.28, 0.26, 0.24, 0.22]  # so với uniform [0.25, 0.25, 0.25, 0.25]
                    else:
                        # Fallback: gần đều nhưng có chút biến động
                        base = 1.0 / m
                        weights = [base + (m - i - m/2) * 0.01 for i in range(m)]
                        s = sum(weights)
                        weights = [w / s for w in weights]
                    
                    # Normalize để đảm bảo tổng = 1
                    s = sum(weights)
                    weights = [w / s for w in weights]
                    
                    for sub in range(m):
                        idx = t_old * m + sub
                        self.demand[idx] = val * weights[sub]
                else:
                    raise ValueError(f"Unknown mode: {mode}")

        # B. Xử lý Chi phí & Năng lực
        
        # 1. Holding cost: Vẫn chia m (đúng theo định lý 2 condition i)
        self.holding_cost = []
        for h in base_holding_cost:
            self.holding_cost.extend([h / m] * m)
            
        # 2. Production Fixed Cost: KHÔNG CHIA m (Theo condition ii)
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

        # D. Xử lý Lead Time
        self.lead_times = {
            (1, 2): 0 ,
            (2, 3): 1 * m, 
            (3, 4): 0 
        }
        
        self.initial_inventory = {1: 0, 2: 0, 3: 0, 4: 100}

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