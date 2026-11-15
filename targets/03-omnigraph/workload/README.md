# Omnigraph workload

- `schema.pg` declares the section 2.1 types and follows the pinned [schema language](https://github.com/ModernRelay/omnigraph/blob/b2dbaff7584eb849a98fa139876e0ae474e929ea/docs/user/schema/index.md) and [edge-cardinality rules](https://github.com/ModernRelay/omnigraph/blob/b2dbaff7584eb849a98fa139876e0ae474e929ea/docs/user/schema/index.md#edge-cardinality).
- `queries.gq` contains the section 2.2 reads and mutations and follows the pinned [query](https://github.com/ModernRelay/omnigraph/blob/b2dbaff7584eb849a98fa139876e0ae474e929ea/docs/user/queries/index.md), [traversal](https://github.com/ModernRelay/omnigraph/blob/b2dbaff7584eb849a98fa139876e0ae474e929ea/docs/user/queries/traversal.md), [mutation](https://github.com/ModernRelay/omnigraph/blob/b2dbaff7584eb849a98fa139876e0ae474e929ea/docs/user/mutations/index.md) and [conditional-mutation](https://github.com/ModernRelay/omnigraph/blob/b2dbaff7584eb849a98fa139876e0ae474e929ea/docs/user/mutations/conditional.md) pages.
- `parity.cypher` gives O6's `q_eligible` and `q_live` equivalents for the pinned FalkorDB and Neo4j baselines and follows the master blueprint §7 contracts.

The files are documentation-derived and intentionally unexecuted in phase 1.
Omnigraph syntax validation and the noted optional-holder shape are phase-2
work [unmeasured: O2 and O6].
