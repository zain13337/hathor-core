import os
import json
from hathor.wallet.keypair import KeyPair
from hathor.wallet.exceptions import OutOfUnusedAddresses
from hathor.wallet import BaseWallet
from hathor.pubsub import HathorEvents


class Wallet(BaseWallet):
    def __init__(self, keys=None, directory='./', filename='keys.json', history_file='history.json', pubsub=None):
        """ A wallet will hold key pair objects and the unspent and
        spent transactions associated with the keys.

        All files will be stored in the same directory, and it should
        only contain wallet associated files.

        :param keys: keys to initialize this wallet
        :type keys: Dict[string(base58), :py:class:`hathor.wallet.keypair.KeyPair`]

        :param directory: where to store wallet associated files
        :type directory: string

        :param filename: name of keys file
        :type filename: string

        :param history_file: name of history file
        :type history_file: string

        :param pubsub: If not given, a new one is created.
        :type pubsub: :py:class:`hathor.pubsub.PubSubManager`
        """
        super().__init__(
            directory=directory,
            history_file=history_file,
            pubsub=pubsub,
        )

        self.filepath = os.path.join(directory, filename)
        self.keys = keys or {}  # Dict[string(b58_address), KeyPair]

        # Set[string(base58)]
        self.unused_keys = set(key.address for key in self.keys.values() if not key.used)

        self.password = None

        # Used in admin frontend to know which wallet is being used
        self.type = self.WalletType.KEY_PAIR

    def _manually_initialize(self):
        if os.path.isfile(self.filepath):
            print('Loading keys...')
            self.read_keys_from_file()

    def read_keys_from_file(self):
        """Reads the keys from file and updates the keys dictionary

        Uses the directory and filename specified in __init__

        :rtype: None
        """
        new_keys = {}
        with open(self.filepath, 'r') as json_file:
            json_data = json.loads(json_file.read())
            for data in json_data:
                keypair = KeyPair.from_json(data)
                new_keys[keypair.address] = keypair
                if not keypair.used:
                    self.unused_keys.add(keypair.address)

        self.keys.update(new_keys)

    def _write_keys_to_file(self):
        data = [keypair.to_json() for keypair in self.keys.values()]
        with open(self.filepath, 'w') as json_file:
            json_file.write(json.dumps(data, indent=4))

    def unlock(self, password):
        """ Validates if the password is valid
            Then saves the password as bytes.

            :type password: bytes

            :raises IncorrectPassword: when the password is incorrect

            :raises ValueError: when the password parameter is not bytes
        """
        # Get one keypair
        # XXX What if we don't have any keypair in the wallet?
        if isinstance(password, bytes):
            keypair_values = list(self.keys.values())
            if keypair_values:
                keypair = keypair_values[0]

                # Test if the password is correct
                # If not correct IncorrectPassword exception is raised
                keypair.get_private_key(password)

            self.password = password
        else:
            raise ValueError('Password must be in bytes')

    def lock(self):
        self.password = None

    def get_unused_address(self, mark_as_used=True):
        """
        :raises OutOfUnusedAddresses: When there is no unused address left
            to be returned and wallet is locked
        """
        updated = False
        if len(self.unused_keys) == 0:
            if not self.password:
                raise OutOfUnusedAddresses
            else:
                self.generate_keys()
                updated = True

        address = next(iter(self.unused_keys))
        if mark_as_used:
            self.unused_keys.discard(address)
            keypair = self.keys[address]
            keypair.used = True
            updated = True

        if updated:
            self._write_keys_to_file()

        return address

    def generate_keys(self, count=20):
        for _ in range(count):
            key = KeyPair.create(self.password)
            self.keys[key.address] = key
            self.unused_keys.add(key.address)

        # Publish to pubsub that new keys were generated
        self.publish_update(HathorEvents.WALLET_KEYS_GENERATED, keys_count=count)

    def get_private_key(self, address58):
        """ Get private key from the address58

            :param address58: address in base58
            :type address58: string

            :return: Private key object.
            :rtype: :py:class:`cryptography.hazmat.primitives.asymmetric.ec.EllipticCurvePrivateKey`
        """
        return self.keys[address58].get_private_key(self.password)

    def tokens_received(self, address58):
        """ Method called when the wallet receive new tokens

            We set the address as used and remove it from the unused_keys

            :param address58: address that received the token in base58
            :type address58: string
        """
        self.keys[address58].used = True
        self.unused_keys.discard(address58)

    def is_locked(self):
        return self.password is None
