class SupplyChainData:
    def __init__(self, m=1, mode='Pm'):
        """
        m: Hệ số chia nhỏ thời gian (1, 2, 3, 4...)
        mode: 'Pm' (Nhu cầu dồn cuối kỳ) hoặc 'Pmd' (Nhu cầu chia đều)
        """
        self.m = m
        self.mode = mode
        
        # --- 1. THAM SỐ GỐC (BASE PARAMETERS - m=1) ---
        base_T = 5
        self.K = 4
        
        # Dữ liệu gốc (m=1)
        base_demand = [100, 200, 250, 300, 200]
        base_holding_cost = [5, 5, 5, 6, 6]
        base_prod_fixed = [2500, 2500, 3000, 3000, 3500]
        base_prod_var   = [10, 10, 12, 12, 13]
        
        base_prod_cap = [270] * base_T
        base_trans_cap = [300] * base_T
        
        # --- 2. BIẾN ĐỔI DỮ LIỆU (TRANSFORMATION) ---
        self.T = base_T * m  # Tăng số kỳ lên m lần (Ví dụ m=2 -> T=10)
        
        # A. Xử lý Nhu cầu (Demand)
        self.demand = [0] * self.T
        if m == 1:
            self.demand = base_demand
        else:
            for t_old in range(base_T):
                val = base_demand[t_old]
                if mode == 'Pm':
                    # Pm: Nhu cầu dồn vào kỳ con cuối cùng của nhóm
                    # Ví dụ m=2: [0, 100, 0, 200...]
                    idx = (t_old + 1) * m - 1 
                    self.demand[idx] = val
                elif mode == 'Pmd':
                    # Pmd: Nhu cầu chia đều cho các kỳ con
                    # Ví dụ m=2: [50, 50, 100, 100...]
                    dist_val = val / m
                    for sub in range(m):
                        self.demand[t_old * m + sub] = dist_val

        # B. Xử lý Chi phí (Costs) - PHẦN QUAN TRỌNG NHẤT CẦN SỬA
        
        # 1. Holding cost: Giảm m lần (vì thời gian lưu kho ngắn lại)
        self.holding_cost = []
        for h in base_holding_cost:
            self.holding_cost.extend([h / m] * m)
            
        # 2. Production Fixed Cost: PHẢI CHIA CHO m
        # Nếu không chia, tổng chi phí setup sẽ tăng gấp m lần, làm sai lệch kết quả.
        self.prod_fixed_cost = []
        for f in base_prod_fixed:
            self.prod_fixed_cost.extend([f / m] * m) 
            
        # 3. Production Variable Cost: Giữ nguyên (đơn giá trên 1 sản phẩm không đổi)
        self.prod_var_cost = []
        for v in base_prod_var:
            self.prod_var_cost.extend([v] * m)

        # C. Xử lý Năng lực (Capacities) - Giảm m lần
        # Vì thời gian ngắn lại, năng lực sản xuất trong kỳ đó cũng phải giảm
        self.prod_capacity = []
        for c in base_prod_cap:
            self.prod_capacity.extend([c / m] * m)
            
        self.trans_capacity = []
        for c in base_trans_cap:
            self.trans_capacity.extend([c / m] * m)
            
        self.inventory_capacity = 400 # Sức chứa kho giữ nguyên (không gian vật lý không đổi)

        # D. Xử lý Lead Time - Tăng m lần
        # Ví dụ: Cũ mất 1 kỳ (12 ngày). Mới (kỳ 6 ngày) -> Phải mất 2 kỳ mới đi hết 12 ngày.
        self.lead_times = {
            (1, 2): 0 ,
            (2, 3): 1 * m, 
            (3, 4): 0 
        }
        
        self.initial_inventory = {1: 0, 2: 0, 3: 0, 4: 100}

        # --- 3. DỮ LIỆU NHÀ CUNG CẤP (SUPPLIERS) ---
        self.global_min_order_first = 50
        self.global_min_order_later = 20
        self.global_max_order_size = 500

        # Hàm helper để giãn nở mảng capacity của Supplier (Lặp lại giá trị)
        def expand_cap(arr_cap, m_factor):
            new_arr = []
            for val in arr_cap:
                new_arr.extend([val] * m_factor) 
            return new_arr

        # Dữ liệu gốc Capacity Supplier
        sup1_off1_cap = [300, 450, 450, 450, 450]
        sup1_off2_cap = [0, 0, 50, 150, 400]
        sup2_cap      = [200, 400, 650, 900, 1200]
        sup3_cap      = [100, 100, 400, 400, 1000]

        # QUAN TRỌNG: Chia nhỏ chi phí Supplier
        # Primary Cost: Phí gia nhập. Chia m để giảm gánh nặng khi so sánh tổng thể.
        # Secondary Cost: Phí đặt hàng. Chia m để mô phỏng việc đặt hàng nhỏ lẻ thường xuyên hơn.
        
        p_scale = 1.0 / m  # Tỷ lệ chia nhỏ
        
        self.suppliers = [
            {
                "name": "Sup1_Offer1",
                "cumulative_capacity": expand_cap(sup1_off1_cap, m),
                "primary_cost": 550 * p_scale,     # <--- CHIA NHỎ
                "secondary_cost": 1000 * p_scale,  # <--- CHIA NHỎ
                "min_order": 50,
                "price_intervals": [{"max_q": 50, "price": 95}, {"max_q": 150, "price": 80}, {"max_q": 300, "price": 70}, {"max_q": 450, "price": 60}]
            },
            {
                "name": "Sup1_Offer2",
                "cumulative_capacity": expand_cap(sup1_off2_cap, m),
                "primary_cost": 550 * p_scale,      # <--- CHIA NHỎ
                "secondary_cost": 1000 * p_scale,   # <--- CHIA NHỎ
                "min_order": 50,
                "price_intervals": [{"max_q": 150, "price": 95}, {"max_q": 250, "price": 80}, {"max_q": 400, "price": 70}]
            },
            {
                "name": "Sup2",
                "cumulative_capacity": expand_cap(sup2_cap, m),
                "primary_cost": 500 * p_scale,      # <--- CHIA NHỎ
                "secondary_cost": 1000 * p_scale,   # <--- CHIA NHỎ
                "min_order": 50,
                "price_intervals": [{"max_q": 200, "price": 120}, {"max_q": 400, "price": 100}, {"max_q": 650, "price": 85}, {"max_q": 900, "price": 70}, {"max_q": 1200, "price": 60}]
            },
            {
                "name": "Sup3",
                "cumulative_capacity": expand_cap(sup3_cap, m),
                "primary_cost": 600 * p_scale,      # <--- CHIA NHỎ
                "secondary_cost": 1050 * p_scale,   # <--- CHIA NHỎ
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