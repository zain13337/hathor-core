# Copyright 2024 Hathor Labs
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

from __future__ import annotations

from collections import defaultdict
from typing import Iterator

from structlog import get_logger
from typing_extensions import Self

from hathor.conf.settings import HathorSettings
from hathor.daa import DifficultyAdjustmentAlgorithm
from hathor.dag_builder.artifacts import DAGArtifacts
from hathor.dag_builder.tokenizer import Token, TokenType
from hathor.dag_builder.types import (
    AttributeType,
    DAGInput,
    DAGNode,
    DAGNodeType,
    DAGOutput,
    VertexResolverType,
    WalletFactoryType,
)
from hathor.wallet import BaseWallet

logger = get_logger()


class DAGBuilder:
    def __init__(
        self,
        settings: HathorSettings,
        daa: DifficultyAdjustmentAlgorithm,
        genesis_wallet: BaseWallet,
        wallet_factory: WalletFactoryType,
        vertex_resolver: VertexResolverType,
    ) -> None:
        from hathor.dag_builder.default_filler import DefaultFiller
        from hathor.dag_builder.tokenizer import tokenize
        from hathor.dag_builder.vertex_exporter import VertexExporter

        self.log = logger.new()

        self._nodes: dict[str, DAGNode] = {}
        self._tokenize = tokenize
        self._filler = DefaultFiller(self, settings, daa)
        self._exporter = VertexExporter(
            builder=self,
            settings=settings,
            daa=daa,
            genesis_wallet=genesis_wallet,
            wallet_factory=wallet_factory,
            vertex_resolver=vertex_resolver,
        )

    def parse_tokens(self, tokens: Iterator[Token]) -> None:
        """Parse tokens and update the DAG accordingly."""
        for parts in tokens:
            match parts:
                case (TokenType.PARENT, (_from, _to)):
                    self.add_parent_edge(_from, _to)

                case (TokenType.SPEND, (_from, _to, _txout_index)):
                    self.add_spending_edge(_from, _to, _txout_index)

                case (TokenType.ATTRIBUTE, (name, key, value)):
                    self.add_attribute(name, key, value)

                case (TokenType.ORDER_BEFORE, (_from, _to)):
                    self.add_deps(_from, _to)

                case (TokenType.OUTPUT, (name, index, amount, token, attrs)):
                    self.set_output(name, index, amount, token, attrs)

                case (TokenType.BLOCKCHAIN, (name, first_parent, begin_index, end_index)):
                    self.add_blockchain(name, first_parent, begin_index, end_index)

                case _:
                    raise NotImplementedError(parts)

    def _get_node(self, name: str) -> DAGNode:
        """Return a node."""
        return self._nodes[name]

    def _get_or_create_node(self, name: str, *, default_type: DAGNodeType = DAGNodeType.Unknown) -> DAGNode:
        """Return a node, creating one if needed."""
        if name not in self._nodes:
            node = DAGNode(name=name, type=default_type)
            self._nodes[name] = node
        else:
            node = self._nodes[name]
            if node.type is DAGNodeType.Unknown:
                node.type = default_type
            else:
                if default_type != DAGNodeType.Unknown:
                    assert node.type is default_type, f'{node.type} != {default_type}'
        return node

    def add_deps(self, _from: str, _to: str) -> Self:
        """Add a dependency between two nodes. For clarity, `_to` has to be created before `_from`."""
        from_node = self._get_or_create_node(_from)
        self._get_or_create_node(_to)
        from_node.deps.add(_to)
        return self

    def add_blockchain(self, prefix: str, first_parent: str | None, first_index: int, last_index: int) -> Self:
        """Add a sequence of nodes representing a chain of blocks."""
        prev = first_parent
        for i in range(first_index, last_index + 1):
            name = f'{prefix}{i}'
            self._get_or_create_node(name, default_type=DAGNodeType.Block)
            if prev is not None:
                self.add_parent_edge(name, prev)
            prev = name
        return self

    def add_parent_edge(self, _from: str, _to: str) -> Self:
        """Add a parent edge between two nodes. For clarity, `_to` has to be created befre `_from`."""
        self._get_or_create_node(_to)
        from_node = self._get_or_create_node(_from)
        from_node.parents.add(_to)
        return self

    def add_spending_edge(self, _from: str, _to: str, _txout_index: int) -> Self:
        """Add a spending edge between two nodes. For clarity, `_to` has to be created before `_from`."""
        to_node = self._get_or_create_node(_to)
        if len(to_node.outputs) <= _txout_index:
            to_node.outputs.extend([None] * (_txout_index - len(to_node.outputs) + 1))
            to_node.outputs[_txout_index] = DAGOutput(0, '', {})
        from_node = self._get_or_create_node(_from)
        from_node.inputs.add(DAGInput(_to, _txout_index))
        return self

    def set_output(self, name: str, index: int, amount: int, token: str, attrs: AttributeType) -> Self:
        """Set information about an output."""
        node = self._get_or_create_node(name)
        if len(node.outputs) <= index:
            node.outputs.extend([None] * (index - len(node.outputs) + 1))
        node.outputs[index] = DAGOutput(amount, token, attrs)
        if token != 'HTR':
            self._get_or_create_node(token, default_type=DAGNodeType.Token)
            node.deps.add(token)
        return self

    def add_attribute(self, name: str, key: str, value: str) -> Self:
        """Add an attribute to a node."""
        node = self._get_or_create_node(name)
        if key == 'type':
            node.type = DAGNodeType(value)
        else:
            node.attrs[key] = value
        return self

    def topological_sorting(self) -> Iterator[DAGNode]:
        """Run a topological sort on the DAG, yielding nodes in an order that respects all dependency constraints."""
        direct_deps: dict[str, set[str]] = {}
        rev_deps: dict[str, set[str]] = defaultdict(set)
        seen: set[str] = set()
        candidates: list[str] = []
        for name, node in self._nodes.items():
            assert name == node.name
            deps = set(node.get_all_dependencies())
            assert name not in direct_deps
            direct_deps[name] = deps
            for x in deps:
                rev_deps[x].add(name)
            if len(deps) == 0:
                candidates.append(name)

        for _ in range(len(self._nodes)):
            if len(candidates) == 0:
                self.log('fail because there is at least one cycle in the dependencies',
                         direct_deps=direct_deps,
                         rev_deps=rev_deps,
                         seen=seen,
                         not_seen=set(self._nodes.keys()) - seen,
                         nodes=self._nodes)
                raise RuntimeError('there is at least one cycle')
            name = candidates.pop()
            assert name not in seen
            seen.add(name)
            for d in rev_deps[name]:
                direct_deps[d].remove(name)
                if len(direct_deps[d]) == 0:
                    candidates.append(d)
                    del direct_deps[d]
            node = self._get_node(name)
            yield node

    def build(self) -> DAGArtifacts:
        """Build all the transactions based on the DAG."""
        self._filler.run()
        return DAGArtifacts(self._exporter.export())

    def build_from_str(self, content: str) -> DAGArtifacts:
        """Run build() after creating an initial DAG from a string."""
        self.parse_tokens(self._tokenize(content))
        return self.build()
