# Sensitivity Analysis - Procedural Version

## Mục đích

Phân tích độ nhạy của MILP model khi thay đổi tham số **m** (hệ số chia nhỏ thời gian).

## Cấu trúc

```
Sensitivity_Procedural/
├── data_loader.py              # Data với tham số m
├── dynamic_scm_procedural.py   # Model (procedural style)
└── run_sensitivity.py          # Script chạy 4 scenarios
```

## Tham số m

- **m = 1**: 5 periods (baseline)
- **m = 2**: 10 periods (chia đôi mỗi period)
- **m = 3**: 15 periods
- **m = 4**: 20 periods

### Điều chỉnh khi m thay đổi:

1. **Demand**: Giữ nguyên tổng, dồn về cuối sub-period (mode='Pm')
2. **Holding cost**: Giảm m lần (thời gian ngắn hơn)
3. **Production fixed cost**: **CHIA m** (quan trọng!)
4. **Production variable cost**: Giữ nguyên
5. **Capacities**: Giảm m lần
6. **Lead time**: Tăng m lần
7. **Supplier costs**: Primary & Secondary chia m

## Cách chạy

```bash
cd Sensitivity_Procedural
python run_sensitivity.py
```

## Kết quả mong đợi

```
m   | Model | Periods | Objective Cost | CPU Time (s)
----|-------|---------|----------------|-------------
1   | Pm    | 5       |    141,274 $   |     X.XXXX
2   | Pm    | 10      |    XXX,XXX $   |     X.XXXX
3   | Pm    | 15      |    XXX,XXX $   |     X.XXXX
4   | Pm    | 20      |    XXX,XXX $   |     X.XXXX
```

## So sánh với OOP version

| Version | Folder | Style |
|---------|--------|-------|
| OOP | `Sensitivity/` | Class-based |
| **Procedural** | **`Sensitivity_Procedural/`** | **Function-based** |

Cả 2 cho **kết quả giống nhau**!

## Notes

- Code dễ đọc hơn (tuần tự từ trên xuống)
- Mỗi function độc lập
- Dễ debug từng bước
