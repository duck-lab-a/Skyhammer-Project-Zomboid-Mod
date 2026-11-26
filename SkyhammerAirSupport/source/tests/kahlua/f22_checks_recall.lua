-- Recalled right after the mark: the bombs already away still land, the flight's radio stops
column()
onStation()
mark(140, 100)
run(1000)
S.Recall("f22")
SAID = {}
run(11000)
check(alive() == 0, "the bombs away land after the recall (" .. alive() .. ")")
check(not said("F22Release") and not said("F22Off") and not said("F22Winchester"), "no strike radio after the recall")
check(S.F22Track() == nil, "no map line")
done("recall")
