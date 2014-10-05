Houpy_PyTake2
=============

This python module allows you to create and edit takes using Python.

more info: www.guillaume-j.com

simple example:

import PyTake2 as pt
my_take = pt.Take("my_take")

=> this will create a new take called "my_take" and add it to the takes list.

my_take.includeDisplayFlag(path_to_node)

=> this will include the display flag of the node "path_to_node" to the take.

