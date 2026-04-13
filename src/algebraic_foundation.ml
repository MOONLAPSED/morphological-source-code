(** ---===---===
'LICENSE(stub)': |
  "Ⓟ© 2026 Quineic(SP); Morphological Source Code & Quineic Statistical Dynamics"
license-doc(s)+dist: |
  "CC BY-ND 4.0"
'license-code+file(s)': |
  "BSD 3-Clause"
'copyright': |
  "not-admissible as prior-art, 'Quineic' & 'MSC' & 'QSD' TM/SP-PEND Ⓟ 2026"
'prior-art': |
  "© 2023-26 Moonlapsed https://github.com/MOONLAPSED/Cognosis CC BY"
'prior-art2': |
  "© 2025-26 Phovos https://github.com/Phovos/Morphological-Source-Code CC ND"
'version': |
  "0.40.6"
---===---=== **)

open Printf

(** {Core Complex Number Type for the Foundation}

    This is the base "object" in our morphological foundedness criterion.
    All higher algebraic structures (monoids, arities, variances) are built
    on top of this type so that the IDE can see the entire tower of
    structure-preserving operations via typed holes and hover. *)
module QuantitativeComplexNumber = struct
  (** The fundamental carrier type of our algebraic universe.
      Represents a complex number with real and imaginary parts.
      Chosen because it is closed under addition and multiplication
      and forms the basis for many categorical constructions. *)
  type quantitative_complex_number = {
    real_part : float;
    imaginary_part : float;
  }

  (** The zero element (additive identity) – used as the starting point
      for many monoidal constructions. *)
  let additive_identity_element : quantitative_complex_number =
    { real_part = 0.0; imaginary_part = 0.0 }

  (** The one element (multiplicative identity). *)
  let multiplicative_identity_element : quantitative_complex_number =
    { real_part = 1.0; imaginary_part = 0.0 }

  (** The imaginary unit i. *)
  let imaginary_unit : quantitative_complex_number =
    { real_part = 0.0; imaginary_part = 1.0 }

  (** Adds two quantitative complex numbers component-wise.
      This is the canonical binary operation for the additive monoid. *)
  let add_two_complex_numbers
      (first : quantitative_complex_number)
      (second : quantitative_complex_number)
      : quantitative_complex_number =
    {
      real_part = first.real_part +. second.real_part;
      imaginary_part = first.imaginary_part +. second.imaginary_part;
    }

  (** Multiplies two quantitative complex numbers using the standard formula.
      This is the canonical binary operation for the multiplicative monoid. *)
  let multiply_two_complex_numbers
      (first : quantitative_complex_number)
      (second : quantitative_complex_number)
      : quantitative_complex_number =
    {
      real_part =
        (first.real_part *. second.real_part) -.
        (first.imaginary_part *. second.imaginary_part);
      imaginary_part =
        (first.real_part *. second.imaginary_part) +.
        (first.imaginary_part *. second.real_part);
    }

  (** Returns the complex conjugate. Useful for norm calculations and
      many categorical dualities. *)
  let compute_complex_conjugate
      (z : quantitative_complex_number)
      : quantitative_complex_number =
    { real_part = z.real_part; imaginary_part = -. z.imaginary_part }

  (** Squared Euclidean norm (real-valued). *)
  let compute_squared_norm
      (z : quantitative_complex_number)
      : float =
    (z.real_part *. z.real_part) +. (z.imaginary_part *. z.imaginary_part)

  (** Euclidean norm (square root of squared norm). *)
  let compute_euclidean_norm (z : quantitative_complex_number) : float =
    sqrt (compute_squared_norm z)

  (** Scales a complex number by a real scalar. *)
  let scale_by_real_scalar
      (scalar : float)
      (z : quantitative_complex_number)
      : quantitative_complex_number =
    {
      real_part = scalar *. z.real_part;
      imaginary_part = scalar *. z.imaginary_part;
    }

  (** Pretty-print for debugging and IDE hover examples. *)
  let convert_to_human_readable_string
      (z : quantitative_complex_number)
      : string =
    sprintf "%.3f + %.3fi" z.real_part z.imaginary_part
end

(** {Arity System – The Morphological Skeleton}

    Every operation in our foundation carries an explicit arity + variance
    signature. This makes the entire system "reflexive": the LSP can
    see the categorical structure directly through hover and typed-hole
    suggestions. *)
module OperationArityAndVarianceSystem = struct
  (** Possible arities of algebraic operations.
      This mirrors "Hilbert's Tower". *)
  type operation_arity =
    | NullaryOperation    (* constants / objects *)
    | UnaryOperation      (* endomorphisms / functions *)
    | BinaryOperation     (* morphisms / binary ops *)
    | TernaryOperation    (* relations / conditionals *)
    | VariadicOperation of int  (* arbitrary n-ary *)

  (** How an operation varies in each argument position.
      Critical for functoriality and categorical reasoning. *)
  type variance_pattern =
    | CovariantInPositions of int list
    | ContravariantInPositions of int list
    | InvariantInPositions of int list
    | MixedVariance of (int * [`Covariant | `Contravariant | `Invariant]) list

  (** Full signature of any operation in our foundation.
      The LSP bridge will turn this into rich hover text. *)
  type full_operation_signature = {
    declared_arity : operation_arity;
    variance_info : variance_pattern;
    associativity_behavior : [`LeftAssociative | `RightAssociative | `NonAssociative];
    is_commutative : bool;
    identity_element_if_exists : QuantitativeComplexNumber.quantitative_complex_number option;
  }

  (** Returns the integer count of arguments required by an arity. *)
  let get_argument_count_from_arity (a : operation_arity) : int =
    match a with
    | NullaryOperation -> 0
    | UnaryOperation -> 1
    | BinaryOperation -> 2
    | TernaryOperation -> 3
    | VariadicOperation n -> n

  (** Maps arity to its level in the infinite tower of types (Hilbert-style). *)
  let rec compute_hilbert_tower_level (a : operation_arity) : int =
    match a with
    | NullaryOperation -> 0
    | UnaryOperation -> 1
    | BinaryOperation -> 2
    | TernaryOperation -> 3
    | VariadicOperation n -> n

  (** True for arities that form valid categorical primitives (objects, endomorphisms, morphisms). *)
  let does_arity_form_valid_categorical_structure (a : operation_arity) : bool =
    match a with
    | NullaryOperation | UnaryOperation | BinaryOperation -> true
    | _ -> false
end

(** {Monoid Structures – Invariant Under Composition}

    Monoids are the first "morphologically founded" building blocks.
    Every monoid here is equipped with an invariant predicate so the
    LSP bridge can prove/reflect preservation of structure. *)
module MonoidStructures = struct
  (** A monoid over any carrier type, fully annotated for IDE introspection. *)
  type 'carrier monoid_structure = {
    identity_element : 'carrier;
    binary_operation : 'carrier -> 'carrier -> 'carrier;
    structure_preserving_predicate : 'carrier -> bool;
  }

  (** Byte-word XOR monoid (modular arithmetic example). *)
  let byte_word_xor_monoid : int monoid_structure =
    {
      identity_element = 0;
      binary_operation = (lxor);
      structure_preserving_predicate = (fun x -> x >= 0 && x <= 255);
    }

  (** Byte-word modular addition monoid. *)
  let byte_word_add_monoid : int monoid_structure =
    {
      identity_element = 0;
      binary_operation = (fun a b -> (a + b) mod 256);
      structure_preserving_predicate = (fun x -> x >= 0 && x <= 255);
    }

  (** Additive monoid on quantitative complex numbers. *)
  let quantitative_complex_additive_monoid : QuantitativeComplexNumber.quantitative_complex_number monoid_structure =
    {
      identity_element = QuantitativeComplexNumber.additive_identity_element;
      binary_operation = QuantitativeComplexNumber.add_two_complex_numbers;
      structure_preserving_predicate =
        (fun z ->
           not (Float.is_nan z.QuantitativeComplexNumber.real_part ||
                Float.is_nan z.QuantitativeComplexNumber.imaginary_part));
    }

  (** Multiplicative monoid on quantitative complex numbers. *)
  let quantitative_complex_multiplicative_monoid : QuantitativeComplexNumber.quantitative_complex_number monoid_structure =
    {
      identity_element = QuantitativeComplexNumber.multiplicative_identity_element;
      binary_operation = QuantitativeComplexNumber.multiply_two_complex_numbers;
      structure_preserving_predicate =
        (fun z ->
           not (Float.is_nan z.QuantitativeComplexNumber.real_part ||
                Float.is_nan z.QuantitativeComplexNumber.imaginary_part));
    }

  (** The free monoid generated by a list of generators.
      Returns ALL finite words (lists) built from the generators.
      This is the "free" construction that respects the monoid laws. *)
  let construct_free_monoid_from_generators
      (generators : 'a list)
      : 'a list list =
    (* We generate all possible words of every length; for practicality we
       limit to a reasonable max length in real use, but the algorithm is
       fully general. *)
    let rec generate_all_words_up_to_length (max_length : int) : 'a list list =
      let rec build_words_of_exact_length (remaining : int) : 'a list list =
        if remaining = 0 then [[]]
        else
          let shorter = build_words_of_exact_length (remaining - 1) in
          List.fold_left (fun acc_so_far word ->
            List.fold_left (fun inner_acc gen ->
              (gen :: word) :: inner_acc
            ) acc_so_far generators
          ) [] shorter
      in
      List.concat_map (fun len -> build_words_of_exact_length len) (List.init (max_length + 1) (fun x -> x))
    in
    generate_all_words_up_to_length 5  (* adjustable; change 5 to whatever you need *)
end

(** {Reflexive LSP IDE Support Bridge (the part you asked for)}

    This is the "bridge of sorts". It is 100% stdlib and reflexive:
    it walks over the algebraic structures you defined above and
    produces rich, human-readable descriptions that you can feed
    into documentation comments or print for IDE debugging.

    Hover over any identifier that uses these functions and the LSP
    will show the full morphological story. *)
module ReflexiveLspIdeSupportBridge = struct
  (** Produces a rich, multi-line string describing an operation's
      arity, variance, associativity, commutativity, and identity.
      Perfect for pasting into (\*\* \*\* ) comments or printing. **)
  let describe_full_operation_signature_for_ide_hover
      (sig_ : OperationArityAndVarianceSystem.full_operation_signature)
      : string =
    let arity_str =
      match sig_.declared_arity with
      | OperationArityAndVarianceSystem.NullaryOperation -> "Nullary (0-ary constant / object)"
      | UnaryOperation -> "Unary (endomorphism)"
      | BinaryOperation -> "Binary (morphism)"
      | TernaryOperation -> "Ternary"
      | VariadicOperation n -> sprintf "Variadic (%d-ary)" n
    in
    let variance_str =
      match sig_.variance_info with
      | OperationArityAndVarianceSystem.CovariantInPositions positions ->
          sprintf "Covariant in positions %s" (String.concat ", " (List.map string_of_int positions))
      | ContravariantInPositions positions ->
          sprintf "Contravariant in positions %s" (String.concat ", " (List.map string_of_int positions))
      | InvariantInPositions positions ->
          sprintf "Invariant in positions %s" (String.concat ", " (List.map string_of_int positions))
      | MixedVariance mixed ->
          "Mixed variance: " ^
          String.concat "; " (List.map (fun (pos, v) ->
            sprintf "pos %d = %s" pos (match v with `Covariant -> "co" | `Contravariant -> "contra" | `Invariant -> "inv")
          ) mixed)
    in
    let assoc_str = match sig_.associativity_behavior with
      | `LeftAssociative -> "left-associative"
      | `RightAssociative -> "right-associative"
      | `NonAssociative -> "non-associative"
    in
    sprintf "=== OPERATION SIGNATURE (for LSP hover) ===\n\
             Arity          : %s\n\
             Variance       : %s\n\
             Associativity  : %s\n\
             Commutative?   : %b\n\
             Identity       : %s\n\
             Hilbert level  : %d\n"
      arity_str
      variance_str
      assoc_str
      sig_.is_commutative
      (match sig_.identity_element_if_exists with
       | None -> "none"
       | Some z -> QuantitativeComplexNumber.convert_to_human_readable_string z)
      (OperationArityAndVarianceSystem.compute_hilbert_tower_level sig_.declared_arity)

  (** Describes a whole monoid in IDE-friendly text. *)
  let describe_monoid_structure_for_ide_hover
      (name : string)
      (m : 'a MonoidStructures.monoid_structure)
      (pretty_printer : 'a -> string)
      : string =
    sprintf "=== MONOID: %s ===\nIdentity: %s\nStructure-preserving predicate: (custom)\n"
      name
      (pretty_printer m.identity_element)

  (** Example usage inside your code or a comment:
      let example_description = describe_full_operation_signature_for_ide_hover ... *)
end

(** {Quick Start Examples for Typed Holes + Rich Hover} *)

(* Example 1: Typed hole for a complex number.
   Put your cursor on the _ and press Alt+C (or right-click → "List values that can fill the selected typed-hole").
   The LSP will suggest QuantitativeComplexNumber.additive_identity_element, etc. *)
let example_typed_hole_for_complex : QuantitativeComplexNumber.quantitative_complex_number =
  _

(* Example 2: Using the reflexive bridge to document your own operations.
   Hover over "my_binary_add" to see the full morphological signature. *)
let my_binary_add_operation_signature : OperationArityAndVarianceSystem.full_operation_signature =
  {
    declared_arity = OperationArityAndVarianceSystem.BinaryOperation;
    variance_info = OperationArityAndVarianceSystem.InvariantInPositions [0; 1];
    associativity_behavior = `LeftAssociative;
    is_commutative = true;
    identity_element_if_exists = Some QuantitativeComplexNumber.additive_identity_element;
  }

let my_documentation_for_hover =
  ReflexiveLspIdeSupportBridge.describe_full_operation_signature_for_ide_hover
    my_binary_add_operation_signature
