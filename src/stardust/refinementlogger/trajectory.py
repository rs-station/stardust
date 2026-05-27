"""PDB trajectory writer for refinement using mdtraj."""

from __future__ import annotations

import contextlib
from pathlib import Path

import mdtraj as md
import numpy as np
import torch
from loguru import logger
from mdtraj.formats import PDBTrajectoryFile


class TrajectoryWriter:
    """Handles saving PDB trajectories during refinement using mdtraj."""

    def __init__(
        self,
        output_dir: Path,
        pdb_template_path: str | Path,
        save_interval: int = 10,  # noqa: ARG002 - kept for API compatibility
        wandb_logger=None,
    ):
        """Initialize trajectory writer.

        Args:
            output_dir: Output directory; a `trajectory/` subdir is created here.
            pdb_template_path: Path to PDB template defining topology and atom count.
            save_interval: Retained for API compatibility; frames are written on every
                `save_frame` call.
            wandb_logger: Optional WandbLogger for real-time per-frame streaming.
        """
        self.output_dir = Path(output_dir) / "trajectory"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.pdb_template_path = Path(pdb_template_path)
        self.wandb_logger = wandb_logger
        self.traj_writers: dict[str, PDBTrajectoryFile] = {}

        self.mdtraj_template = md.load_pdb(str(self.pdb_template_path))
        self.topology = self.mdtraj_template.topology
        logger.info(
            f"TrajectoryWriter loaded {self.pdb_template_path} "
            f"({self.topology.n_atoms} atoms, {self.topology.n_residues} residues)"
        )

    @staticmethod
    def _to_numpy(x: torch.Tensor | np.ndarray) -> np.ndarray:
        return x.detach().cpu().numpy() if isinstance(x, torch.Tensor) else x

    def _check_atom_count(self, coordinates: np.ndarray, context: str) -> bool:
        n_coords, n_template = coordinates.shape[0], self.topology.n_atoms
        if n_coords != n_template:
            logger.error(
                f"Atom count mismatch in {context}: "
                f"coordinates have {n_coords}, template has {n_template}"
            )
            return False
        return True

    def save_frame(
        self,
        coordinates: torch.Tensor | np.ndarray,
        iteration: int,
        run_id: str,
        b_factors: torch.Tensor | np.ndarray | None = None,  # noqa: ARG002
        loss: float | None = None,  # noqa: ARG002
    ) -> None:
        """Append a frame (in Angstroms) to the trajectory file for ``run_id``."""
        coords = self._to_numpy(coordinates).reshape(-1, 3)
        if not self._check_atom_count(coords, "save_frame"):
            return

        if run_id not in self.traj_writers:
            traj_path = self.output_dir / f"{run_id}_refinement_trajectory.pdb"
            self.traj_writers[run_id] = PDBTrajectoryFile(str(traj_path), mode="w")
            logger.info(f"Opened trajectory file: {traj_path}")

        writer = self.traj_writers[run_id]
        writer.write(coords, self.topology, modelIndex=iteration)

        # PDBTrajectoryFile buffers writes; flush so partial trajectories are tailable.
        if hasattr(writer, "_file") and hasattr(writer._file, "flush"):
            writer._file.flush()

        if self.wandb_logger is not None:
            self._stream_frame_to_wandb(coords, iteration, run_id)

    def _stream_frame_to_wandb(
        self, coords: np.ndarray, iteration: int, run_id: str
    ) -> None:
        """Log a single frame to wandb as a Molecule. Best-effort; never raises."""
        try:
            import wandb  # local import keeps wandb an optional dependency
        except ImportError:
            return

        temp_path = self.output_dir / f"_temp_{run_id}_frame.pdb"
        try:
            coords_nm = coords.reshape(1, -1, 3) / 10.0  # mdtraj uses nm
            md.Trajectory(coords_nm, self.topology).save_pdb(str(temp_path))
            wandb.log({
                f"trajectory_{run_id}_live": wandb.Molecule(str(temp_path)),
                "iteration": iteration,
            })
        except Exception as e:
            logger.debug(f"Could not stream frame to wandb: {e}")
        finally:
            temp_path.unlink(missing_ok=True)

    def save_best(
        self,
        coordinates: np.ndarray | torch.Tensor,
        run_id: str,
        iteration: int,
        b_factors: np.ndarray | torch.Tensor | None = None,
    ) -> None:
        """Save a single best-so-far structure as a standalone PDB."""
        coords = self._to_numpy(coordinates).reshape(-1, 3)
        if not self._check_atom_count(coords, "save_best"):
            return

        best_path = self.output_dir / f"checkpoint_{run_id}_iter{iteration}.pdb"
        coords_nm = coords.reshape(1, -1, 3) / 10.0  # mdtraj uses nm
        traj = md.Trajectory(coords_nm, self.topology)

        if b_factors is not None:
            traj.bfactors = self._to_numpy(b_factors).reshape(-1, 1)

        traj.save_pdb(str(best_path))

    def close(self, run_id: str | None = None) -> None:
        """Close one trajectory writer (by ``run_id``) or all of them."""
        run_ids = [run_id] if run_id is not None else list(self.traj_writers)
        for rid in run_ids:
            writer = self.traj_writers.pop(rid, None)
            if writer is None:
                continue
            try:
                writer.close()
                logger.info(f"Closed trajectory writer for run {rid}")
            except Exception as e:
                logger.warning(f"Error closing trajectory writer for {rid}: {e}")

    def __del__(self):
        """Cleanup: close any open writers."""
        with contextlib.suppress(Exception):
            self.close()
