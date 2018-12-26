"""
Bitcoin Cash mining simulator
"""
from collections import namedtuple
import numpy as np

np.random.seed(list(b'BCH'))

Block = namedtuple("Block", "id parent height timestamp difficulty chainwork")

initial_difficulty = 600.*5e18
genesis = Block(0, None, 0, 0, initial_difficulty)
next_block_id = 1

class BlockTip:
    """ Pointer to a block with extra info:
    - info needed for difficulty adjustment
    - chainwork
    - other stuff if needed
    """
    def __init__(self, newblock, history):
        self.block = newblock
        history = history[-146:]
        history.append(newblock)
        self.history = history

        # calc next block difficulty
        if len(history) < 147:
            # early blocks just copy difficulty
            self.next_difficulty = newblock.difficulty
        else:
            # BCH DAA since Nov 2017:
            # https://github.com/bitcoincashorg/bitcoincash.org/blob/master/spec/nov-13-hardfork-spec.md#difficulty-adjustment-algorithm-description
            b_last = self.history[-2]  # skip median since timestamps are in order
            b_first = self.history[-146]  # ditto
            ts = b_last.timestamp - b_first.timestamp
            ts = min(288*600, max(72*600, ts))
            w = b_last.chainwork - b_first.chainwork
            pw = w*600./ts
            self.next_difficulty = pw

    @classmethod
    def from_parent_tip(cls, newblock, parent):
        """ fastest constructor - copy history from parent """
        return cls(newblock, parent.history)

    @classmethod
    def from_block(cls, newblock):
        """ slow constructor -- digs through past blocks to build history """
        block = newblock.parent
        diffs = [None]*146
        for i in range(145,-1,-1):
            if block is None:
                break
            diffs[i] = block
            block = block.parent
        return cls(newblock, diffs[i+1:])

genesistip = BlockTip.from_block(genesis)

class BasicMiner:
    blockinfo = [None]*maxNblocks

    def __init__(self, hashrate):
        self.hashrate = hashrate
        self.chaintips = [genesistip]  # known chain tips
        self.besttip = genesistip
        self.blockinfo = self.blockinfo.copy()
    def receiveblock(self, newtip, time):
        pass
    def minedblock(self, newtip, time):
        """ Called when block is successfully mined. """
        # Return False to broadcast the new block; return True to hide block.
        pass
    def getmining(self):
        return (self.hashrate, self.besttip)

class Simulation:
    def __init__(self, miners):
        self.time = 0
        self.miners = list(miners)
        self.stopping = False

    def run(self, maxruntime):
        """run until a given time"""
        self.stopping = False
        while not self.stopping:
            deltaT, winner_tip, winner = self.nextblock()
            newtime = self.time + deltaT
            if newtime > maxruntime:
                # If next block would have been mined after maxruntime, then
                # effectively it did not happen. We stop the simulation at the
                # threshold.
                self.time = maxruntime
                return
            timestamp = int(newtime) # timestamps are integers

            self.time = newtime


    def nextblock(self,):
        """get random next block winner & time according to current mining priorities"""
        M = len(self.miners)
        hashrates    = np.empty((M))
        difficulties = np.empty((M))
        tips = np.empty((45),dtype=object)
        for i,m in enumerate(self.miners):
            hr, tip = m.getmining()
            hashrates[i] = hr
            difficulties[i] = tip.next_difficulty
            tips[i] = tip
        # calculate probability-per-unit time for each miner to find a block.
        rates = hashrates / difficulties

        # pick random winner
        ratesum = np.cumsum(rates)
        totalrate = ratesum[-1]
        # next block could be found by anyone
        expected_blocktime = 1./totalrate
        deltaT = np.random.exponential(expected_blocktime)
        # who won the block?
        # numpy black magic -- argmin (arr <= x) finds first index where value >= x
        winner_idx = np.argmin(ratesum <= np.random.uniform(0, totalrate))

        return deltaT, tips[winner_idx], self.miners[winner_idx]
