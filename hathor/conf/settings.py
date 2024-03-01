# Copyright 2021 Hathor Labs
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
from math import log
from pathlib import Path
from typing import NamedTuple, Optional, Union

import pydantic

from hathor.checkpoint import Checkpoint
from hathor.feature_activation.settings import Settings as FeatureActivationSettings
from hathor.utils import yaml
from hathor.utils.named_tuple import validated_named_tuple_from_dict

DECIMAL_PLACES = 2

GENESIS_TOKEN_UNITS = 1 * (10**9)  # 1B
GENESIS_TOKENS = GENESIS_TOKEN_UNITS * (10**DECIMAL_PLACES)  # 100B


class HathorSettings(NamedTuple):
    # Version byte of the address in P2PKH
    P2PKH_VERSION_BYTE: bytes

    # Version byte of the address in MultiSig
    MULTISIG_VERSION_BYTE: bytes

    # Name of the network: "mainnet", "testnet-alpha", "testnet-bravo", ...
    NETWORK_NAME: str

    # Initial bootstrap servers
    BOOTSTRAP_DNS: list[str] = []

    # enable peer whitelist
    ENABLE_PEER_WHITELIST: bool = False

    # weather to use the whitelist with sync-v2 peers, does not affect whether the whitelist is enabled or not, it will
    # always be enabled for sync-v1 if it is enabled
    USE_PEER_WHITELIST_ON_SYNC_V2: bool = True

    DECIMAL_PLACES: int = DECIMAL_PLACES

    # Genesis pre-mined tokens
    GENESIS_TOKEN_UNITS: int = GENESIS_TOKEN_UNITS

    GENESIS_TOKENS: int = GENESIS_TOKENS

    # To disable reward halving, just set this to `None` and make sure that INITIAL_TOKEN_UNITS_PER_BLOCK is equal to
    # MINIMUM_TOKEN_UNITS_PER_BLOCK.
    BLOCKS_PER_HALVING: Optional[int] = 2 * 60 * 24 * 365  # 1051200, every 365 days

    INITIAL_TOKEN_UNITS_PER_BLOCK: int = 64
    MINIMUM_TOKEN_UNITS_PER_BLOCK: int = 8

    @property
    def INITIAL_TOKENS_PER_BLOCK(self) -> int:
        return self.INITIAL_TOKEN_UNITS_PER_BLOCK * (10**DECIMAL_PLACES)

    @property
    def MINIMUM_TOKENS_PER_BLOCK(self) -> int:
        return self.MINIMUM_TOKEN_UNITS_PER_BLOCK * (10**DECIMAL_PLACES)

    # Assume that: amount < minimum
    # But, amount = initial / (2**n), where n = number_of_halvings. Thus:
    #   initial / (2**n) < minimum
    #   initial / minimum < 2**n
    #   2**n > initial / minimum
    # Applying log to both sides:
    #   n > log2(initial / minimum)
    #   n > log2(initial) - log2(minimum)
    @property
    def MAXIMUM_NUMBER_OF_HALVINGS(self) -> int:
        return int(log(self.INITIAL_TOKEN_UNITS_PER_BLOCK, 2) - log(self.MINIMUM_TOKEN_UNITS_PER_BLOCK, 2))

    # Average time between blocks.
    AVG_TIME_BETWEEN_BLOCKS: int = 30  # in seconds

    # Genesis pre-mined outputs
    # P2PKH HMcJymyctyhnWsWTXqhP9txDwgNZaMWf42
    #
    # To generate a new P2PKH script, run:
    # >>> from hathor.transaction.scripts import P2PKH
    # >>> import base58
    # >>> address = base58.b58decode('HMcJymyctyhnWsWTXqhP9txDwgNZaMWf42')
    # >>> P2PKH.create_output_script(address=address).hex()
    GENESIS_OUTPUT_SCRIPT: bytes = bytes.fromhex('76a914a584cf48b161e4a49223ed220df30037ab740e0088ac')

    # Genesis timestamps, nonces and hashes

    # Timestamp used for the genesis block
    GENESIS_BLOCK_TIMESTAMP: int = 1572636343

    @property
    def GENESIS_TX1_TIMESTAMP(self) -> int:
        """Timestamp used for the first genesis transaction."""
        return self.GENESIS_BLOCK_TIMESTAMP + 1

    @property
    def GENESIS_TX2_TIMESTAMP(self) -> int:
        """Timestamp used for the second genesis transaction."""
        return self.GENESIS_BLOCK_TIMESTAMP + 2

    GENESIS_BLOCK_NONCE: int = 3526202
    GENESIS_BLOCK_HASH: bytes = bytes.fromhex('000007eb968a6cdf0499e2d033faf1e163e0dc9cf41876acad4d421836972038')
    GENESIS_TX1_NONCE: int = 12595
    GENESIS_TX1_HASH: bytes = bytes.fromhex('00025d75e44804a6a6a099f4320471c864b38d37b79b496ee26080a2a1fd5b7b')
    GENESIS_TX2_NONCE: int = 21301
    GENESIS_TX2_HASH: bytes = bytes.fromhex('0002c187ab30d4f61c11a5dc43240bdf92dba4d19f40f1e883b0a5fdac54ef53')

    # Weight of genesis and minimum weight of a tx/block
    MIN_BLOCK_WEIGHT: int = 21
    MIN_TX_WEIGHT: int = 14
    MIN_SHARE_WEIGHT: int = 21

    HATHOR_TOKEN_UID: bytes = b'\x00'

    # Maximum distance between two consecutive blocks (in seconds), except for genesis.
    # This prevent some DoS attacks exploiting the calculation of the score of a side chain.
    #     P(t > T) = exp(-MAX_DISTANCE_BETWEEN_BLOCKS / AVG_TIME_BETWEEN_BLOCKS)
    #     P(t > T) = exp(-35) = 6.3051e-16
    MAX_DISTANCE_BETWEEN_BLOCKS: int = 150 * AVG_TIME_BETWEEN_BLOCKS

    # Enable/disable weight decay.
    WEIGHT_DECAY_ENABLED: bool = True

    # Minimum distance between two consecutive blocks that enables weight decay.
    # Assuming that the hashrate is constant, the probability of activating is:
    #     P(t > T) = exp(-WEIGHT_DECAY_ACTIVATE_DISTANCE / AVG_TIME_BETWEEN_BLOCKS)
    #     P(t > T) = exp(-120) = 7.66e-53
    # But, if the hashrate drops 40 times, the expected time to find the next block
    # becomes 40 * AVG_TIME_BETWEEN_BLOCKS = 20 minutes and the probability of
    # activating the decay is exp(-3) = 0.05 = 5%.
    WEIGHT_DECAY_ACTIVATE_DISTANCE: int = 120 * AVG_TIME_BETWEEN_BLOCKS

    # Window size of steps in which the weight is reduced when decaying is activated.
    # The maximum number of steps is:
    #     max_steps = floor((MAX_DISTANCE_BETWEEN_BLOCKS - WEIGHT_DECAY_ACTIVATE_DISTANCE) / WEIGHT_DECAY_WINDOW_SIZE)
    # Using these parameters, `max_steps = 15`.
    WEIGHT_DECAY_WINDOW_SIZE: int = 60

    # Amount to reduce the weight when decaying is activated.
    #     adj_weight = weight - decay
    #     difficulty = 2**adj_weight
    #     difficulty = 2**(weight - decay)
    #     difficulty = 2**weight / 2**decay
    # As 2**(-2.73) = 0.15072, it reduces the mining difficulty for 15% of the original weight.
    # Finally, the maximum decay is `max_steps * WEIGHT_DECAY_AMOUNT`.
    # As `max_steps = 15`, then `max_decay = 2**(-15 * 2.73) = 4.71e-13`.
    WEIGHT_DECAY_AMOUNT: float = 2.73

    # Number of blocks to be found with the same hash algorithm as `block`.
    # The bigger it is, the smaller the variance of the hash rate estimator is.
    BLOCK_DIFFICULTY_N_BLOCKS: int = 134

    # Size limit in bytes for Block data field
    BLOCK_DATA_MAX_SIZE: int = 100

    # Number of subfolders in the storage folder (used in JSONStorage and CompactStorage)
    STORAGE_SUBFOLDERS: int = 256

    # Maximum level of the neighborhood graph generated by graphviz
    MAX_GRAPH_LEVEL: int = 3

    # Maximum difference between our latest timestamp and a peer's synced timestamp to consider
    # that the peer is synced (in seconds).
    P2P_SYNC_THRESHOLD: int = 60

    # This multiplier will be used to decide whether the fullnode has had recent activity in the p2p sync.
    # This info will be used in the readiness endpoint as one of the checks.
    #
    # We will multiply it by the AVG_TIME_BETWEEN_BLOCKS, and compare the result with the gap between the
    # current time and the latest timestamp in the database.
    #
    # If the gap is bigger than the calculated threshold, than we will say the fullnode is not ready (unhealthy).
    #
    # Using (P2P_RECENT_ACTIVITY_THRESHOLD_MULTIPLIER * AVG_TIME_BETWEEN_BLOCKS) as threshold will have false
    # positives.
    # The probability of a false positive is exp(-N), assuming the hash rate is constant during the period.
    # In other words, a false positive is likely to occur every exp(N) blocks. If the hash rate decreases
    # quickly, this probability gets bigger.
    #
    # For instance, P2P_RECENT_ACTIVITY_THRESHOLD_MULTIPLIER=5 would get a false positive every 90 minutes.
    # For P2P_RECENT_ACTIVITY_THRESHOLD_MULTIPLIER=10, we would have a false positive every 8 days.
    # For P2P_RECENT_ACTIVITY_THRESHOLD_MULTIPLIER=15, we would have a false positive every 3 years.
    #
    # On the other side, using higher numbers will lead to a higher delay for the fullnode to start reporting
    # as not ready.
    #
    # So for use cases that may need more reponsiveness on this readiness check, at the cost of some eventual false
    # positive, it could be a good idea to decrease the value in this setting.
    P2P_RECENT_ACTIVITY_THRESHOLD_MULTIPLIER: int = 15

    # Whether to warn the other peer of the reason for closing the connection
    WHITELIST_WARN_BLOCKED_PEERS: bool = False

    # Maximum number of opened threads that are solving POW for send tokens
    MAX_POW_THREADS: int = 5

    # The error tolerance, to allow small rounding errors in Python, when comparing weights,
    # accumulated weights, and scores
    # How to use:
    # if abs(w1 - w2) < WEIGHT_TOL:
    #     print('w1 and w2 are equal')

    # if w1 < w2 - WEIGHT_TOL:
    #     print('w1 is smaller than w2')

    # if w1 <= w2 + WEIGHT_TOL:
    #     print('w1 is smaller than or equal to w2')

    # if w1 > w2 + WEIGHT_TOL:
    #     print('w1 is greater than w2')

    # if w1 >= w2 - WEIGHT_TOL:
    #     print('w1 is greater than or equal to w2')
    WEIGHT_TOL: float = 1e-10

    # Maximum difference between the weight and the min_weight.
    MAX_TX_WEIGHT_DIFF: float = 4.0
    MAX_TX_WEIGHT_DIFF_ACTIVATION: float = 32.0

    # Maximum number of txs or blocks (each, not combined) to show on the dashboard
    MAX_DASHBOARD_COUNT: int = 15

    # Maximum number of txs or blocks returned by the '/transaction' endpoint
    MAX_TX_COUNT: int = 15

    # URL prefix where API is served, for instance: /v1a/status
    API_VERSION_PREFIX: str = 'v1a'

    # If should use stratum to resolve pow of transactions in send tokens resource
    SEND_TOKENS_STRATUM: bool = True

    # Maximum size of the tx output's script allowed by the /push-tx API.
    PUSHTX_MAX_OUTPUT_SCRIPT_SIZE: int = 256

    # Maximum number of subscribed addresses per websocket connection
    WS_MAX_SUBS_ADDRS_CONN: Optional[int] = None

    # Maximum number of subscribed addresses that do not have any outputs (also per websocket connection)
    WS_MAX_SUBS_ADDRS_EMPTY: Optional[int] = None

    # Whether miners are assumed to mine txs by default
    STRATUM_MINE_TXS_DEFAULT: bool = True

    # Percentage used to calculate the number of HTR that must be deposited when minting new tokens
    # The same percentage is used to calculate the number of HTR that must be withdraw when melting tokens
    # See for further information, see [rfc 0011-token-deposit].
    TOKEN_DEPOSIT_PERCENTAGE: float = 0.01

    # Array with the settings parameters that are used when calculating the settings hash
    P2P_SETTINGS_HASH_FIELDS: list[str] = [
        'P2PKH_VERSION_BYTE',
        'MULTISIG_VERSION_BYTE',
        'MIN_BLOCK_WEIGHT',
        'MIN_TX_WEIGHT',
        'BLOCK_DATA_MAX_SIZE'
    ]

    # Maximum difference allowed between current time and a received tx timestamp (in seconds). Also used
    # during peer connection. Peers shouldn't have their clocks more than MAX_FUTURE_TIMESTAMP_ALLOWED/2 apart
    MAX_FUTURE_TIMESTAMP_ALLOWED: int = 5 * 60

    # Multiplier for the value to increase the timestamp for the next retry moment to connect to the peer
    PEER_CONNECTION_RETRY_INTERVAL_MULTIPLIER: int = 5

    # Maximum retry interval for retrying to connect to the peer
    PEER_CONNECTION_RETRY_MAX_RETRY_INTERVAL: int = 300

    # Number max of connections in the p2p network
    PEER_MAX_CONNECTIONS: int = 125

    # Maximum period without receiving any messages from ther peer (in seconds).
    PEER_IDLE_TIMEOUT: int = 60

    # Filepath of ca certificate file to generate connection certificates
    CA_FILEPATH: str = os.path.join(os.path.dirname(__file__), '../p2p/ca.crt')

    # Filepath of ca key file to sign connection certificates
    CA_KEY_FILEPATH: str = os.path.join(os.path.dirname(__file__), '../p2p/ca.key')

    # Timeout (in seconds) for the downloading deferred (in the downloader) when syncing two peers
    GET_DATA_TIMEOUT: int = 90

    # Number of retries for downloading a tx from a peer (in the downloader)
    GET_DATA_RETRIES: int = 5

    # Maximum number of characters in a token name
    MAX_LENGTH_TOKEN_NAME: int = 30

    # Maximum number of characters in a token symbol
    MAX_LENGTH_TOKEN_SYMBOL: int = 5

    # Name of the Hathor token
    HATHOR_TOKEN_NAME: str = 'Hathor'

    # Symbol of the Hathor token
    HATHOR_TOKEN_SYMBOL: str = 'HTR'

    # After how many blocks can a reward be spent
    REWARD_SPEND_MIN_BLOCKS: int = 300

    # Mamimum number of inputs accepted
    MAX_NUM_INPUTS: int = 255

    # Mamimum number of outputs accepted
    MAX_NUM_OUTPUTS: int = 255

    # Maximum size of each txout's script (in bytes)
    MAX_OUTPUT_SCRIPT_SIZE: int = 1024

    # Maximum size of each txin's data (in bytes)
    MAX_INPUT_DATA_SIZE: int = 1024

    # Maximum number of pubkeys per OP_CHECKMULTISIG
    MAX_MULTISIG_PUBKEYS: int = 20

    # Maximum number of signatures per OP_CHECKMULTISIG
    MAX_MULTISIG_SIGNATURES: int = 15

    # Maximum number of sig operations of all inputs on a given tx
    # including the redeemScript in case of MultiSig
    MAX_TX_SIGOPS_INPUT: int = 255*5

    # Maximum number of sig operations of all outputs on a given tx
    MAX_TX_SIGOPS_OUTPUT: int = 255*5

    # Maximum number of transactions returned on addresses history API
    MAX_TX_ADDRESSES_HISTORY: int = 150

    # Maximum number of elements (inputs and outputs) to be returned on address history API
    # As a normal tx has ~2-4 inputs and 2 outputs, I would say the maximum should be 150*6 = 900 elements
    MAX_INPUTS_OUTPUTS_ADDRESS_HISTORY: int = 6*MAX_TX_ADDRESSES_HISTORY

    # Maximum number of TXs that will be sent by the Mempool API.
    MEMPOOL_API_TX_LIMIT: int = 100

    # Multiplier coefficient to adjust the minimum weight of a normal tx to 18
    MIN_TX_WEIGHT_COEFFICIENT: float = 1.6

    # Amount in which tx min weight reaches the middle point between the minimum and maximum weight
    MIN_TX_WEIGHT_K: int = 100

    # When the node is being initialized (with a full verification) we don't verify
    # the difficulty of all blocks, we execute the validation every N blocks only
    VERIFY_WEIGHT_EVERY_N_BLOCKS: int = 1000

    # Capabilities
    CAPABILITY_WHITELIST: str = 'whitelist'
    CAPABILITY_SYNC_VERSION: str = 'sync-version'
    CAPABILITY_GET_BEST_BLOCKCHAIN: str = 'get-best-blockchain'

    # Where to download whitelist from
    WHITELIST_URL: Optional[str] = None

    # Interval (in seconds) to broadcast dashboard metrics to websocket connections
    WS_SEND_METRICS_INTERVAL: int = 1

    # Interval (in seconds) to write data to prometheus
    PROMETHEUS_WRITE_INTERVAL: int = 5

    # Interval (in seconds) to collect metrics data
    METRICS_COLLECT_DATA_INTERVAL: int = 5

    # Interval (in seconds) to collect metrics data from rocksdb
    METRICS_COLLECT_ROCKSDB_DATA_INTERVAL: int = 86400  # 1 day

    # Block checkpoints
    CHECKPOINTS: list[Checkpoint] = []

    # Used on testing to enable slow asserts that help catch bugs but we don't want to run in production
    SLOW_ASSERTS: bool = False

    # List of soft voided transaction.
    SOFT_VOIDED_TX_IDS: list[bytes] = []

    # Identifier used in metadata's voided_by to mark a tx as soft-voided.
    SOFT_VOIDED_ID: bytes = b'tx-non-grata'

    # Identifier used in metadata's voided_by when an unexpected exception occurs at consensus.
    CONSENSUS_FAIL_ID: bytes = b'consensus-fail'

    # Identifier used in metadata's voided_by to mark a tx as partially validated.
    PARTIALLY_VALIDATED_ID: bytes = b'pending-validation'

    # Maximum number of sync running simultaneously.
    MAX_ENABLED_SYNC: int = 16

    # Time to update the peers that are running sync.
    SYNC_UPDATE_INTERVAL: int = 10 * 60  # seconds

    # Interval to re-run peer discovery.
    PEER_DISCOVERY_INTERVAL: int = 5 * 60  # seconds

    # All settings related to Feature Activation
    FEATURE_ACTIVATION: FeatureActivationSettings = FeatureActivationSettings()

    # Maximum number of GET_TIPS delayed calls per connection while running sync.
    MAX_GET_TIPS_DELAYED_CALLS: int = 5

    # Maximum number of blocks in the best blockchain list.
    MAX_BEST_BLOCKCHAIN_BLOCKS: int = 20

    # Default number of blocks in the best blockchain list.
    DEFAULT_BEST_BLOCKCHAIN_BLOCKS: int = 10

    # Time in seconds to request the best blockchain from peers.
    BEST_BLOCKCHAIN_INTERVAL: int = 5  # seconds

    # Merged mining settings. The old value is going to be replaced by the new value through Feature Activation.
    OLD_MAX_MERKLE_PATH_LENGTH: int = 12
    NEW_MAX_MERKLE_PATH_LENGTH: int = 20

    # Used to enable nano contracts.
    #
    # This should NEVER be enabled for mainnet and testnet, since both networks will
    # activate Nano Contracts through the Feature Activation.
    ENABLE_NANO_CONTRACTS: bool = False

    # List of enabled blueprints.
    BLUEPRINTS: dict[bytes, 'str'] = {}

    @classmethod
    def from_yaml(cls, *, filepath: str) -> 'HathorSettings':
        """Takes a filepath to a yaml file and returns a validated HathorSettings instance."""
        settings_dict = yaml.dict_from_extended_yaml(filepath=filepath, custom_root=Path(__file__).parent)

        return validated_named_tuple_from_dict(
            HathorSettings,
            settings_dict,
            validators=_VALIDATORS
        )


def _parse_checkpoints(checkpoints: Union[dict[int, str], list[Checkpoint]]) -> list[Checkpoint]:
    """Parse a dictionary of raw checkpoint data into a list of checkpoints."""
    if isinstance(checkpoints, dict):
        return [
            Checkpoint(height, bytes.fromhex(_hash))
            for height, _hash in checkpoints.items()
        ]

    if not isinstance(checkpoints, list):
        raise TypeError(f'expected \'dict[int, str]\' or \'list[Checkpoint]\', got {checkpoints}')

    return checkpoints


def _parse_blueprints(blueprints_raw: dict[str, str]) -> dict[bytes, str]:
    """Parse dict[str, str] into dict[bytes, str]."""
    blueprints: dict[bytes, str] = {}
    for _id_str, _name in blueprints_raw.items():
        _id = bytes.fromhex(_id_str)
        if _id in blueprints:
            raise TypeError(f'Duplicate blueprint id: {_id_str}')
        blueprints[_id] = _name
    return blueprints


def _parse_hex_str(hex_str: Union[str, bytes]) -> bytes:
    """Parse a raw hex string into bytes."""
    if isinstance(hex_str, str):
        return bytes.fromhex(hex_str.lstrip('x'))

    if not isinstance(hex_str, bytes):
        raise TypeError(f'expected \'str\' or \'bytes\', got {hex_str}')

    return hex_str


_VALIDATORS = dict(
    _parse_hex_str=pydantic.validator(
        'P2PKH_VERSION_BYTE',
        'MULTISIG_VERSION_BYTE',
        'GENESIS_OUTPUT_SCRIPT',
        'GENESIS_BLOCK_HASH',
        'GENESIS_TX1_HASH',
        'GENESIS_TX2_HASH',
        pre=True,
        allow_reuse=True
    )(_parse_hex_str),
    _parse_soft_voided_tx_id=pydantic.validator(
        'SOFT_VOIDED_TX_IDS',
        pre=True,
        allow_reuse=True,
        each_item=True
    )(_parse_hex_str),
    _parse_checkpoints=pydantic.validator(
        'CHECKPOINTS',
        pre=True
    )(_parse_checkpoints),
    _parse_blueprints=pydantic.validator(
        'BLUEPRINTS',
        pre=True
    )(_parse_blueprints)
)
