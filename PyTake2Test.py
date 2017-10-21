import hou
import PyTake2
reload(PyTake2)

def run():

    geo1 = hou.node("/obj/geo1")
    geo2 = hou.node("/obj/geo2")
    geo3 = hou.node("/obj/geo3")
    null = hou.node("/obj/geo4/null1")

    print("create take1, empty")
    take1 = PyTake2.Take(name="take1")

    print("go back to main")
    PyTake2.returnToMainTake()

    print("create takeA and B")
    # create take A and include all parameters from geo3 node
    takeA = PyTake2.Take(name="take_A")
    takeA.includeDisplayFlag(geo1)
    print takeA

    # create take B ( empty ) set take A as parent
    takeB = PyTake2.Take(name="take_B", parent=takeA)
    print("TakeB parent: " + takeB.getParent().getName())

    # add parameter to take B, here we add a parm tuple ( t )
    # as wel a a float parameter ( scale )
    takeB.includeParms([hou.node("/obj/geo1").parmTuple("t"),
                        hou.node("/obj/geo1").parm("scale")])

    # merge take C and take B
    print("create takeC from take A")
    takeC = PyTake2.Take(name="take_C")
    takeC.includeParmsFromTake(takeA)
    print("TakeC parent: " + takeC.getParent().getName())
    print("TakeC members: " + str(takeC.getTakeMembers()))
    print("Remove display flag from take C")
    takeC.includeDisplayFlag(geo1, False)
    print("TakeC members: " + str(takeC.getTakeMembers()))
    PyTake2.setTake(takeC)

    # create take D and set parent take A
    takeD = PyTake2.Take(name="take_D")
    takeD.setParent(takeA)
    print("TakeD parent: " + takeD.getParent().getName())

    # create take E and add parameters from a node according to a pattern
    PyTake2.returnToMainTake()
    takeE = PyTake2.Take(name="take_E")
    takeE.includeParmsFromNode(null, ["parm*", "cacheInput"])

    # set parent to None ( Main )
    takeE.setParent(None)

    # copy take A
    takeA.copy("take_A_COPY")

    print("current take:")
    print PyTake2.currentTake()

