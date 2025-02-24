## Fourier Transform

The Fourier transform maps a function f(x) into its frequency-domain representation F(k). This is expressed as:

    F[f(x)] = F(k) = ∫ from -∞ to ∞ f(x) e^(-2πi k x) dx
    F(k) = ∫₋∞^∞ f(x) e^(-ikx) dx

This integral operates on f(x), meaning the exponential term alone is not the Fourier transform but rather part of the kernel function.

The Fourier transform applies a feedback loop in frequency space, where functions transformed under `e^(-2πi k x)` can exhibit self-similar or dual properties, particularly in the case of Gaussians.

## Square-Integrable functions

A function f(x) is square-integrable over an interval [a,b] if:

    ∫ₐᵇ |f(x)|² dx < ∞

Or, in the case of functions over the entire real line (common in Fourier analysis):

    ∫₋∞^∞ |f(x)|² dx < ∞

This means that f(x) belongs to the space L²(a,b) or L²(ℝ), respectively.  L² represents the set of all such square-integrable functions.

Breaking It Down:

    |f(x)|² ensures we're dealing with the magnitude squared, avoiding issues with negative values.
    The integral ∫ |f(x)|² dx represents the total "energy" of the function.
    If this integral is finite, then f(x) belongs to the space of square-integrable functions, denoted as L²(a,b) or L²(ℝ).

Formal Definition:

A function f(x) belongs to the Hilbert space L²(a,b) if:

    f ∈ L²(a,b) ⟺ ∫ₐᵇ |f(x)|² dx < ∞

## Hilbert Spaces & Inner Products

L² spaces are Hilbert spaces.  A Hilbert space is a complete inner product space.

The space `L²(a,b)` (or more commonly `L²(ℝ)` for the whole real line) is the set of square-integrable functions over an interval `(a,b)`, defined as:

    L²(a,b) = {f : ∫ₐᵇ |f(x)|² dx < ∞}

L² as a Hilbert Space: L² is a complete inner product space with the inner product:

    ⟨f, g⟩ = ∫ₐᵇ f*(x) g(x) dx

    where f*(x) is the complex conjugate of f(x).

This inner product allows us to define orthogonality:

    ⟨f, g⟩ = 0 ⇒ f ⊥ g

    The norm associated with this inner product is:

    ‖f‖ = √⟨f, f⟩ = (∫ₐᵇ |f(x)|² dx)^(1/2)

## Hermitian Operators

In a Hilbert space, an operator Ô is Hermitian if:

    ⟨f | Ôg⟩ = ⟨Ôf | g⟩, for all functions f, g in the space.

The Fourier transform itself isn't Hermitian, but the momentum operator in quantum mechanics is:

    p̂ = -iħ d/dx

which satisfies:

    ⟨f | p̂g⟩ = ⟨p̂f | g⟩

The Fourier transform *is* a unitary operator.  However, it does not diagonalize the momentum operator directly.  Instead, when the momentum operator is transformed to the frequency domain using the Fourier transform, it becomes a multiplicative operator:

    p̂f(x) = -iħ d/dx f(x)  ⟶  pF(k) = ħkF(k)

    meaning in Fourier space; momentum simply acts as multiplication by k.

The Fourier transform is unitary, meaning it preserves inner products (up to a normalization constant, depending on the specific definition of the Fourier transform used):

    ⟨F^f, F^g⟩ = ⟨f, g⟩

where F^ is the Fourier transform operator. This ensures that Fourier transforms preserve energy (norms) in L².  The specific form of the normalization depends on the convention used for the Fourier transform.

    ⟨F, G⟩ = ⟨f, g⟩

which ensures that Fourier transforms preserve energy (norms) in L².

---

| Concept | Definition |
|---------|------------|
| **Fourier Transform** | Maps functions between time/spatial and frequency domains.  The specific form of the transform (including normalization constants) depends on the convention used. |
| **Square-Integrable Function (L²)** | A function whose squared magnitude integrates to a finite value. |
| **Hilbert Space** | A complete inner product space. L² spaces are Hilbert spaces. |
| **Inner Product** | ⟨f, g⟩ = ∫ f*(x) g(x) dx |
| **Hermitian Operator** | Ô satisfies ⟨f | Ôg⟩ = ⟨Ôf | g⟩. |
| **Momentum Operator (p̂)** | p̂ = -i ħ d/dx (in the spatial domain).  In the frequency domain, it becomes multiplication by ħk. |
| **Unitary Transformation** | A transformation that preserves inner products (up to a normalization factor). The Fourier transform is unitary. |

---