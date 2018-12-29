#!/usr/bin/env python3
"""
Test a mining situation where difficulty is high, then:
* mining suddenly stops for a while, and
* mining returns but at a very low level
"""
from miningsim import *

initial_difficulty = 600.*5e18
genesis = Block(0, None, 0, 0, initial_difficulty, 0)
genesistip = BlockTip.from_block(genesis)

miners = [BasicMiner(5e18, genesistip, name="Strong Miners"),
          BasicMiner(0.1e18, genesistip, name="Weak Miner"),
          ]

sim = Simulation(miners)

sim.run(2 * 86400)

sim.miners.pop(0) # remove the big miner
sim.time += 10*86400 # add a bunch of days

sim.run(30 * 86400)
