# Stardust: Modular Coordinate Refinement Library

Stardust is a modular library supporting coordinate refinement against experimental data: cryo-EM maps, crystallographic structure factors, and beyond.

Stardust is based on pytorch.


## Structure and Vision

Stardust implements two primary abstractions:

1. **losslab.** These are likelihood functions that compute the probability of some structure given a set of experimental data: `p(x|D)`. A common interface to these losses is enforced by an abstract base class, `BaseLoss`.

2. The **refinementlogger**, a gradient decent manager and logger. Many of the outputs of refinement are common to all refinement strategies: structures as a function of iteration, compute metrics, etc. The `RefinementEngine` class implements these common features and provides a foundation which specific refinement implementations can extend.

3. A **structure** module that helps manage topology, coordinate, B-factor, and occupancy information. It contains a powerful `Structure` object in its own right, as well as code that is crucial for converting and interoperating with different coordinate representations in use.


## Out of scope

Stardust does not generate or sample structures/coordinates. Stardust simply provides a likelihood (and, via torch, likelihood gradients) and a generic system for tracking progress as one seeks to optimize that likelihood.

Stardust assumes your are working with a discrete list of cartesian coordinates that represent atomic positions. Models that use densities, continous distributions, _etc._ are out of scope.
