with open('dynamic_scm_milp_backup.py', 'r') as f:
    lines = f.readlines()

# Find and replace lines 53-59 (0-indexed: 52-58)
new_section = [
    "        # 4. Freight Rates (CONDITIONAL based on number of stages)\n",
    "        transport_intervals = self.data.freight_actual \n",
    "        for t in range(T):\n",
    "            # Determine which stages need freight variables\n",
    "            if self.data.K == 4:\n",
    "                freight_stages = [3]  # leg 3 -> 4\n",
    "            elif self.data.K == 3:\n",
    "                freight_stages = [2]  # leg 2 -> 3\n",
    "            else:\n",
    "                freight_stages = []\n",
    "            \n",
    "            for k in freight_stages:\n",
    "                for e, _ in enumerate(transport_intervals):\n",
    "                    self.f_freight[k, t, e] = self.solver.BoolVar(f'f_{k}_{t}_{e}')\n",
    "                    self.y_freight[k, t, e] = self.solver.NumVar(0, self.infinity, f'y_fr_{k}_{t}_{e}')\n",
    "\n"
]

# Replace lines 52-58 (7 lines) with new section
new_lines = lines[:52] + new_section + lines[59:]

with open('dynamic_scm_milp.py', 'w') as f:
    f.writelines(new_lines)

print('Fixed!')
