#lang racket/gui
(require racket/gui)
(require racket/path)

(define obsidian-vault-path "C:\\Users\\DEV\\Music")

;; Basic frame setup
(define frame 
  (new frame% 
       [label "ObsidianExplorer"]
       [width 800]
       [height 1200]))

;; Create the vertical panel with the frame as parent
(define sizer (new vertical-panel% [parent frame]))

;; Text area component for editing
(define editor 
  (new editor-canvas% 
       [parent sizer]))

;; Debugger component
(define debugger 
  (new editor-canvas% 
       [parent sizer]))

;; REPL component
(define repl 
  (new editor-canvas% 
       [parent sizer]))

;; Status message display using a text area
(define status-message 
  (new text-field% 
       [parent sizer]
       [label "Status"]
       [min-height 50]))

;; Button to execute commands
(define execute-button
  (new button%
       [parent sizer]
       [label "Execute Command"]
       [callback (λ (button event)
                   (let ([input (send editor get-value)])
                     (send editor set-value "")
                     (hash-ref commands input (λ () (send status-message set-value "Unknown command.")))))]))

;; Function to save content to Obsidian vault
(define (save-to-obsidian filename content)
  (with-output-to-file 
    (build-path obsidian-vault-path filename)
    #:exists 'replace
    (λ () (display content))))

;; Function to load content from Obsidian vault
(define (load-from-obsidian filename)
  (call-with-input-file 
    (build-path obsidian-vault-path filename)
    (λ (in) (read-line in))))

;; Command registration system
(define (register-command name func)
  (hash-set! commands name func))

(define commands (make-hash))

;; Command to save content
(define (cmd-save)
  (let ([filename (send editor get-value)])
    (if (not (string=? filename ""))
        (begin
          (save-to-obsidian filename "Content saved!")
          (send status-message set-value "File saved successfully.")
          (send editor set-value ""))
        (send status-message set-value "Please enter a filename."))))

;; Command to load content
(define (cmd-load)
  (let ([filename (send editor get-value)])
    (if (not (string=? filename ""))
        (begin
          (let ([content (load-from-obsidian filename)])  ;; Use let here
            (send editor set-value content)
            (send status-message set-value "File loaded successfully."))
          )
        (send status-message set-value "Please enter a filename."))))

;; Register commands
(register-command "save" cmd-save)
(register-command "load" cmd-load)

;; Show the frame
(send frame show #t)