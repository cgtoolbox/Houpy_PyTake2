Houpy_PyTake2
=============

This python module allows you to create and edit takes using Python.

more info: www.guillaume-j.com

simple example:

import PyTake2 as pt

mytake = pt.Take("my_take")

=> this will create a new take called "my_take" and add it to the takes list.

mytake.includeDisplayFlag(pathToNode)

=> this will include the display flag of the node "pathToNode" to the take.

