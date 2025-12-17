# 📦 Inventory Price Scheme Optimization

Supply Chain Management optimization using Mixed Integer Linear Programming (MILP) to find the optimal purchasing, production, and transportation plan with minimum total cost.

## 🎯 Problem Description

This project solves a **4-stage, 5-period supply chain optimization problem** with:
- **4 Suppliers** (with quantity discounts and time-limited offers)
- **4 Stages**: Manufacturing → Local Warehouse → Regional Warehouse → Customer
- **5 Time Periods** (12 days each)
- **Objective**: Minimize total cost while satisfying customer demand

## 🏗️ System Architecture

```
Suppliers → Stage 1 (Manufacturing) → Stage 2 (Local WH) → Stage 3 (Regional WH) → Stage 4 (Customer)
             [Production]              [Lead Time = 0]      [Lead Time = 1]        [Demand]
```

## 📊 Cost Components

The model minimizes the following costs:

1. **Purchasing Cost**: Raw material cost + ordering fees (with price breaks)
2. **Production Cost**: Fixed setup cost + variable production cost
3. **Holding Cost**: Inventory holding at warehouses + in-transit inventory
4. **Transportation Cost**: Freight rates (with quantity discounts)

## 📁 Project Structure

```
Price_Scheme/
├── FIXED/                 # Latest optimized version
│   ├── data_loader.py     # Input parameters and data
│   └── dynamic_scm_milp.py # MILP model implementation
├── HiGHS/                 # HiGHS solver version
│   ├── data_loader.py
│   ├── dynamic_scm_highs.py
│   └── compare_solvers.py
├── Chat/                  # Development versions
└── README.md
```

## 🚀 Getting Started

### Prerequisites

```bash
pip install ortools
```

### Running the Model

```bash
cd FIXED
python dynamic_scm_milp.py
```

### Expected Output

```
Creating variables...
Adding constraints...
Setting objective function...
Solving...
Objective value = 141,274

COST BREAKDOWN:
  Purchasing:   86,250
  Production:   11,530
  Holding:      13,450
  Transport:    10,374
===================================

PURCHASING PLAN:
Per  Sup1_1   Sup1_2   Sup2   Sup3
1    270      0        0      0
2    180      0        60     0
3    0        0        0      400
4    0        140      0      0
5    0        0        0      0
```

## 🔧 Key Features

### Supplier Constraints
- **Time-limited offers**: Supplier 1 Offer 1 expires after Period 2
- **Minimum order quantities**: 50 units for first order, 20 for subsequent
- **Cumulative capacity**: Supplier capacity accumulates over periods
- **Price breaks**: Discounts for larger order quantities

### Operational Constraints
- **Production capacity**: 270 units/period
- **Transportation capacity**: 300 units/period
- **Inventory capacity**: 200 units/warehouse
- **Lead time**: 1 period between Stage 2 → Stage 3
- **Ending inventory**: Must maintain 100 units at Stage 4

### Optimization Techniques
- **Price break linearization**: Convert nonlinear pricing to linear constraints
- **Freight rate optimization**: Handle quantity-based freight discounts
- **Cumulative capacity modeling**: Track supplier capacity over time

## 📈 Solver Comparison

Multiple solvers tested:
- **SCIP**: Default solver (fast, reliable)
- **HiGHS**: Modern open-source solver (often faster)

Use `compare_solvers.py` to benchmark both solvers.

## 📖 Model Formulation

### Decision Variables
- `q[j,t]`: Quantity purchased from supplier j in period t
- `x[t]`: Quantity produced in period t
- `y[k,t]`: Quantity shipped from stage k in period t
- `i[k,t]`: Inventory level at stage k at end of period t

### Objective Function
```
Minimize: Purchasing + Production + Holding + Transportation
```

### Key Constraints
- Material balance at each stage
- Production and transportation capacity limits
- Supplier capacity and minimum order requirements
- Inventory capacity limits
- Demand satisfaction

## 🛠️ Technical Details

- **Language**: Python 3.x
- **Optimization**: OR-Tools (Google)
- **Solver**: SCIP / HiGHS
- **Problem Type**: MILP (Mixed Integer Linear Programming)
- **Variables**: ~200 decision variables
- **Constraints**: ~150 constraints



