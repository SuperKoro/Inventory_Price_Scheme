# 📦 Supply Chain Optimization - Multi-Stage MILP Models

Comprehensive supply chain management optimization using **Mixed Integer Linear Programming (MILP)** to find optimal purchasing, production, and transportation plans with minimum total cost. This project implements **3-stage, 4-stage, and 5-stage** supply chain models with sensitivity analysis capabilities.

---

## 🎯 Problem Overview

This project solves **multi-stage, multi-period supply chain optimization problems** with:

- **Multiple Suppliers** (with quantity discounts and time-limited offers)
- **K Stages**: Suppliers → Regional Warehouses → Production Sites → Customer
- **Time Periods**: Configurable planning horizon (5 base periods, expandable with parameter `m`)
- **Objective**: **Minimize total cost** while satisfying customer demand

### Supply Chain Stages

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────┐
│  Suppliers  │ ──▶ │  Warehouse 1 │ ──▶ │  Warehouse 2 │ ──▶ │ Customer │
│   (K=1)     │     │    (K=2)     │     │    (K=3)     │     │  (K=4)   │
└─────────────┘     └──────────────┘     └──────────────┘     └──────────┘
   Purchasing        Production          Transportation         Demand
                     Holding             Lead Time = m
```

---

## 📊 Cost Components

The model minimizes the following costs:

1. **Purchasing Cost**: Raw material cost from suppliers + ordering fees (with price break schemes)
2. **Production Cost**: Fixed setup cost + variable production cost per unit
3. **Holding Cost**: Inventory holding at warehouses + in-transit inventory
4. **Transportation Cost**: Freight rates with quantity-based discounts

---

## 📁 Project Structure

```
Price_Scheme/
│
├── 📂 Basemodel/                    # Original base implementation
│   ├── data_loader.py               # Base data parameters
│   └── dynamic_scm_procedural.py    # Procedural approach
│
├── 📂 Sensitivity/                  # 4-Stage MILP Sensitivity Analysis
│   ├── data_loader.py               # Data loader with parameter m
│   ├── dynamic_scm_milp.py          # 4-stage MILP model
│   ├── run_sensitivity.py           # Main sensitivity analysis script
│   ├── plot_sensitivity.py          # Visualization tools
│   └── *.png                        # Generated plots
│
├── 📂 3Stage/                       # 3-Stage Model (removes 1 warehouse)
│   ├── data_loader.py               # 3-stage data configuration
│   ├── dynamic_scm_milp.py          # 3-stage MILP model
│   ├── run_sensitivity.py           # 3-stage sensitivity analysis
│   └── plot_sensitivity.py          # Plotting tools
│
├── 📂 5Stage/                       # 5-Stage Model (adds production site)
│   ├── data_loader.py               # 5-stage data configuration
│   ├── dynamic_scm_milp.py          # 5-stage MILP model with 2 production sites
│   ├── run_sensitivity.py           # 5-stage sensitivity analysis
│   ├── plot_sensitivity.py          # Plotting tools
│   ├── BUG_FIX_SUMMARY.md          # Bug fixes documentation
│   └── README.md                    # 5-stage specific documentation
│
├── 📂 Sai_Theorem3/                 # Theorem 3 validation
│   ├── data_loader.py               # Special test data
│   └── *.py                         # Validation scripts
│
├── 📄 FORMULA_MAPPING.md            # Mathematical formulas ↔ Code mapping
├── 📄 README.md                     # This file
└── *.png                            # Generated comparison plots
```

---

## 🚀 Quick Start

### Prerequisites

```bash
pip install ortools matplotlib numpy
```

### 1️⃣ Run 4-Stage Sensitivity Analysis (MILP)

```bash
cd Sensitivity
python run_sensitivity.py
```

**Output:** Console table + cost breakdown + purchasing plans for `m = [1, 2, 3, 4]`

### 2️⃣ Generate Visualization Plots

```bash
cd Sensitivity
python plot_sensitivity.py
```

**Output:** PNG files showing cost breakdown, purchasing strategy, and Pm vs Pmd comparisons

### 3️⃣ Run 5-Stage Model

```bash
cd 5Stage
python run_sensitivity.py
```

**Output:** 5-stage analysis with 2 production sites

### 4️⃣ Run 3-Stage Model

```bash
cd 3Stage
python run_sensitivity.py
```

**Output:** 3-stage analysis (single warehouse configuration)

---

##  Sensitivity Analysis

### Parameter `m`: Period Subdivision

The sensitivity analysis varies parameter **`m`** (period subdivision factor):

- `m = 1`: **5 periods** of 12 days each (base case)
- `m = 2`: **10 periods** of 6 days each
- `m = 3`: **15 periods** of 4 days each
- `m = 4`: **20 periods** of 3 days each

### Demand Distribution Modes

**Pm (Demand at end of sub-periods):**
- Entire period demand occurs at the **last sub-period**

**Pmd (Demand distributed evenly):**
- Period demand is **evenly distributed** across sub-periods

### Results Analysis

The analysis compares:
-  **Total cost** (Pm vs Pmd)
-  **Cost breakdown** (Purchasing, Production, Holding, Transport)
-  **Purchasing strategies** across different `m` values
-  **CPU time** for each scenario

---

##  Mathematical Model

### Decision Variables

| Symbol | Code Variable | Type | Description |
|--------|---------------|------|-------------|
| q<sub>j,t</sub> | `self.q[j,t]` | Continuous | Quantity purchased from supplier j in period t |
| z<sub>j,t</sub> | `self.z[j,t]` | Binary | 1 if ordering from supplier j in period t |
| x<sub>t</sub> | `self.x[t]` | Continuous | Production quantity in period t |
| w<sub>t</sub> | `self.w_prod[t]` | Binary | 1 if producing in period t |
| y<sub>k,t</sub> | `self.y[k,t]` | Continuous | Quantity shipped from stage k in period t |
| i<sub>k,t</sub> | `self.i[k,t]` | Continuous | Inventory level at stage k at end of period t |

### Objective Function

```
Minimize Z = Purchasing Cost + Ordering Cost + Production Cost 
             + Holding Cost + Transportation Cost
```

### Key Constraints

1. **Flow Balance** at each stage
2. **Production Capacity** limits
3. **Transportation Capacity** limits
4. **Supplier Capacity** (cumulative over periods)
5. **Minimum/Maximum Order Quantities**
6. **Price Break Linearization** (piecewise linear costs)
7. **Freight Rate Optimization** (quantity-based discounts)
8. **Inventory Capacity** limits
9. **Lead Times** between stages
10. **Demand Satisfaction**

 **See [`FORMULA_MAPPING.md`](FORMULA_MAPPING.md) for detailed mathematical formulas and code mappings.**

---

##  Key Features

###  Supplier Constraints
- **Time-limited offers**: Certain offers expire after specific periods
- **Minimum order quantities**: 50 units for first order, 20 for subsequent
- **Cumulative capacity**: Supplier capacity accumulates over time
- **Price breaks**: Quantity-based discounts (incremental pricing)

###  Operational Constraints
- **Production capacity**: 270 units/period (base case)
- **Transportation capacity**: 300 units/period
- **Inventory capacity**: 400 units/warehouse
- **Lead times**: Configurable between stages (typically 1×m for Stage 2→3)
- **Ending inventory**: Must maintain safety stock at customer stage

###  Optimization Techniques
- **Price break linearization**: Binary variables + constraints for piecewise costs
- **Freight rate optimization**: Handles complex freight schedules
- **Cumulative capacity modeling**: Tracks supplier availability over horizon
- **Production grouping**: Fixed costs apply per base period, not sub-period
- **Lead time handling**: Proper modeling of in-transit inventory

---

##  Model Variants

### 3-Stage Model
- **Configuration**: Removes 1 regional warehouse
- **Stages**: Suppliers → Warehouse → Customer
- **Use case**: Simpler supply chain network

### 4-Stage Model (Default)
- **Configuration**: Standard 4-stage configuration
- **Stages**: Suppliers → Warehouse 1 → Warehouse 2 → Customer
- **Use case**: Balanced complexity and realism

### 5-Stage Model
- **Configuration**: Adds 2nd production site
- **Stages**: Suppliers → Production Site 1 → Production Site 2 → Warehouse → Customer
- **Use case**: Multi-site production scenarios
- **Special features**: Production capacity split between sites

---

##  Technical Details

- **Language**: Python 3.8+
- **Optimization**: OR-Tools (Google)
- **Solver**: SCIP (default backend)
- **Problem Type**: MILP (Mixed Integer Linear Programming)
- **Variables**: ~200-600 (depending on K and T)
- **Constraints**: ~150-500 (depending on configuration)
- **Visualization**: Matplotlib

---

##  Output Examples

### Console Output
```
==============================================
SENSITIVITY ANALYSIS - TABLE 8 FORMAT (Pm vs Pmd)
==============================================
m   | Len/Per(d) | Periods |     Cost_Pm | CPU_Pm(s) |    Cost_Pmd | CPU_Pmd(s)
------------------------------------------------------------------------------------------------------
1   | 12.00      | 5       |     141,274 |     0.0234 |     141,274 |     0.0198
2   | 6.00       | 10      |     141,829 |     0.0456 |     141,829 |     0.0412
3   | 4.00       | 15      |     142,163 |     0.0678 |     142,163 |     0.0689
4   | 3.00       | 20      |     142,384 |     0.0891 |     142,384 |     0.0923
```

### Generated Plots
- `cost_breakdown_Pm.png` - Cost components breakdown for Pm mode
- `cost_breakdown_Pmd.png` - Cost components breakdown for Pmd mode
- `cost_breakdown_comparison.png` - Side-by-side comparison
- `purchasing_strategy_*.png` - Cumulative order quantities by supplier
- `total_cost_Pm_vs_Pmd.png` - Total cost comparison across m values

---


