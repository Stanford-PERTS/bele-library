"""A module implementing a sharded counter for views."""


import random

from google.appengine.api import memcache
from google.appengine.ext import ndb


SHARD_KEY_TEMPLATE = 'shard-view:{}-{:d}'


class ViewCounterShardConfig(ndb.Model):
    """Tracks the number of shards for each named counter."""
    num_shards = ndb.IntegerProperty(default=20)

    @classmethod
    def all_keys(cls, name):
        """Returns all possible keys for the counter name given the config.
        Args:
            name: The name of the counter.
        Returns:
            The full list of ndb.Key values corresponding to all the possible
                counter shards that could exist.
        """
        config = cls.get_or_insert(name)
        shard_key_strings = [SHARD_KEY_TEMPLATE.format(name, index)
                             for index in range(config.num_shards)]
        return [ndb.Key(ViewCounterShard, shard_key_string)
                for shard_key_string in shard_key_strings]


class ViewCounterShard(ndb.Model):
    """Shards for each named counter."""
    count = ndb.IntegerProperty(default=0)


def get_count(name):
    """Retrieve the value for a given sharded counter.
    Args:
        name: The name of the counter.
    Returns:
        Integer; the cumulative count of all sharded counters for the given
            counter name.
    """
    total = memcache.get(name)
    if total is None:
        total = 0
        all_keys = ViewCounterShardConfig.all_keys(name)
        for counter in ndb.get_multi(all_keys):
            if counter is not None:
                total += counter.count
        memcache.add(name, total, 60)
    return total


def increment(name):
    """Increment the value for a given sharded counter.
    Args:
        name: The name of the counter.
    """
    config = ViewCounterShardConfig.get_or_insert(name)
    _increment(name, config.num_shards)


@ndb.transactional
def _increment(name, num_shards):
    """Transactional helper to increment the value for a given sharded counter.
    Also takes a number of shards to determine which shard will be used.
    Args:
        name: The name of the counter.
        num_shards: How many shards to use.
    """
    index = random.randint(0, num_shards - 1)
    shard_key_string = SHARD_KEY_TEMPLATE.format(name, index)
    counter = ViewCounterShard.get_by_id(shard_key_string)
    if counter is None:
        counter = ViewCounterShard(id=shard_key_string)
    counter.count += 1
    counter.put()
    # Memcache increment does nothing if the name is not a key in memcache
    memcache.incr(name)


@ndb.transactional
def increase_shards(name, num_shards):
    """Increase the number of shards for a given sharded counter.
    Will never decrease the number of shards.
    Args:
        name: The name of the counter.
        num_shards: How many shards to use.
    """
    config = ViewCounterShardConfig.get_or_insert(name)
    if config.num_shards < num_shards:
        config.num_shards = num_shards
        config.put()