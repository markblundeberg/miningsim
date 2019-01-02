#!/usr/bin/env python3
"""
Test of switch mining -- starts high then drops to optimal 3 EH/s difficulty
"""

from miningsim import *

np.random.seed(list(b'switch sim'))

initial_difficulty = 600.*2e18
blocktree = BlockTree(initial_difficulty)

miners = [BasicMiner (blocktree, 0.1e18, name="Miner A"),
          BasicMiner (blocktree, 0.5e18, name="Miner B"),
          SwitchMiner(blocktree, 5.0e18, 600*1.8e18, name="Miner C"),
          ]

sim = Simulation(blocktree, miners)

sim.run(10 * 86400)
