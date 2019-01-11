"""
Bitcoin Cash mining simulator
"""
from collections import namedtuple
import numpy as np

###
# Blockchain / blocktree
###

Block = namedtuple("Block", "id parent height timestamp difficulty chainwork")

class BlockPoint:
    """ Marker for special blocks on the blocktree:
    - fork blocks
    - tips
    """
    __slots__ = ["block", "parentpoint", "forks"]
    def __init__(self, block, parentpoint):
        self.block = block
        self.parentpoint = parentpoint # single upstream point
        self.forks = () # multiple downstream points

class BlockTree:
    """
    Holds a tree of Blocks (initialized with a genesis block) and manages
    the overall tree structure with BlockPoints.
    """
    def __init__(self, initial_difficulty):
        self.genesis = Block(0, None, 0, 0, initial_difficulty, 0)
        self.next_id = 1
        genpoint = BlockPoint(self.genesis, None)
        self.nextpoint = {0: genpoint}
        self.bestblock = self.genesis

    def addblock(self, block):
        """
        Include a given block
        """
        assert block.id not in self.nextpoint
        pb = block.parent
        pp = self.nextpoint[pb.id]
        if pp.block is pb:
            # block appended to an existing point
            if pp.forks:
                # the point was a fork -- add a new branch.
                point = BlockPoint(block, pp)
                pp.forks = pp.forks + (point,)
                self.nextpoint[block.id] = point
            else:
                # the point was a tip -- just move forward
                pp.block = block
                self.nextpoint[block.id] = pp
        else:
            # block appended to non-point -- need to add two points:
            # a fork and a new tip.
            fp = BlockPoint(block, pp.parent)
            fp.forks = (pp,)
            pp.parent = fp
            point = BlockPoint(block, fp)
            self.nextpoint[block.id] = point
            # traverse history and update pointers to the new point
            b = pb
            while self.nextpoint[block.id] is pp:
                self.nextpoint[block.id] = fp
                b = b.parent

        if self.bestblock.chainwork < block.chainwork:
            self.bestblock = block

    def newblock(self, parent, timestamp, difficulty):
        """ Create and add a new block """
        newblock = Block(self.next_id, parent, parent.height+1, timestamp,
                         difficulty, parent.chainwork + difficulty)
        self.next_id += 1
        self.addblock(newblock)
        return newblock

###
# Mining
###

class MiningTip:
    """ Pointer to a block with extra info:
    - info needed for difficulty adjustment
    - other stuff if needed

    (this exists since difficulty adjustment algo has a long memory and
    traversing the block linked list every time is slow.)
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
    """ The most basic miner -- mines longest chain at constant hashrate. """
    def __init__(self, blocktree, hashrate, name=None):
        if name is None:
            name = "Miner %x"%(id(self),)
        self.blocktree = blocktree
        self.name = name
        self.hashrate = hashrate
        starttip = MiningTip.from_block(blocktree.bestblock)
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
    """ Like BasicMiner but only mines if difficulty is less than diff_threshold.

    This emulates the profit-seeking behaviour of miners like BTC.TOP who
    mine BTC or BCH depending on which is currently more profitable.
    """
    def __init__(self, blocktree, hashrate, diff_threshold, name=None):
        BasicMiner.__init__(self, blocktree, hashrate, name)
        self.diff_threshold = diff_threshold
    def getmining(self):
        if self.besttip.next_difficulty < self.diff_threshold:
            return (self.hashrate, self.besttip)
        else:
            return (0., self.besttip)

class Simulation:
    """
    Time simulation of mining
    """
    def __init__(self, blocktree, miners, starttime=0, debug=False):
        self.blocktree = blocktree
        self.miners = list(miners)
        self.time = starttime
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
            parent = winner_tip.block
            difficulty = winner_tip.next_difficulty
            newblock = self.blocktree.newblock(parent, timestamp, difficulty)
            newtip = MiningTip.from_parent_tip(newblock, winner_tip)

            if not winner.minedblock(newtip, self.time):
                for m in self.miners:
                    m.receiveblock(newtip, self.time)
            if self.debug:
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
