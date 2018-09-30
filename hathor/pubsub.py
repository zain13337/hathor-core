# encoding: utf-8

from collections import defaultdict
from enum import Enum


class HathorEvents(Enum):
    """
        NETWORK_NEW_ACCEPTED:
            Triggered when a new tx/block is accepted in the network
            Publishes a tx/block object

        WALLET_OUTPUT_RECEIVED:
            Triggered when a wallet receives a new output
            Publishes an UnspentTx object and the new total number of tx in the Wallet (total=int, output=UnspentTx)

        WALLET_INPUT_SPENT:
            Triggered when a wallet spends an output
            Publishes a SpentTx object (output_spent=SpentTx)

        WALLET_BALANCE_UPDATED:
            Triggered when the balance of the wallet changes
            Publishes an int (balance=int)

        WALLET_KEYS_GENERATED:
            Triggered when new keys are generated by the wallet and returns the quantity of keys generated
            Publishes an int (keys_count=int)
    """
    MANAGER_ON_START = 'manager:on_start'
    MANAGER_ON_STOP = 'manager:on_stop'

    NETWORK_NEW_TX_ACCEPTED = 'network:new_tx_accepted'

    WALLET_OUTPUT_RECEIVED = 'wallet:output_received'

    WALLET_INPUT_SPENT = 'wallet:output_spent'

    WALLET_BALANCE_UPDATED = 'wallet:balance_updated'

    WALLET_KEYS_GENERATED = 'wallet:keys_generated'

    WALLET_GAP_LIMIT = 'wallet:gap_limit'


class EventArguments(object):
    """Simple object for storing event arguments.
    """
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __contains__(self, key):
        return key in self.__dict__


class PubSubManager(object):
    """Manages a pub/sub pattern bus.

    It is used to let independent objects respond to events.
    """
    def __init__(self):
        self._subscribers = defaultdict(list)

    def subscribe(self, key, fn):
        """Subscribe to a specific event.

        :param key: Name of the key to which to subscribe.
        :type key: string

        :param fn: A function to be called when an event with `key` is published.
        :type fn: function
        """
        if fn not in self._subscribers[key]:
            self._subscribers[key].append(fn)

    def unsubscribe(self, key, fn):
        """Unsubscribe from a specific event.
        """
        if fn in self._subscribers[key]:
            self._subscribers[key].pop(fn)

    def publish(self, key, **kwargs):
        """Publish a new event.

        :param key: Key of the new event.
        :type key: string

        :param **kwargs: Named arguments to be given to the functions that will be called with this event.
        :type **kwargs: dict
        """
        args = EventArguments(**kwargs)
        for fn in self._subscribers[key]:
            fn(key, args)
