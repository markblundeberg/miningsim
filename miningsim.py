"""
Bitcoin Cash mining simulator
"""
from collections import namedtuple
import numpy as np

np.random.seed(list(b'BCH'))

Block = namedtuple("Block", "id parent height timestamp difficulty chainwork")

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

class BasicMiner:
    def __init__(self, hashrate, starttip, name=None):
        if name is None:
            name = "Miner %x"%(id(self),)
        self.name = name
        self.hashrate = hashrate
        self.chaintips = [starttip]  # known chain tips
        self.besttip = starttip
    def receiveblock(self, newtip, time):
        # Called when block is broadcasted.
        if newtip.block.chainwork > self.besttip.block.chainwork:
            self.besttip = newtip
    def minedblock(self, newtip, time):
        # Called when block is successfully mined.
        # Return False to broadcast the new block; return True to hide block.
        return
    def getmining(self):
        return (self.hashrate, self.besttip)

class SwitchMiner(BasicMiner):
    """ Like BasicMiner but only mines if difficulty is less than diff_threshold."""
    def __init__(self, hashrate, starttip, diff_threshold, name=None):
        BasicMiner.__init__(self, hashrate, starttip, name)
        self.diff_threshold = diff_threshold
    def getmining(self):
        if self.besttip.next_difficulty < self.diff_threshold:
            return (self.hashrate, self.besttip)
        else:
            return (0., self.besttip)


class Simulation:
    def __init__(self, miners):
        self.miners = list(miners)
        self.next_id = 1
        self.time = 0
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
            self.time = newtime
            timestamp = int(newtime) # timestamps are integers
            block = winner_tip.block
            difficulty = winner_tip.next_difficulty
            newblock = Block(self.next_id, block, block.height+1, timestamp,
                             difficulty, block.chainwork + difficulty)
            newtip = BlockTip.from_parent_tip(newblock, winner_tip)

            if not winner.minedblock(newtip, self.time):
                for m in self.miners:
                    m.receiveblock(newtip, self.time)
            print("%15.3f: Block found by %s, h%d, %.2fZH"%(self.time, winner.name, newblock.height, difficulty/1e21))


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
