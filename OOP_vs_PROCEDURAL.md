# 📊 OOP vs PROCEDURAL Comparison

## Tổng Quan

Project này có **2 implementations** của cùng 1 MILP model:
- **FIXED/**: Object-Oriented Programming (OOP) - Dùng Class
- **PROCEDURAL/**: Procedural Programming - Dùng Functions

---

## 🔍 So Sánh Chi Tiết

### 1. KIẾN TRÚC CODE

#### **OOP Version (FIXED/)**
```python
class SupplyChainModel:
    def __init__(self, data):
        self.data = data
        self.solver = ...
        self.q = {}  # Instance variables
        
    def create_variables(self):
        # Access via self
        self.q[j, t] = self.solver.NumVar(...)
        
    def add_constraints(self):
        # Access instance variables
        self.solver.Add(self.q[j, t] >= ...)
```

**Đặc điểm:**
- ✅ Encapsulation: Data và methods gói trong class
- ✅ State management: Instance variables
- ✅ Reusable: Có thể tạo nhiều instances
- ❌ Phức tạp hơn cho người mới

#### **Procedural Version (PROCEDURAL/)**
```python
def create_variables(solver, data):
    q = {}  # Local variable
    q[j, t] = solver.NumVar(...)
    return {'q': q, 'z': z, ...}  # Return dict

def add_constraints(solver, data, vars):
    q = vars['q']  # Extract from dict
    solver.Add(q[j, t] >= ...)
```

**Đặc điểm:**
- ✅ Đơn giản, dễ hiểu
- ✅ Sequential workflow rõ ràng
- ✅ Dễ debug (mỗi function độc lập)
- ❌ Pass parameters nhiều lần

---

### 2. WORKFLOW SO SÁNH

| Step | OOP | Procedural |
|------|-----|------------|
| **1. Initialize** | `model = SupplyChainModel(data)` | `solver = create_solver()` |
| **2. Variables** | `model.create_variables()` | `vars = create_variables(solver, data)` |
| **3. Constraints** | `model.add_constraints()` | `add_supplier_constraints(...)`<br>`add_flow_balance_constraints(...)`<br>... |
| **4. Objective** | `model.set_objective()` | `set_objective(solver, data, vars)` |
| **5. Solve** | `model.solve()` | `solve_and_display(solver, data, vars)` |

---

### 3. CÁCH TỔ CHỨC CODE

#### **OOP**: Gộp theo Object
```
SupplyChainModel
├── __init__()
├── create_variables()
├── add_constraints()      # Tất cả constraints trong 1 method
├── set_objective()
└── solve()
```

#### **Procedural**: Chia nhỏ theo chức năng
```
main()
├── create_solver()
├── create_variables()
├── add_supplier_constraints()      # Tách riêng
├── add_flow_balance_constraints()  # Tách riêng
├── add_freight_constraints()       # Tách riêng
├── add_ending_inventory_constraints()
├── set_objective()
└── solve_and_display()
```

---

### 4. VARIABLE MANAGEMENT

#### **OOP**: Instance Variables
```python
class SupplyChainModel:
    def __init__(self):
        self.q = {}  # Lưu trong instance
        
    def create_variables(self):
        self.q[j, t] = ...  # Gán vào self
        
    def add_constraints(self):
        # Truy cập trực tiếp
        self.solver.Add(self.q[j, t] >= ...)
```

#### **Procedural**: Return & Pass
```python
def create_variables(solver, data):
    q = {}  # Local variable
    q[j, t] = ...
    return {'q': q, ...}  # Return dictionary

def add_constraints(solver, data, vars):
    q = vars['q']  # Extract from dict
    solver.Add(q[j, t] >= ...)
```

---

### 5. ƯU ĐIỂM / NHƯỢC ĐIỂM

| Tiêu chí | OOP | Procedural |
|----------|-----|------------|
| **Dễ hiểu** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Tổ chức code** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Reusability** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Debugging** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Memory** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Scalability** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |

---

### 6. KHI NÀO DÙNG GÌ?

#### **Chọn OOP nếu:**
- ✅ Cần tạo nhiều instances khác nhau
- ✅ Model phức tạp với nhiều state
- ✅ Muốn kế thừa/extend model
- ✅ Team đã quen OOP
- ✅ Project lớn, dài hạn

#### **Chọn Procedural nếu:**
- ✅ Model đơn giản, chạy 1 lần
- ✅ Người mới học MILP
- ✅ Muốn code dễ đọc, tuần tự
- ✅ Script nhỏ, rapid prototyping
- ✅ Dễ debug từng bước

---

## 📈 PERFORMANCE

Cả 2 versions:
- ✅ Cho **cùng objective value**
- ✅ Cùng solve time
- ✅ Cùng purchasing plan

**Lý do:** Cả 2 đều tạo CÙNG mathematical model cho SCIP!

---

## 🎯 KẾT LUẬN

| Aspect | Winner |
|--------|--------|
| **Professional** | OOP ⭐ |
| **Beginner-friendly** | Procedural ⭐ |
| **Teaching** | Procedural ⭐ |
| **Production** | OOP ⭐ |
| **Quick script** | Procedural ⭐ |
| **Large project** | OOP ⭐ |

**Recommendation:**
- 📚 **Học tập / Present**: Dùng **Procedural** (dễ hiểu)
- 🏭 **Production / Research**: Dùng **OOP** (professional)
- 🔀 **Flexibility**: Giữ cả 2! (như project này)

---

## 📂 FILE STRUCTURE

```
Price_Scheme/
├── FIXED/                    # OOP Version
│   ├── data_loader.py
│   └── dynamic_scm_milp.py   # Class-based
│
├── PROCEDURAL/               # Procedural Version
│   ├── data_loader.py
│   └── dynamic_scm_procedural.py   # Function-based
│
└── OOP_vs_PROCEDURAL.md      # This file
```

---

## 🚀 USAGE

**OOP Version:**
```bash
cd FIXED
python dynamic_scm_milp.py
```

**Procedural Version:**
```bash
cd PROCEDURAL
python dynamic_scm_procedural.py
```

Both will produce identical output! ✅
