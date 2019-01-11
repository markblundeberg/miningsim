#!/usr/bin/env python3
"""
Test a mining situation where difficulty is high, then:
* mining suddenly stops for a while, and
* mining returns but at a very low level
"""
from miningsim import *

np.random.seed(list(b'off sim'))

initial_difficulty = 600.*5e18
blocktree = BlockTree(initial_difficulty)

miners = [BasicMiner(blocktree, 5.0e18, name="Strong Miners"),
          BasicMiner(blocktree, 0.1e18, name="Weak Miner"),
          ]

sim = Simulation(blocktree, miners, debug=True)

sim.run(2 * 86400)

print("----remove big miner")
sim.miners.pop(0)
print("----fast forward simulation by 10 days")
sim.time += 10*86400

sim.run(30 * 86400)
