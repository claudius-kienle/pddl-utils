(define (problem impossible-blocks-problem)
  (:domain simple-blocks)
  (:objects
    a b - block)
  (:init
    (on a b)
    (clear a)
    (ontable b)
    (handempty))
  (:goal (and
    (on a b)
    (on b a))))