from ortools.linear_solver import pywraplp

class SupplyChainData:
    def __init__(self):
        # --- 1. THAM SỐ HỆ THỐNG (SYSTEM PARAMETERS) ---
        # Mô hình gốc: 5 periods, 4 stages, mỗi period = 12 ngày (Table 5)
        self.T = 5           # Số kỳ
        self.K = 4           # Số cấp
        self.period_days = 12

        # Lead times (Độ trễ vận chuyển giữa các stage)
        # Chỉ có luồng từ Stage 2 -> Stage 3 là có lead time = 1 period (paper Section 5)
        # Các luồng khác giả sử lead time = 0.
        self.lead_times = {
            (1, 2): 0,
            (2, 3): 1,   # quan trọng: 2->3 mất 1 kỳ
            (3, 4): 0
        }

        # Tồn kho ban đầu (Initial Inventory) tại t = 0
        # Paper: chỉ có Stage 4 có 100 units, các stage khác 0.
        self.initial_inventory = {1: 0, 2: 0, 3: 0, 4: 100}

        # (Nếu cần target tồn kho cuối kỳ, paper cho stage 1–3 = 0, stage 4 cũng thường = 0)
        self.ending_inventory_target = {1: 0, 2: 0, 3: 0, 4: 0}

        # --- 2. DỮ LIỆU VẬN HÀNH (OPERATIONS DATA) - Table 5 ---
        # Dùng list index 0..4 tương ứng Period 1..5 cho tiện giữ style ban đầu

        # Nhu cầu tại Stage 4 (Demand) – Table 5
        self.demand = [100, 200, 250, 300, 200]

        # Chi phí sản xuất tại Stage 1 – fixed & variable – Table 5
        self.prod_fixed_cost = [2500, 2500, 3000, 3000, 3500]
        self.prod_var_cost   = [10,   10,   12,   12,   13]

        # Chi phí tồn kho (holding cost) – Table 5 (giả sử như nhau cho mọi stage)
        self.holding_cost = [5, 5, 5, 6, 6]

        # Năng lực (Capacities) – CHUẨN THEO TABLE 5
        # Inventory capacity: 200 units/period cho tất cả các stages
        self.inventory_capacity = 200

        # Production capacity tại Stage 1: 270 units/period cho cả 5 kỳ (Table 5)
        self.prod_capacity = [270, 270, 270, 270, 270]

        # Transportation capacity (giữa các stage): 300 units/period cho cả 5 kỳ (Table 5)
        self.trans_capacity = [300, 300, 300, 300, 300]

        # --- 3. DỮ LIỆU NHÀ CUNG CẤP (SUPPLIERS DATA) ---
        # Từ Table 3 & Table 4 + mô tả text: tách Supplier 1 thành 2 "offers" (ảo)

        # Tham số chung từ Table 4:
        self.global_min_order_first  = 50   # minimal quantity for first order
        self.global_min_order_later  = 20   # minimal quantity for subsequent orders
        self.global_max_order_size   = 500  # capacity of each order (Q̄_j)

        # Danh sách suppliers ảo
        self.suppliers = [
            {
                "name": "Sup1_Offer1",
                # Cumulative capacity theo period – Table 3
                # Offer 1 hiệu lực Period 1–2, sau đó = 0 để "khóa" offer này
                "cumulative_capacity": [300, 450, 450, 450, 450],
                # Ordering cost – Table 4
                "primary_cost": 550,
                "secondary_cost": 1000,
                # Min order quantity
                "min_order": 50,          # lần đầu
                "min_order_later": 20,    # các lần sau
                "max_order_per_order": 500,
                # PRICE BREAK SCHEME (giữ đúng cấu trúc bạn đã dùng)
                "price_intervals": [
                    {"max_q": 50,  "price": 95},
                    {"max_q": 150, "price": 80},
                    {"max_q": 300, "price": 70},
                    {"max_q": 450, "price": 60}
                ]
            },
            {
                "name": "Sup1_Offer2",
                # Cumulative capacity – Table 3 (bắt đầu từ Period 3)
                "cumulative_capacity": [0,   0,   50,  150, 400],
                "primary_cost": 550,
                "secondary_cost": 1000,
                "min_order": 50,
                "min_order_later": 20,
                "max_order_per_order": 500,
                "price_intervals": [
                    {"max_q": 150, "price": 95},
                    {"max_q": 250, "price": 80},
                    {"max_q": 400, "price": 70}
                ]
            },
            {
                "name": "Sup2",
                # Cumulative capacity – Table 3
                "cumulative_capacity": [200, 400, 650, 900, 1200],
                "primary_cost": 500,
                "secondary_cost": 1000,
                "min_order": 50,
                "min_order_later": 20,
                "max_order_per_order": 500,
                # Giá Sup2 cao hơn Sup1 – intervals bám cumulative capacity
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
                # Cumulative capacity – Table 3
                "cumulative_capacity": [100, 100, 400, 400, 1000],
                "primary_cost": 600,
                "secondary_cost": 1050,
                "min_order": 50,
                "min_order_later": 20,
                "max_order_per_order": 500,
                "price_intervals": [
                    {"max_q": 100,  "price": 110},
                    {"max_q": 400,  "price": 80},
                    {"max_q": 1000, "price": 60}
                ]
            }
        ]

        # --- 4. DỮ LIỆU CƯỚC VẬN CHUYỂN (FREIGHT RATES) - Table 6 ---
        # 4.1. Nominal freight rates (all-unit discount) – dùng nếu muốn để mô hình tự over-declare
        self.freight_nominal = [
            # Interval 1: 1–31 units, fixed 519$
            {"min": 1,   "max": 31,  "fixed_cost": 519, "var_cost_per_unit": 0.0},
            # Interval 2: 32–62 units, 16.2$/unit
            {"min": 32,  "max": 62,  "fixed_cost": 0.0, "var_cost_per_unit": 16.2},
            # Interval 3: 63–124 units, 12.5$/unit
            {"min": 63,  "max": 124, "fixed_cost": 0.0, "var_cost_per_unit": 12.5},
            # Interval 4: 125–312 units, 11.3$/unit
            {"min": 125, "max": 312, "fixed_cost": 0.0, "var_cost_per_unit": 11.3}
        ]

        # 4.2. Actual freight rates (sau khi over-declaring) – đúng Table 6
        # Dùng nếu bạn muốn khớp tối đa kết quả trong bài.
        self.freight_actual = [
            # 1–31 units: fixed 519$
            {"min": 1,   "max": 31,  "fixed_cost": 519,  "var_cost_per_unit": 0.0},
            # 32–48 units: 16.2$/unit
            {"min": 32,  "max": 48,  "fixed_cost": 0.0,  "var_cost_per_unit": 16.2},
            # 49–62 units: fixed 789$
            {"min": 49,  "max": 62,  "fixed_cost": 789,  "var_cost_per_unit": 0.0},
            # 63–112 units: 12.5$/unit
            {"min": 63,  "max": 112, "fixed_cost": 0.0,  "var_cost_per_unit": 12.5},
            # 113–124 units: fixed 1411$
            {"min": 113, "max": 124, "fixed_cost": 1411, "var_cost_per_unit": 0.0},
            # 125–254 units: 11.3$/unit
            {"min": 125, "max": 254, "fixed_cost": 0.0,  "var_cost_per_unit": 11.3},
            # 255–312 units: fixed 2876$
            {"min": 255, "max": 312, "fixed_cost": 2876, "var_cost_per_unit": 0.0}
        ]


# --- QUICK CHECK ---
if __name__ == "__main__":
    data = SupplyChainData()
    print("✅ Data (chuẩn paper) loaded.")
    print(f"Periods (T): {data.T}")
    print(f"Stages (K): {data.K}")
    print(f"Demand profile: {data.demand}")
    print(f"Prod capacity per period: {data.prod_capacity}")
    print(f"Trans capacity per period: {data.trans_capacity}")
    print(f"Inventory capacity: {data.inventory_capacity}")
    print(f"Suppliers: {[s['name'] for s in data.suppliers]}")
    print(f"Nominal freight intervals: {[(f['min'], f['max']) for f in data.freight_nominal]}")
    print(f"Actual freight intervals: {[(f['min'], f['max']) for f in data.freight_actual]}")
