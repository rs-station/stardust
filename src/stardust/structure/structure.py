"""Interface sketch for the ``Structure`` object.

This is an *interface-only* mock-up. It is meant to
pin down the object's surface and call signatures, not its behavior.

Slicing / indexing accessors
----------------------------
Pandas-style typed indexers, each keyed by the natural key for its axis. A
bare ``sys["A"]`` is ambiguous (chain? altloc?), so the axis is made explicit
by the accessor name. ``sys.atoms[...]`` returns a deep copy; ``sys.view[...]``
returns a tensor-storage view so gradients flow back to the parent's tensors.

    Accessor                             Keyed by                      Example
    -----------------------------------  ----------------------------  ----------------------
    _AtomAccessor (sys.atoms / sys[])    int / slice / mask / indices  sys.atoms[0:100]
    _ResidueAccessor (sys.residues)      (chain, residue_id) tuples    sys.residues["A", 42]
    _ChainAccessor (sys.chains)          chain id(s)                   sys.chains[["A", "C"]]
    _ConformerAccessor (sys.conformers)  altloc / tree node            sys.conformers["A"]
    _ViewAccessor (sys.view)             same keys as atoms (view)     sys.view[mask]
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, NewType, Optional, Sequence, Union

import gemmi
import numpy as np
import pandas as pd
import torch


CoordinateTensor = NewType("CoordinateTensor", torch.Tensor)      # (..., n_atoms, 3) Å
BfactorTensor = NewType("BfactorTensor", torch.Tensor)            # (..., n_atoms,)  Å²  (B_iso)
AnisoTensor = NewType("AnisoTensor", torch.Tensor)                # (..., n_atoms, 6) Å²  (U_ij)
OccupancyTensor = NewType("OccupancyTensor", torch.Tensor)        # (..., n_atoms,)  ∈[0,1]
AtomicNumberTensor = NewType("AtomicNumberTensor", torch.Tensor)  # (n_atoms,) int
NodeIdTensor = NewType("NodeIdTensor", torch.Tensor)              # (n_atoms,) int32

Selection = Union[int, slice, Sequence[int], np.ndarray, torch.Tensor]


class CrystalData:
    cell: gemmi.UnitCell
    spacegroup: gemmi.SpaceGroup


class Topology:
    chain_id: np.ndarray   # (n_atoms,) str
    residue_id: np.ndarray     # (n_atoms,) int   (resseq)
    residue_name: np.ndarray   # (n_atoms,) str
    atom_name: np.ndarray      # (n_atoms,) str


# TODO this requires work -- make a pivotable occupancy tree
class ConformerForest:
    leaves: "list[object]"

    @property
    def dominant(self) -> "Structure": ...

    def where(self, predicate: Callable[[object], bool]) -> "Structure": ...


@dataclass
class GapDescriptor:
    chain_id: str
    after_residue_id: int
    sequence: str
    length: int


@dataclass
class MissingAtomDescriptor:
    chain_id: str
    resseq: int
    resname: str
    missing_atom_names: "list[str]"


@dataclass
class NonstandardResidueDescriptor:
    chain_id: str
    resseq: int
    resname: str
    standard_equivalent: Optional[str]


class _AtomAccessor:
    def __getitem__(self, key: Selection) -> "Structure": ...


class _ViewAccessor:
    def __getitem__(self, key: Selection) -> "Structure": ...


class _ResidueAccessor:
    def __getitem__(self, key) -> "Structure": ...


class _ChainAccessor:
    def __getitem__(self, key) -> "Structure": ...
    @property
    def is_water(self) -> torch.Tensor: ...


class _ConformerAccessor:
    def __getitem__(self, key) -> "Structure": ...
    @property
    def dominant(self) -> "Structure": ...
    @property
    def leaves(self) -> "list[object]": ...
    def where(self, predicate: Callable[[object], bool]) -> "Structure": ...


class Structure:
    xyz: CoordinateTensor          # (..., n_atoms, 3)
    adp: BfactorTensor             # (..., n_atoms,)
    aniso_adp: AnisoTensor         # (..., n_atoms, 6) or (..., n, 3, 3) TODO decide
    occupancy: OccupancyTensor     # (..., n_atoms,)
    aniso_flag: torch.Tensor       # (n_atoms,) bool: True ⇒ use aniso_adp, else adp
    atomic_number: AtomicNumberTensor  # (n_atoms,) int
    node_id: NodeIdTensor          # (n_atoms,) index into conformer tree
    topology: Topology             # chain/res/atom names
    annotations: pd.DataFrame      # rich per-atom metadata
    crystal: CrystalData           # cell + spacegroup  TODO should we have subclass CrystalStructure?
    pdb_header: "list[str]"        # header lines minus CRYST1 TODO probably this is a bad idea...
                                   # ... metadata should be modeled

    def __init__(
        self,
        **kwargs,  # TODO
    ) -> None:
        ...

    def to_gemmi(self, include_header: bool = True) -> gemmi.Structure:
        ...
    @classmethod
    def from_gemmi(cls, structure: gemmi.Structure) -> "Structure":
        ...

    def to_biotite(self):  # biotite AtomArray | AtomArrayStack ??  TODO needed?
        ...
    @classmethod
    def from_biotite(self, *args, **kwargs) -> "Structure":  # TODO
        ...

    def to_torchref(sys: Structure):    # -> torchref.Model (shared storage)
        ...
    def from_torchref(model) -> Structure:
        ...

    def save_pdb(self, path: Path, include_header: bool = True) -> None: ...
    @classmethod
    def read_pdb(cls, path: Path) -> "Structure":
        ...
    
    def save_cif(self, path: Path, include_header: bool = True) -> None: ...
    @classmethod
    def read_cif(cls, path: Path) -> "Structure":
        ...

    @property
    def sequence(self) -> str:
        """One-letter sequence from CA records."""
        ...

    @property
    def xyz_fractional(self) -> CoordinateTensor:  # lazy/cached
        ...

    @property
    def operations(self) -> gemmi.GroupOps:
        ...

    @property
    def R_G_stack(self) -> torch.Tensor:  # (n_ops, 3, 3)
        ...

    @property
    def T_G_stack(self) -> torch.Tensor:  # (n_ops, 3)
        ...

    def exp_sym(
        self,
        frac_pos: Optional[CoordinateTensor] = None,  # (..., n_atoms, 3), batch-aware
    ) -> CoordinateTensor:
        """Apply all symmetry ops to fractional coords -> (..., n_ops, 3)."""
        ...

    def orth2frac(self, orth_pos: CoordinateTensor) -> CoordinateTensor:
        ...

    def frac2orth(self, frac_pos: CoordinateTensor) -> CoordinateTensor:
        ...

    def move2cell(self) -> "Structure":
        """Shift the model into the unit cell."""
        ...

    def set_spacegroup(self, spacegroup: Union[str, gemmi.SpaceGroup]) -> None: ...
    def set_unitcell(self, unitcell: gemmi.UnitCell) -> None: ...
    def set_positions(self, positions: CoordinateTensor) -> None: ...
    def set_biso(self, biso: BfactorTensor) -> None: ...
    def set_baniso(self, baniso: AnisoTensor) -> None: ...
    def set_occ(self, occ: OccupancyTensor) -> None: ...

    @property
    def atoms(self) -> _AtomAccessor: ...
    @property
    def view(self) -> _ViewAccessor: ...
    @property
    def residues(self) -> _ResidueAccessor: ...
    @property
    def chains(self) -> _ChainAccessor: ...

    def selection(self, condition: str, inplace: bool = False) -> "Structure":
        """gemmi selection-syntax string."""
        ...

    def to_device(self, device=None, dtype=None) -> "Structure":
        ...

    def copy(self) -> "Structure":
        ...
