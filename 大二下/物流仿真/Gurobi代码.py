import gurobipy as gp
from gurobipy import GRB
import numpy as np

# 1. 真实的销售数据
sales_pred = np.array([
    [1.09, 1.01, 0.92, 0.83, 0.77],
    [0.96, 0.89, 0.81, 0.73, 0.67],
    [0.96, 0.90, 0.81, 0.73, 0.68],
    [0.99, 0.91, 0.84, 0.75, 0.69],
    [1.00, 0.93, 0.85, 0.76, 0.70],
    [1.07, 0.95, 0.90, 0.81, 0.75],
    [1.03, 0.99, 0.87, 0.78, 0.72]
])
num_days, num_stores = sales_pred.shape

# 2. 车辆参数
num_truck = 4
num_emergency = 1
truck_cap = 2
emergency_cap = 1
truck_cost_day = 300
truck_cost_km = 0.2
emergency_cost_day = 500
emergency_cost_km = 0.5
truck_speed = 40
emergency_speed = 60
decay_cost = 20
time_cost = 0.1

# 3. 距离矩阵，门店0为配送中心
distance = np.array([
    [0, 10, 15, 20, 25, 30],
    [10, 0, 8, 12, 18, 22],
    [15, 8, 0, 10, 16, 20],
    [20, 12, 10, 0, 8, 14],
    [25, 18, 16, 8, 0, 10],
    [30, 22, 20, 14, 10, 0]
])

# 4. 随机生成超额销售，强制第3天第2家门店超额
np.random.seed(42)
over_sales = np.zeros((num_days, num_stores))
for d in range(num_days):
    for s in range(num_stores):
        if np.random.rand() < 0.15 or (d == 2 and s == 1):
            over_sales[d, s] = sales_pred[d, s] * 0.3  # 超额30%

# 5. Gurobi建模
m = gp.Model("delivery_opt")

# 决策变量
gx = m.addVars(num_days, num_stores, num_truck, lb=0, name="x")  # 普通车配送量
gy = m.addVars(num_days, num_stores, num_emergency, lb=0, name="y")  # 应急车配送量
gz = m.addVars(num_days, num_truck, vtype=GRB.BINARY, name="z")  # 普通车是否用
gs = m.addVars(num_days+1, num_stores, lb=0, name="s")  # 库存

# 辅助
visit_truck = m.addVars(num_days, num_stores, num_truck, vtype=GRB.BINARY, name="visit_truck")
visit_emergency = m.addVars(num_days, num_stores, num_emergency, vtype=GRB.BINARY, name="visit_emergency")
emergency_used = m.addVars(num_days, num_emergency, vtype=GRB.BINARY, name="emergency_used")
M = 1000

# 约束1：初始库存为0
for j in range(num_stores):
    m.addConstr(gs[0, j] == 0, name=f"init_stock_{j}")

# 约束2：库存动态平衡
for d in range(num_days):
    for j in range(num_stores):
        m.addConstr(
            gs[d+1, j] == gs[d, j] + gp.quicksum(gx[d, j, k] for k in range(num_truck)) + gp.quicksum(gy[d, j, k] for k in range(num_emergency))
            - sales_pred[d, j] - over_sales[d, j],
            name=f"stock_balance_{d}_{j}"
        )

# 约束3：普通车容量
for d in range(num_days):
    for k in range(num_truck):
        m.addConstr(
            gp.quicksum(gx[d, j, k] for j in range(num_stores)) <= truck_cap * gz[d, k],
            name=f"truck_cap_{d}_{k}"
        )

# 约束4：应急车容量
for d in range(num_days):
    for k in range(num_emergency):
        m.addConstr(
            gp.quicksum(gy[d, j, k] for j in range(num_stores)) <= emergency_cap,
            name=f"emergency_cap_{d}_{k}"
        )

# 约束5：普通车是否用
for d in range(num_days):
    for k in range(num_truck):
        m.addConstr(
            gz[d, k] <= 1,
            name=f"truck_use_{d}_{k}"
        )

# 约束6：普通车优先补货（满足当天预测需求+提前补货，提前补货比例50%）
for d in range(num_days):
    for j in range(num_stores):
        # 普通车配送量要覆盖当天销售+部分提前补货（提前补货量为次日需求的50%，防止无解）
        if d < num_days - 1:
            m.addConstr(
                gp.quicksum(gx[d, j, k] for k in range(num_truck)) >= sales_pred[d, j] + 0.5 * sales_pred[d+1, j] - gs[d, j],
                name=f"truck_priority_advance_{d}_{j}"
            )
        else:
            m.addConstr(
                gp.quicksum(gx[d, j, k] for k in range(num_truck)) >= sales_pred[d, j] - gs[d, j],
                name=f"truck_priority_{d}_{j}"
            )

# 约束7：应急车即时补货（当天超额必须当天补）
for d in range(num_days):
    for j in range(num_stores):
        m.addConstr(
            gp.quicksum(gy[d, j, k] for k in range(num_emergency)) >= over_sales[d, j],
            name=f"emergency_now_{d}_{j}"
        )

# 约束8：库存上限3吨
for d in range(num_days+1):
    for j in range(num_stores):
        m.addConstr(gs[d, j] <= 3, name=f"s_max_{d}_{j}")

# 约束9：配送量非负
for d in range(num_days):
    for j in range(num_stores):
        for k in range(num_truck):
            m.addConstr(gx[d, j, k] >= 0, name=f"x_nonneg_{d}_{j}_{k}")
        for k in range(num_emergency):
            m.addConstr(gy[d, j, k] >= 0, name=f"y_nonneg_{d}_{j}_{k}")

# 约束10：库存非负
for d in range(num_days+1):
    for j in range(num_stores):
        m.addConstr(gs[d, j] >= 0, name=f"s_nonneg_{d}_{j}")

# 约束11：强制应急车调用
m.addConstr(
    gp.quicksum(gy[2, 1, k] for k in range(num_emergency)) >= 0.1,
    name="force_emergency"
)

# 辅助变量与配送量绑定
for d in range(num_days):
    for j in range(num_stores):
        for k in range(num_truck):
            m.addConstr(gx[d, j, k] <= M * visit_truck[d, j, k], name=f"visit_truck1_{d}_{j}_{k}")
            m.addConstr(gx[d, j, k] >= 0.01 * visit_truck[d, j, k], name=f"visit_truck2_{d}_{j}_{k}")
        for k in range(num_emergency):
            m.addConstr(gy[d, j, k] <= M * visit_emergency[d, j, k], name=f"visit_emergency1_{d}_{j}_{k}")
            m.addConstr(gy[d, j, k] >= 0.01 * visit_emergency[d, j, k], name=f"visit_emergency2_{d}_{j}_{k}")

for d in range(num_days):
    for k in range(num_emergency):
        m.addConstr(
            gp.quicksum(gy[d, j, k] for j in range(num_stores)) <= M * emergency_used[d, k],
            name=f"emergency_used1_{d}_{k}"
        )
        m.addConstr(
            gp.quicksum(gy[d, j, k] for j in range(num_stores)) >= 0.01 * emergency_used[d, k],
            name=f"emergency_used2_{d}_{k}"
        )

# 目标函数
total_cost = 0
for d in range(num_days):
    # 普通车成本
    for k in range(num_truck):
        used = gz[d, k]
        km = gp.quicksum(distance[0, j+1] * visit_truck[d, j, k] for j in range(num_stores))
        total_cost += truck_cost_day * used + truck_cost_km * km
    # 应急车成本
    for k in range(num_emergency):
        km = gp.quicksum(distance[0, j+1] * visit_emergency[d, j, k] for j in range(num_stores))
        total_cost += emergency_cost_day * emergency_used[d, k] + emergency_cost_km * km
    # 腐败成本
    for j in range(num_stores):
        total_cost += decay_cost * (gs[d+1, j] * 0.01)
    # 时间成本
    for k in range(num_truck):
        total_cost += time_cost * (gp.quicksum(distance[0, j+1] / truck_speed * 60 * visit_truck[d, j, k] for j in range(num_stores)))
    for k in range(num_emergency):
        total_cost += time_cost * (gp.quicksum(distance[0, j+1] / emergency_speed * 60 * visit_emergency[d, j, k] for j in range(num_stores)))

m.setObjective(total_cost, GRB.MINIMIZE)
m.optimize()

# 输出
if m.status == GRB.OPTIMAL or m.status == GRB.SUBOPTIMAL:
    print("每日配送明细：")
    for d in range(num_days):
        print(f"第{d+1}天：")
        for j in range(num_stores):
            x_sum = sum(gx[d, j, k].X for k in range(num_truck))
            y_sum = sum(gy[d, j, k].X for k in range(num_emergency))
            print(f"  门店{j+1} 普通车配送量: {x_sum:.2f} 吨，应急车配送量: {y_sum:.2f} 吨，销售: {sales_pred[d, j]:.2f} 吨，超额: {over_sales[d, j]:.2f} 吨，库存: {gs[d+1, j].X:.2f} 吨")
    print("\n每日成本分析：")
    print(f"总成本: {m.ObjVal:.2f} 元")
else:
    print("模型未找到可行解，状态码：", m.status)