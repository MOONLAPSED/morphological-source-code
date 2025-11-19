#lang racket

;; Define the original model Θ as a sorted list of knowledge elements
(define Θ '("Fact1" "Fact2" "Fact3")) ;; Example initial knowledge

;; Helper function for set union
(define (set-union lst1 lst2)
  (remove-duplicates (append lst1 lst2)))

;; Generalized sorting function
(define (sort-model model comparator)
  (sort model comparator))

;; Sorting Strategies

;; Alphabetical Sorting
(define (alphabetical-comparator a b)
  (string<? a b))

;; Length-Based Sorting
(define (length-comparator a b)
  (< (string-length a) (string-length b)))

;; Reverse Alphabetical Sorting
(define (reverse-alphabetical-comparator a b)
  (string>? a b))

;; Keyword-Priority Sorting
(define (keyword-priority-comparator keyword)
  (λ (a b)
    (cond
      [(and (string-contains? a keyword) (not (string-contains? b keyword))) #t]
      [(and (string-contains? b keyword) (not (string-contains? a keyword))) #f]
      [else (string<? a b)])))

;; Define the knowledge editing function F with customizable sorting
(define (F Θ k operation comparator [save #f])
  (let* ([result
          (case operation
            ;; Knowledge Insertion: Add new knowledge k and sort
            [("Insertion") (sort-model (set-union Θ (list k)) comparator)]
            
            ;; Knowledge Modification: Replace k with kPrime and sort
            [("Modification")
             (sort-model
              (map (λ (fact) (if (equal? fact (car k)) (cdr k) fact)) Θ)
              comparator)]
            
            ;; Knowledge Erasure: Remove knowledge k and sort
            [("Erasure") 
             (sort-model
              (filter (λ (fact) (not (equal? fact k))) Θ)
              comparator)]
            
            ;; Default case if operation is not recognized
            [else Θ])]
         [final-result (sort-model result comparator)]) ;; Ensure final sorting
    ;; Save the result if requested
    (when save
      (with-output-to-file "modelState.txt"
        (λ () (write final-result))
        #:exists 'replace)
      (displayln "Model saved to modelState.txt"))
    final-result))

;; Example Usage

;; Knowledge Insertion with Alphabetical Sorting
(define insertedModel (F Θ "NewFact" "Insertion" alphabetical-comparator #t))

;; Knowledge Modification with Length-Based Sorting
(define modifiedModel (F insertedModel '("Fact2" . "CorrectedFact2") "Modification" length-comparator #t))

;; Knowledge Erasure with Keyword-Priority Sorting (prioritizing "New")
(define erasedModel (F modifiedModel "Fact1" "Erasure" (keyword-priority-comparator "New") #t))

;; Display Results
(displayln "Inserted Model (Alphabetical):")
(displayln insertedModel)

(displayln "Modified Model (Length-Based):")
(displayln modifiedModel)

(displayln "Result After Erasure (Keyword-Priority for 'New'):")
(displayln erasedModel)