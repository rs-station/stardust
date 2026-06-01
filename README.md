# Stardust: structural representations for refinement and beyond

Stardust is a library that defines `Structure` object that is fully featured for structural biology applications.

NOTE: This repo is a WIP, and should be considered hot lava code at the moment. Don't build on it. We are still working to get the concepts right!

## Structure and Vision

Stardust implements two primary abstractions:

1. A **structure** module that helps manage topology, coordinate, B-factor, and occupancy information. It defines a powerful `Structure` object, as well as code that is crucial for converting and interoperating with different coordinate representations in use.

2. **losslab.** This specifies an interface for loss/likelihood functions that facilitates interoperability between different refinement projects. Because these loss functions depend on attributes of a `Structure` (for example, the Cartesian coordinate positions or B-factors), designing these interfaces for compatability with `Structure` enables maximum interoperability. Further, in addition to a `Structure` interface, valid `loss`es will have an overloaded pure-array interface, which maximizes compatability.


## Out of scope

Stardust does not generate or sample structures/coordinates.

Stardust assumes your are working with a discrete list of cartesian coordinates that represent atomic positions. Models that use densities, continous distributions, _etc._ are out of scope.
