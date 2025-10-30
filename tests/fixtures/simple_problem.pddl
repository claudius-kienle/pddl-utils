(define (problem simple-blocks-problem)
    (:domain simple-blocks)
    (:objects
        a b c - block
    )
    (:init
        (clear a)
        (clear b)
        (clear c)
        (ontable a)
        (ontable b)
        (ontable c)
        (handempty)
    )
    (:goal
        (and
            (on a b)
            (on b c))
    )
)