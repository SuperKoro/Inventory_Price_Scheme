import re

# Read the file with UTF-8 encoding
with open('dynamic_scm_milp.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find and replace the Stage 3 section
old_text = """                # Stage 3 - Mfg2 (QUAN TRỌNG: có cả inflow từ WH1 VÀ sản xuất x2)
                lt_23 = self.data.lead_times[(2, 3)]
                in_3 = 0
                if t >= lt_23:
                    in_3 = self.y[2, t - lt_23]
                prev_3 = self.data.initial_inventory[3] if t == 0 else self.i[3, t-1]
                # In + tồn trước + sản xuất tại site2 = ship ra + tồn
                self.solver.Add(in_3 + prev_3 + self.x2[t] == self.y[3, t] + self.i[3, t])
                self.solver.Add(self.y[3, t] <= self.data.trans_capacity[t] * self.w_trans[3, t])"""

new_text = """                # Stage 3 - Mfg2 (Site 2 CHỈ xử lý bán thành phẩm từ Site 1)
                lt_23 = self.data.lead_times[(2, 3)]
                in_3 = 0
                if t >= lt_23:
                    in_3 = self.y[2, t - lt_23]
                prev_3 = self.data.initial_inventory[3] if t == 0 else self.i[3, t-1]
                
                # CONSTRAINT: Site 2 production output = shipment to WH2
                self.solver.Add(self.y[3, t] == self.x2[t])
                
                # FLOW BALANCE: Input (từ WH1) = Production consumed + Inventory
                # Site 2 chỉ có thể sản xuất khi có bán thành phẩm từ Site 1
                self.solver.Add(in_3 + prev_3 == self.x2[t] + self.i[3, t])
                self.solver.Add(self.y[3, t] <= self.data.trans_capacity[t] * self.w_trans[3, t])"""

content = content.replace(old_text, new_text)

# Write back
with open('dynamic_scm_milp.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Fixed Stage 3 flow balance!")
print("Changes:")
print("  - Added: y[3,t] == x2[t] (production output = shipment)")
print("  - Changed: in_3 + prev_3 == x2[t] + i[3,t] (input must equal production + inventory)")
