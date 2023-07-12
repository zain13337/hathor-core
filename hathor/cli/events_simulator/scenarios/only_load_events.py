#  Copyright 2023 Hathor Labs
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

from hathor.event.model.base_event import BaseEvent, EventType
from hathor.event.model.event_data import EmptyData, TxData, TxMetadata, TxOutput

ONLY_LOAD_EVENTS = [
    BaseEvent(peer_id='97c14daade28cfe68d5854361bf6d5754b2a1f81e38fb44fe51367f1eb254d11', id=0, timestamp=1572653259.0, type=EventType.LOAD_STARTED, data=EmptyData(), group_id=None),  # noqa E501
    BaseEvent(peer_id='97c14daade28cfe68d5854361bf6d5754b2a1f81e38fb44fe51367f1eb254d11', id=1, timestamp=1572653259.0, type=EventType.NEW_VERTEX_ACCEPTED, data=TxData(hash='339f47da87435842b0b1b528ecd9eac2495ce983b3e9c923a37e1befbe12c792', nonce=0, timestamp=1572636343, version=0, weight=2.0, inputs=[], outputs=[TxOutput(value=100000000000, script='dqkU/QUFm2AGJJVDuC82h2oXxz/SJnuIrA==', token_data=0)], parents=[], tokens=[], token_name=None, token_symbol=None, metadata=TxMetadata(hash='339f47da87435842b0b1b528ecd9eac2495ce983b3e9c923a37e1befbe12c792', spent_outputs=[], conflict_with=[], voided_by=[], received_by=[], children=[], twins=[], accumulated_weight=2.0, score=2.0, first_block=None, height=0, validation='full')), group_id=None),  # noqa E501
    BaseEvent(peer_id='97c14daade28cfe68d5854361bf6d5754b2a1f81e38fb44fe51367f1eb254d11', id=2, timestamp=1572653259.0, type=EventType.NEW_VERTEX_ACCEPTED, data=TxData(hash='16ba3dbe424c443e571b00840ca54b9ff4cff467e10b6a15536e718e2008f952', nonce=6, timestamp=1572636344, version=1, weight=2.0, inputs=[], outputs=[], parents=[], tokens=[], token_name=None, token_symbol=None, metadata=TxMetadata(hash='16ba3dbe424c443e571b00840ca54b9ff4cff467e10b6a15536e718e2008f952', spent_outputs=[], conflict_with=[], voided_by=[], received_by=[], children=[], twins=[], accumulated_weight=2.0, score=2.0, first_block=None, height=0, validation='full')), group_id=None),  # noqa E501
    BaseEvent(peer_id='97c14daade28cfe68d5854361bf6d5754b2a1f81e38fb44fe51367f1eb254d11', id=3, timestamp=1572653259.0, type=EventType.NEW_VERTEX_ACCEPTED, data=TxData(hash='33e14cb555a96967841dcbe0f95e9eab5810481d01de8f4f73afb8cce365e869', nonce=2, timestamp=1572636345, version=1, weight=2.0, inputs=[], outputs=[], parents=[], tokens=[], token_name=None, token_symbol=None, metadata=TxMetadata(hash='33e14cb555a96967841dcbe0f95e9eab5810481d01de8f4f73afb8cce365e869', spent_outputs=[], conflict_with=[], voided_by=[], received_by=[], children=[], twins=[], accumulated_weight=2.0, score=2.0, first_block=None, height=0, validation='full')), group_id=None),  # noqa E501
    BaseEvent(peer_id='97c14daade28cfe68d5854361bf6d5754b2a1f81e38fb44fe51367f1eb254d11', id=4, timestamp=1572653259.0, type=EventType.LOAD_FINISHED, data=EmptyData(), group_id=None)  # noqa E501
]
