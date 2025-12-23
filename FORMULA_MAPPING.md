# 📐 GIẢI THÍCH CÔNG THỨC TOÁN HỌC - INVENTORY MILP MODEL

## Mapping Code → Mathematical Formulas

Tài liệu này giải thích cách code implementation map với các công thức toán học trong paper.

---

## 1. HÀM MỤC TIÊU (OBJECTIVE FUNCTION) - Eq. (15)

### Công thức tổng quát:
```
Min Z = (1) + (2) + (3) + (4) + (5)
```

### (1) CHI PHÍ MUA HÀNG (Purchasing Cost)
**Công thức:** `∑_{j∈J} ∑_{g=1}^{m_j} {s_{gj}C_{gj} + P_{gj}r_{gj}}`

**Code implementation:**
```python
for j_idx, supplier in enumerate(self.data.suppliers):
    intervals = supplier['price_intervals']
    for g, interval in enumerate(intervals):
        base_cost = 0  # C_{gj}
       for pg in range(g):
            w = intervals[pg]['max_q'] - (0 if pg==0 else intervals[pg-1]['max_q'])
            base_cost += w * intervals[pg]['price']
        
        # s_{gj} * C_{gj} + P_{gj} * r_{gj}
        total += (self.s_price[j_idx, g] * base_cost + 
                 self.r_price[j_idx, g] * interval['price'])
```

**Giải thích:**
- `C_{gj}` (base_cost): Tổng chi phí các khoảng giá trước g
- `P_{gj}`: Giá đơn vị của khoảng g (`interval['price']`)
- `r_{gj}`: Phần dư trong khoảng g (`self.r_price[j_idx, g]`)
- `s_{gj}`: Binary (1 nếu chọn khoảng g) (`self.s_price[j_idx, g]`)

### (2) CHI PHÍ ĐẶT HÀNG (Ordering Cost)
**Công thức:** `∑_{j∈J} (∑_{g=1}^{m_j} M_j*s_{gj} + N_j*∑_{t∈T₁} z_j^t)`

**Code:**
```python
# M_j * ∑ s_{gj} (Primary cost)
is_selected = sum(self.s_price[j_idx, g] for g in range(len(intervals)))
total += supplier['primary_cost'] * is_selected

# N_j * ∑ z_j^t (Secondary cost)
for t in range(T): 
    total += supplier['secondary_cost'] * self.z[j_idx, t]
```

### (3) CHI PHÍ SẢN XUẤT (Production Cost)
**Công thức:** `∑_{t∈T₁} (c_1^t*x_1^t + f_1^t*w_1^t)`

**Code:**
```python
for t in range(T):
    total += self.data.prod_fixed_cost[t] * self.w_prod[t]  # f_1^t * w_1^t
    total += self.data.prod_var_cost[t] * self.x[t]          # c_1^t * x_1^t
```

### (4) CHI PHÍ LƯU KHO (Holding Cost)
**Công thức:** `∑_{k∈K} ∑_{t∈T_k} h_k^t*i_k^t + ∑_{k∈K_D} ∑_{t∈T_k} u_k^t*y_k^t`

**Code:**
```python
for t in range(T):
    # Phần 1: Node Inventory
    for k in range(1, self.data.K + 1):
        total += self.data.holding_cost[t] * self.i[k, t]  # h_k^t * i_k^t
    
    # Phần 2: In-transit Inventory (K_D = {2, 3})
    for k in [2, 3]:
        total += self.y[k, t] * self.data.holding_cost[t]  # u_k^t * y_k^t
```

### (5) CHI PHÍ VẬN CHUYỂN (Transportation Cost)
**Công thức:** `∑_{k∈K_D} ∑_{t∈T_k} ∑_{e∈E} (β_{k0}*f_{ke}^t + β_{ke}*y_{ke}^t)`

**Code:**
```python
for t in range(T):
    for k in range(3, self.data.K):
        for e, iv in enumerate(transport_intervals):
            total += iv['fixed_cost'] * self.f_freight[k, t, e]           # β_{k0} * f
            total += iv['var_cost_per_unit'] * self.y_freight[k, t, e]   # β_{ke} * y
```

---

## 2. RÀNG BUỘC (CONSTRAINTS)

### A. RÀNG BUỘC NHÀ CUNG CẤP

#### Eq. (18), (19): Quy mô đơn hàng (Order Size)
**Công thức:** `z_j^t * o_j ≤ q_j^t ≤ z_j^t * R_j`

**Code:**
```python
# Min order: q >= o_j * z
self.solver.Add(qty >= supplier['min_order'] * self.z[j_idx, t])

# Max order: q <= R_j * z
self.solver.Add(qty <= self.data.global_max_order_size * self.z[j_idx, t])
```

#### Eq. (16), (17): Năng lực tích lũy (Cumulative Capacity)
**Công thức:** `∑_{t'=1}^{t} q_j^{t'} ≤ Q'_{tj}`

**Code:**
```python
total_purchased_cumulative += qty  # ∑ q_j^{t'}
self.solver.Add(total_purchased_cumulative <= supplier['cumulative_capacity'][t])  # ≤ Q'_{tj}
```

#### Eq. (21)-(26): Cơ chế giá lũy tiến (Price Break Scheme)
**Công thức:** 
- `∑_{g=1}^{m_j} s_{gj} ≤ 1`
- `∑_{t∈T₁} q_j^t = ∑_{g=1}^{m_j} (s_{gj}*Q_{g-1,j} + r_{gj})`

**Code:**
```python
# Eq. (21): Chọn tối đa 1 khoảng giá
self.solver.Add(sum(self.s_price[j_idx, g] for g in range(len(intervals))) <= 1)

# Eq. (22), (23)
expr_qty = 0
for g, interval in enumerate(intervals):
    lower = 0 if g == 0 else intervals[g-1]['max_q']  # Q_{g-1,j}
    width = interval['max_q'] - lower
    
    # r_{gj} ≤ width * s_{gj}
    self.solver.Add(self.r_price[j_idx, g] <= width * self.s_price[j_idx, g])
    
    # s_{gj}*Q_{g-1,j} + r_{gj}
    expr_qty += (self.s_price[j_idx, g] * lower + self.r_price[j_idx, g])

# ∑ q = ∑ (s*Q + r)
self.solver.Add(total_qty_horizon == expr_qty)
```

### B. RÀNG BUỘC CÂN BẰNG DÒNG CHẢY (FLOW BALANCE)

#### Eq. (27): Stage 1 (Manufacturing)
**Công thức:** `∑_{j∈J} q_j^t + i_1^{t-1} = x_1^t + i_1^t`

**Code:**
```python
in_1 = sum(self.q[j, t] for j in range(len(self.data.suppliers)))  # ∑ q_j^t
prev_1 = self.data.initial_inventory[1] if t == 0 else self.i[1, t-1]  # i_1^{t-1}
self.solver.Add(in_1 + prev_1 == self.x[t] + self.i[1, t])
```

#### Eq. (28): Stage 2 (Local Warehouse)
**Công thức:** `x_1^t + i_2^{t-1} = y_2^t + i_2^t`

**Code:**
```python
prev_2 = self.data.initial_inventory[2] if t == 0 else self.i[2, t-1]
self.solver.Add(self.x[t] + prev_2 == self.y[2, t] + self.i[2, t])
```

#### Eq. (29): Stage k với Lead Time
**Công thức:** `y_{k-1}^{t-l_{k-1}} + i_k^{t-1} = y_k^t + i_k^t`

**Code:**
```python
# Stage 3: Lead time = 1
in_3 = 0
lt = self.data.lead_times[(2,3)]  # l_{k-1}
if t >= lt: 
    in_3 = self.y[2, t - lt]  # y_{k-1}^{t-l}

prev_3 = self.data.initial_inventory[3] if t == 0 else self.i[3, t-1]
self.solver.Add(in_3 + prev_3 == self.y[3, t] + self.i[3, t])
```

#### Eq. (30): Stage n_K (Customer)
**Công thức:** `y_{n_K-1}^{t-l} + i_{n_K}^{t-1} = d^t + i_{n_K}^t`

**Code:**
```python
prev_4 = self.data.initial_inventory[4] if t == 0 else self.i[4, t-1]
self.solver.Add(self.y[3, t] + prev_4 == self.data.demand[t] + self.i[4, t])  # d^t
```

### C. RÀNG BUỘC NĂNG LỰC (CAPACITY)

#### Eq. (31): Năng lực sản xuất
**Công thức:** `x_1^t ≤ b_1^t * w_1^t`

**Code:**
```python
self.solver.Add(self.x[t] <= self.data.prod_capacity[t] * self.w_prod[t])
```

#### Eq. (32): Năng lực vận chuyển
**Công thức:** `y_k^t ≤ b_k^t * w_k^t`

**Code:**
```python
self.solver.Add(self.y[2, t] <= self.data.trans_capacity[t] * self.w_trans[2, t])
self.solver.Add(self.y[3, t] <= self.data.trans_capacity[t] * self.w_trans[3, t])
```

#### Eq. (33): Sức chứa kho
**Công thức:** `i_k^t ≤ e_k`

**Code:**
```python
# Enforced trong variable domain
self.i[k, t] = self.solver.NumVar(0, self.data.inventory_capacity, f'i_{k}_{t}')
```

### D. RÀNG BUỘC CƯỚC VẬN CHUYỂN (FREIGHT RATE)

#### Eq. (34), (35): Bounds cho freight interval
**Công thức:**
- `y_{ke}^t ≥ f_{ke}^t * α_{ke-1}`
- `y_{ke}^t ≤ f_{ke}^t * α_{ke}`

**Code:**
```python
self.solver.Add(self.y_freight[k, t, e] >= iv['min'] * self.f_freight[k, t, e])  # ≥ α_{ke-1}
self.solver.Add(self.y_freight[k, t, e] <= iv['max'] * self.f_freight[k, t, e])  # ≤ α_{ke}
```

#### Eq. (36), (37): Freight selection
**Công thức:**
- `∑_{e∈E} f_{ke}^t ≤ 1`
- `∑_{e∈E} y_{ke}^t = y_k^t`

**Code:**
```python
# Chọn tối đa 1 khoảng cước
self.solver.Add(sum(self.f_freight[k, t, e] for e in range(len(intervals))) <= 1)

# Tổng quantity trong các khoảng = Total quantity
self.solver.Add(sum(self.y_freight[k, t, e] for e in range(len(intervals))) == self.y[k, t])
```

---

## TÓM TẮT BIẾN QUYẾT ĐỊNH (DECISION VARIABLES)

| Ký hiệu  | Code Variable | Loại | Mô tả |
|----------|---------------|------|-------|
| q_j^t    | self.q[j,t]   | Continuous | Số lượng mua từ NCC j trong kỳ t |
| z_j^t    | self.z[j,t]   | Binary | 1 nếu đặt hàng từ NCC j trong kỳ t |
| x_k^t    | self.x[t]     | Continuous | Sản lượng sản xuất kỳ t |
| w_k^t    | self.w_prod[t] | Binary | 1 nếu sản xuất trong kỳ t |
| y_k^t    | self.y[k,t]   | Continuous | Lượng vận chuyển từ stage k kỳ t |
| i_k^t    | self.i[k,t]   | Continuous | Tồn kho tại stage k cuối kỳ t |
| s_{gj}   | self.s_price[j,g] | Binary | 1 nếu chọn khoảng giá g của NCC j |
| r_{gj}   | self.r_price[j,g] | Continuous | Phần dư trong khoảng giá g |
| f_{ke}^t | self.f_freight[k,t,e] | Binary | 1 nếu chọn khoảng cước e |
| y_{ke}^t | self.y_freight[k,t,e] | Continuous | Lượng hàng trong khoảng cước e |

---

