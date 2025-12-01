class SupplyChainData:
    def __init__(self):
        # --- 1. THAM SỐ HỆ THỐNG ---
        self.T = 5           # Số kỳ
        self.K = 4           # Số cấp (Stages)
        self.period_days = 12

        # Lead times (Độ trễ vận chuyển)
        self.lead_times = {
            (1, 2): 0,
            (2, 3): 1,   # Quan trọng: Stage 2->3 mất 1 kỳ
            (3, 4): 0
        }

        # Tồn kho ban đầu
        self.initial_inventory = {1: 0, 2: 0, 3: 0, 4: 100}

        # --- 2. DỮ LIỆU VẬN HÀNH (OPERATIONS) - Table 5 ---
        self.demand = [100, 200, 250, 300, 200]

        # Chi phí sản xuất
        self.prod_fixed_cost = [2500, 2500, 3000, 3000, 3500]
        self.prod_var_cost   = [10,   10,   12,   12,   13]

        # Chi phí tồn kho
        self.holding_cost = [5, 5, 5, 6, 6]

        # Năng lực (Capacities) - CỐ ĐỊNH (Theo hình ảnh Table 5)
        self.inventory_capacity = 200 
        self.prod_capacity =  [270, 270, 270, 270, 270] 
        self.trans_capacity = [300, 300, 300, 300, 300] 

        # --- 3. DỮ IỆU NHÀ CUNG CẤP (SUPPLIERS) 
        self.global_min_order_first = 50
        self.global_min_order_later = 20
        self.global_max_order_size = 500

        self.suppliers = [
            {
                "name": "Sup1_Offer1",
                # Giữ nguyên 450 ở các kỳ cuối để tránh lỗi ràng buộc
                "cumulative_capacity": [300, 450, 450, 450, 450], 
                "primary_cost": 550,    
                "secondary_cost": 1000, 
                "min_order": 50,
                "price_intervals": [    
                    {"max_q": 50,  "price": 95},
                    {"max_q": 150, "price": 80},
                    {"max_q": 300, "price": 70},
                    {"max_q": 450, "price": 60}
                ]
            },
            {
                "name": "Sup1_Offer2",
                # Bắt đầu từ kỳ 3
                "cumulative_capacity": [0, 0, 50, 150, 400],
                "primary_cost": 550, 
                "secondary_cost": 1000,
                "min_order": 50,
                "price_intervals": [
                    {"max_q": 150, "price": 95},
                    {"max_q": 250, "price": 80},
                    {"max_q": 400, "price": 70}
                ]
            },
            {
                "name": "Sup2",
                "cumulative_capacity": [200, 400, 650, 900, 1200],
                "primary_cost": 500,
                "secondary_cost": 1000,
                "min_order": 50,
                "price_intervals": [
                    {"max_q": 200,  "price": 120},
                    {"max_q": 400,  "price": 100},
                    {"max_q": 650,  "price": 85},
                    {"max_q": 900,  "price": 70},
                    {"max_q": 1200, "price": 60}
                ]
            },
            {
                "name": "Sup3",
                "cumulative_capacity": [100, 100, 400, 400, 1000],
                "primary_cost": 600,
                "secondary_cost": 1050,
                "min_order": 50,
                "price_intervals": [
                    {"max_q": 100,  "price": 110},
                    {"max_q": 400,  "price": 80},
                    {"max_q": 1000, "price": 60}
                ]
            }
        ]

        # --- 4. CƯỚC VẬN CHUYỂN (ACTUAL - Đã tối ưu Over-declaring) ---
        self.freight_actual = [
            {"min": 1,   "max": 31,  "fixed_cost": 519,  "var_cost_per_unit": 0.0},
            {"min": 32,  "max": 48,  "fixed_cost": 0.0,  "var_cost_per_unit": 16.2},
            {"min": 49,  "max": 62,  "fixed_cost": 789,  "var_cost_per_unit": 0.0},
            {"min": 63,  "max": 112, "fixed_cost": 0.0,  "var_cost_per_unit": 12.5},
            {"min": 113, "max": 124, "fixed_cost": 1411, "var_cost_per_unit": 0.0},
            {"min": 125, "max": 254, "fixed_cost": 0.0,  "var_cost_per_unit": 11.3},
            {"min": 255, "max": 312, "fixed_cost": 2780, "var_cost_per_unit": 0.0}
        ]