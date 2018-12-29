#!/usr/bin/env python3
"""
Test of switch mining -- starts high then drops to optimal 3 EH/s difficulty
"""

from miningsim import *

initial_difficulty = 600.*5e18
genesis = Block(0, None, 0, 0, initial_difficulty, 0)
genesistip = BlockTip.from_block(genesis)

miners = [BasicMiner(0.1e18, genesistip, name="Miner A"),
          BasicMiner(0.5e18, genesistip, name="Miner B"),
          SwitchMiner(5e18, genesistip, 600*3e18, name="Miner C"),
          ]

sim = Simulation(miners)

sim.run(10 * 86400)
