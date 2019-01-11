#!/usr/bin/env python3
"""
Test of switch mining.
- 0.6 EH/s is dedicated
- 1.8 EH/s is break-even
- 10 EH/s switches on and off depending if profitable.
"""

from miningsim import *

np.random.seed(list(b'switch sim'))

initial_difficulty = 600.*1e18
blocktree = BlockTree(initial_difficulty)

miners = [BasicMiner (blocktree,  0.1e18, name="Miner A"),
          BasicMiner (blocktree,  0.5e18, name="Miner B"),
          SwitchMiner(blocktree, 10.0e18, 600*1.8e18, name="Miner C"),
          ]

sim = Simulation(blocktree, miners, debug=True)

sim.run(10 * 86400)
