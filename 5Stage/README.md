# 5-Stage Supply Chain Model

Mô hình chuỗi cung ứng 5 tầng với 2 xưởng sản xuất, hỗ trợ cả 4-stage và 5-stage.

## Cấu trúc 5-Stage

```
Stage 1: Production Site 1 (Mfg1)
   ↓
Stage 2: Local Warehouse 1 (WH1)
   ↓ (Lead Time = 1 period)
Stage 3: Production Site 2 (Mfg2)  ← Xử lý bán thành phẩm từ Site 1
   ↓
Stage 4: Local Warehouse 2 (WH2)
   ↓
Stage 5: Regional WH / Customer (Demand)
```

## Files Chính

### 1. `data_loader.py`
- Quản lý dữ liệu cho model
- **Tham số:** `num_stages=4 hoặc 5`
- Chứa thông số cho 2 production sites

### 2. `dynamic_scm_milp.py`
- Model optimization chính (MILP)
- Tự động điều chỉnh theo số stage
- **Bug fix:** Site 2 chỉ xử lý bán thành phẩm từ Site 1

### 3. `run_sensitivity.py`
- Chạy sensitivity analysis
- Test: m=1,2,3,4 cho 4-stage; m=1,2 cho 5-stage
- Output: Cost breakdown và purchasing plan

### 4. `plot_sensitivity.py`
- Tạo biểu đồ visualization
- Hỗ trợ cả 4-stage và 5-stage
- Charts: Cost breakdown, Purchasing, Production split

## Cách Chạy

### 1. Chạy Sensitivity Analysis

```bash
# Chạy cả 4-stage và 5-stage
python run_sensitivity.py
```

**Output:**
- Bảng cost breakdown theo m
- Bảng purchasing plan
- Hiển thị separate cho 4-stage và 5-stage

### 2. Tạo Biểu Đồ

```bash
# Tự động chạy cả 4-stage và 5-stage
python plot_sensitivity.py

# Hoặc chỉ chạy 1 loại:
python plot_sensitivity.py 4    # Chỉ 4-stage
python plot_sensitivity.py 5    # Chỉ 5-stage
```

**Output files:**
- `4stage_*.png` - Biểu đồ cho 4-stage
- `5stage_*.png` - Biểu đồ cho 5-stage
  - `5stage_production_split.png` - Phân tách Site 1 vs Site 2

### 3. Test Nhanh

```bash
# Kiểm tra bug đã fix chưa
python verify_fix.py

# Test cả 2 models
python quick_test.py
```

## Các Biểu Đồ Được Tạo

1. **Cost Breakdown** (Pm & Pmd)
   - Purchasing, Production, Holding, Transport, Total

2. **Purchasing Strategy** (Pm & Pmd)
   - Cumulative order quantity theo supplier

3. **Production Split** (chỉ 5-stage)
   - So sánh Site 1 vs Site 2

4. **Comparison Charts**
   - Cost breakdown: Pm vs Pmd
   - Purchasing: Pm vs Pmd
   - Total cost: Pm vs Pmd

## Kết Quả Mong Đợi

### 4-Stage (m=1, mode=Pm)
```
Purchasing:   ~95,000
Production:   ~22,500
Holding:      ~10,000
Transport:    ~11,000
Total:        ~138,500
```

### 5-Stage (m=1, mode=Pm) - SAU KHI FIX BUG
```
Purchasing:   > 0
Prod Site 1:  > 0
Prod Site 2:  > 0
Total:        ~180,000 (cao hơn 4-stage vì có 2 sites)
```

## Bug Fix Log

**Vấn đề:** Site 2 sản xuất mà không cần nguyên liệu từ Site 1

**Giải pháp:**
```python
# Thêm constraint:
self.solver.Add(self.y[3, t] == self.x2[t])
self.solver.Add(in_3 + prev_3 == self.x2[t] + self.i[3, t])
```

**Kết quả:** Site 2 giờ CHỈ có thể xử lý khi có bán thành phẩm từ Site 1 ✓

## Tham Khảo Paper

- **Table 12**: Production cost & capacity cho 2 sites
- **Table 13**: Expected results cho 5-stage, m=1,2
- **Table 14-15**: Freight configuration cho 2 legs (2→3, 4→5)

## Lưu Ý

1. **5-stage chỉ test m=1,2** (theo paper)
2. **Freight áp dụng cho 2 legs** trong 5-stage (2→3 và 4→5)
3. **Lead time chỉ có ở 2→3** (1 period)
4. **Initial inventory:** Stage cuối = 100, còn lại = 0
5. **Ending inventory:** Stage cuối = 100, còn lại = 0

## Debug Scripts

- `debug_5stage.py` - Chi tiết production & inventory flow
- `verify_fix.py` - Kiểm tra bug đã fix
- `fix_stage3.py` - Script đã dùng để fix bug
- `BUG_FIX_SUMMARY.md` - Tóm tắt bug fix

---

**Last updated:** 2025-12-05  
**Status:** ✓ Bug fixed, fully functional
