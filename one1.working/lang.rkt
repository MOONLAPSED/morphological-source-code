#lang racket
(require racket/string
         racket/port)

;; A simple parser for .env files: each line in the form KEY=VALUE
(define (parse-env-file filepath)
  (define env-hash (make-hash))
  (with-input-from-file filepath
    (lambda ()
      (for ([line (in-lines)])
        (when (and (not (string-blank? line))
                   (not (regexp-match? #rx"^\s*#" line))) ; skip blank lines and comments
          (define parts (string-split line "="))
          (when (= (length parts) 2)
            (hash-set! env-hash 
                       (string-trim (first parts))
                       (string-trim (second parts))))))))
  env-hash)

;; Load the top-level .env file (user-defined values)
(define top-env (parse-env-file ".env"))

;; Function to load a lifecycle-specific env file and merge with top-env
(define (get-lifecycle-env lifecycle)
  (define lifecycle-file (string-append "config/" lifecycle ".env"))
  (define lifecycle-env (parse-env-file lifecycle-file))
  ;; Merge: values from top-env override (or augment) the lifecycle file.
  (hash-union lifecycle-env top-env))

;; Example: Get the environment for the dev lifecycle
(define dev-env (get-lifecycle-env "dev"))
(displayln "Dev Environment:")
(for-each (lambda (key)
            (printf "~a = ~a\n" key (hash-ref dev-env key)))
          (hash-keys dev-env))

;; You could similarly load staging and production environments:
(define staging-env (get-lifecycle-env "staging"))
(define production-env (get-lifecycle-env "production"))

;; And now use these env-hashes to orchestrate your application behavior
;; For example, you might choose a branch from your repository hash:
(define repository
  (list (hash 'id 1 'branch "production" 'permissions '(x))
        (hash 'id 2 'branch "staging" 'permissions '(r x))
        (hash 'id 3 'branch "dev" 'permissions '(r w x))))

;; A function to pick the env based on branch name
(define (env-for-branch branch)
  (cond
    [(string=? branch "production") production-env]
    [(string=? branch "staging") staging-env]
    [(string=? branch "dev") dev-env]
    [else (error "Unknown branch" branch)]))

;; Example: Merge all branch envs (if needed)
(define merged-env
  (for/fold ([acc (make-hash)])
            ([branch repository])
    (hash-union acc (env-for-branch (hash-ref branch 'branch)))))
  
(displayln "\nMerged Environment for all branches:")
(for-each (lambda (key)
            (printf "~a = ~a\n" key (hash-ref merged-env key)))
          (hash-keys merged-env))
