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

sim = Simulation(blocktree, miners)

sim.run(2 * 86400)

sim.miners.pop(0) # remove the big miner
sim.time += 10*86400 # add a bunch of days

sim.run(30 * 86400)
