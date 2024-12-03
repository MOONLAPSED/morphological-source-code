#lang racket
;; Create a dictionary generator
(define (make-dictionary)
  (let ((dict (make-hash))) ; Initialize an empty hash table
    (lambda (action . args)
      (match (cons action args)
        [(list 'set key value)
         (hash-set! dict key value)]
        [(list 'get key)
         (hash-ref dict key #f)]
        [(list 'delete key)
         (hash-remove! dict key)]
        [(list 'keys)
         (hash-keys dict)]
        [(list 'values)
         (hash-values dict)]
        [_ 
         (error "Invalid action or incorrect number of arguments")]))))

;; Create the dictionary instance
(define my-dict (make-dictionary))
;; Define a value to use with the dictionary
(define my-value "Byte Dict Tree")
;; Set some key-value pairs
(my-dict 'set 'branch "b1101")
(my-dict 'set 'leaf "0110b")
(my-dict 'set 'key my-value)
;; Retrieve values
(display (my-dict 'get 'branch))
(newline)
(display (my-dict 'get 'leaf))
(newline)
;; Get all keys
(display (my-dict 'keys))
(newline)
;; Delete a key
(my-dict 'delete 'leaf)
;; Retrieve value of deleted key
(display (my-dict 'get 'leaf)) ; Should output: #f
(newline)
