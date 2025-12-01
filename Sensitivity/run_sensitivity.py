import time
from data_loader import SupplyChainData
from dynamic_scm_milp import SupplyChainModel

def run_analysis():
    # Danh sách các giá trị m cần test
    m_values = [1, 2, 3, 4]
    results = []

    print(f"{'m':<3} | {'Model':<5} | {'Periods':<7} | {'Objective Cost':<15} | {'CPU Time (s)':<12}")
    print("-" * 55)

    for m in m_values:
        # 1. Khởi tạo dữ liệu với m tương ứng, chế độ 'Pm'
        data = SupplyChainData(m=m, mode='Pm')
        
        # 2. Khởi tạo mô hình
        model = SupplyChainModel(data)
        
        # 3. Xây dựng và giải
        start_time = time.time()
        
        model.create_variables()
        model.add_constraints()
        model.set_objective()
        
        # Tắt in chi tiết để gọn màn hình (nếu muốn)
        # model.solver.EnableOutput(False) 
        
        model.solve()
        end_time = time.time()
        
        duration = end_time - start_time
        
        # 4. Lấy kết quả
        if model.solver.Objective().Value() > 0:
            obj_val = model.solver.Objective().Value()
        else:
            obj_val = float('inf') # Không tìm thấy nghiệm

        print(f"{m:<3} | {'Pm':<5} | {data.T:<7} | {obj_val:,.0f} {'$':<3} | {duration:.4f}")
        results.append((m, obj_val, duration))

    print("-" * 55)
    print("DONE SENSITIVITY ANALYSIS.")

if __name__ == "__main__":
    run_analysis()