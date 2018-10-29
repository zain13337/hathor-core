from hathor.exception import HathorError


class TxValidationError(HathorError):
    """Base class for tx validation errors"""


class ParentDoesNotExist(TxValidationError):
    """A parent does not exist"""


class IncorrectParents(TxValidationError):
    """Wrong number of parents or confirming incorrect types of transactions:
    - block: 3 parents: 1 block, 2 transactions
    - tx: 2 parents, both transactions
    """


class TimestampError(TxValidationError):
    """Transaction timestamp is smaller or equal to one parent's timestamp"""


class DoubleSpend(TxValidationError):
    """Some input has already been spent"""


class InputOutputMismatch(TxValidationError):
    """Input and output amounts are not equal"""


class InvalidInputData(TxValidationError):
    """Input data does not solve output script correctly"""


class TooManyInputs(TxValidationError):
    """More than 256 inputs"""


class InexistentInput(TxValidationError):
    """Input tx does not exist or index spent does not exist"""


class ConflictingInputs(TxValidationError):
    """Inputs in the tx are spending the same output"""


class TooManyOutputs(TxValidationError):
    """More than 256 outputs"""


class PowError(TxValidationError):
    """Proof-of-work is not correct"""


class WeightError(TxValidationError):
    """Transaction not using correct weight"""


class DuplicatedParents(TxValidationError):
    """Transaction has duplicated parents"""


class BlockError(TxValidationError):
    """Base class for Block-specific errors"""


class BlockHeightError(BlockError):
    """Block not using correct height"""


class BlockWithInputs(BlockError):
    """Block has inputs"""
