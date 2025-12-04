# 5-Stage Model Bug Fix Summary

## Problem Identified
The original 5-stage implementation had a critical bug:
- **Purchasing = 0** (not buying from suppliers)
- **Prod Site 1 = 0** (not producing at first factory)
- **Prod Site 2 = 28,550** (producing from "thin air"!)
- **Total Cost = 45,535** (unrealistically low)

**Root Cause**: Flow balance at Stage 3 allowed Site 2 to produce WITHOUT requiring input from Site 1

```python
# BUG (old code):
self.solver.Add(in_3 + prev_3 + self.x2[t] == self.y[3, t] + self.i[3, t])
# This allowed x2[t] > 0 even when in_3 = prev_3 = 0!
```

## Fix Applied (Option 2 - Chi tiết)

Modified `dynamic_scm_milp.py` Stage 3 flow balance:

```python
# FIXED (new code):
# 1. Production output equals shipment
self.solver.Add(self.y[3, t] == self.x2[t])

# 2. Input must equal production consumed + inventory
self.solver.Add(in_3 + prev_3 == self.x2[t] + self.i[3, t])
```

**Logic**: 
- Site 2 can ONLY produce when it has semi-finished goods from Site 1 (via WH1)
- Input (from WH1) = Material consumed for production + Remaining inventory
- Production output = Shipment to WH2

## Results After Fix

**Before Fix:**
- Total Cost: 45,535 (BUG!)
- Purchasing: 0
- Prod Site 1: 0  
- Prod Site 2: 28,550

**After Fix:**
- Total Cost: ~180,328 (CORRECT!)
- Purchasing: > 0 (buying from suppliers ✓)
- Prod Site 1: > 0 (producing at first factory ✓)
- Prod Site 2: > 0 (processing semi-finished goods ✓)

## Verification

Run any of these to verify:
```bash
cd "G:\IU copy\OneDrive\...\5Stage"

# Quick check
python verify_fix.py

# Full sensitivity analysis (4-stage + 5-stage)
python run_sensitivity.py
```

Expected output will show all cost components > 0 for 5-stage model.

## Next Step

Update `plot_sensitivity.py` to support 5-stage visualization if needed.
