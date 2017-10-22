import hou

#
# Python module to create and edit takes in SideFX Houdini.
#
# MIT License
# 
# Copyright (c) 2017 Guillaume Jobst, www.cgtoolbox.com
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#

# Static methods
def currentTake():
    '''
        Return the current take.
    '''
    currentName = hou.expandString('$ACTIVETAKE')
    if currentName == "Main":
        print("Current take is Main take")
        return None
    else:
        return _readScript(currentName)
    
def ls(name_only=False, pattern="", pattern_ignore_case=False):
    '''
        Return the list of takes in the scene.
        Return a list of Take object or a list of string if name_only is set to True.
        A Houdini-style pattern can be set with pattern.
    '''

    if name_only:
        return  _listTakeNames()

    out_list = []
    for take in _listTakeNames():
        if take == "Main":
            continue
        
        if pattern:
            
            m = hou.patternMatch(pattern, take, pattern_ignore_case)
            if m == 1:
                out_list.append(_readScript(take, make_current=False))

        else:
            out_list.append(_readScript(take, make_current=False))
        
    return out_list

def setAutoMode(toggle=True):
    '''
        Set the take mode "automode" on / off
    '''
    if toggle:
        toggle = "on"
    else:
        toggle = "off"
        
    result = hou.hscript("takeautomode " + toggle)
    if result[1]:
        raise TakeError(result[1])

    else:
        return True

def setTake(take):
    '''
        Set the given take as current take.
        take argument can be either a Take name ( string ) or a Take object.
    '''
    if isinstance(take, Take):
        take = take.name
    else:
        take = str(take)

    result = hou.hscript("takeset " + take)
    
    if result[1]:
        raise TakeSetError("Take '{0}' not found.".format(take))
    
    else:
        return True
    
def returnToMainTake():
    '''
        Set Main take as current take.
    '''
    result = hou.hscript("takeset Main")
    if result[1]:
        raise TakeSetError(result[1])

    return True

def takeFromName(take_name):
    '''
        Return a Take object from a given take name.
    '''
    if not take_name in _listTakeNames():
        raise TakeError(take_name + " not found in take list.")

    out_take = _readScript(take_name)
    return out_take

def takeFromFile(file_path, parent=""):
    '''
        Create a take from a file saved with Take.saveToFile().
        file_path: (str) File to load.
        parent: (str) Name of parent take, if empty, parent take will be current take
        returns a Take object.
    '''

    take_list_before = _listTakeNames()

    if parent:
        parent = "-p " + parent
    
    result = hou.hscript("takeload {0} {1}".format(parent, file_path))
    if result[1]:
        raise TakeError(result[1])

    take_list_after= _listTakeNames()
    
    # Find take's name
    take_name = list(set(take_list_after) - set(take_list_before))[0]
    out_take = _readScript(take_name)
    return out_take


# Take members container
class TakeMember(object):
    '''
        Used internally by Take objects to store take's members ( nodes and parameters ).
    '''
    __slots__ = ["flags", "parms", "node"]

    def __init__(self, node=None, flags=[], parms=[]):
        
        self.node = node

        if flags is not None and not hasattr(flags, "__iter__"):
            self.flags = [flags]
        else:
            self.flags = []

        self.parms = parms

    def __str__(self):

        return ("Node: {0}\n"
                "Flags included {1}\n"
                "Parms included: {2}".format(self.node, self.flags, self.parms))

    def __repr__(self):

        return self.__str__()


# Main Take classe
class Take(object):
    '''
        The Take class, to create a new take instanciate this class.
        name: (str) Name of the take.
        parent: (Take) Parent take, if empty, parent take will be current take.
        set_to_current: (bool) If set to True, the take will be set as current take.
        include_node: (hou.Node or string) A hou.Node object or a node path to be included in the take.
                                           It can be a list of hou.Node or string.
        include_parm: (hou.parm or hou.parmTuple) a parm ( or parm tuple ) object to be included in the take.
                                                  It can be a list.
                                            
        _add_to_scene: (bool) Must be set to True used only internally.
    '''
    
    def __init__(self, name="pytake", parent="", set_to_current=False,
                 include_node=None, include_parm=None, _add_to_scene=True):
        
        if not hasattr(include_parm, "__iter__"):
            if include_parm is None:
                include_parm = []
            else:
                include_parm = [include_parm]

        if not hasattr(include_node, "__iter__"):
            if include_node is None:
                include_node = []
            else:
                include_node = [include_node]
            
        self.set_to_current = set_to_current
        self.take_members = {}
        
        # Construc take's name
        if _add_to_scene:
            self.name = _incName(_checkName(name))
        else:
            self.name = _checkName(name)
            
        # Construct parent string
        if not parent:
            if hou.expandString('$ACTIVETAKE') != "Main":
                parent = hou.expandString('$ACTIVETAKE')
        else:
            if isinstance(parent, Take):
                parent = parent.getName()

        if parent:
            self._parent = "-p " + parent
            self.parent = parent
        else:
            self._parent = ""
            self.parent = parent

            
        # Create Take and add it to the list of takes
        if _add_to_scene:
            self._createTake()

        # if node or parms included add it
        if include_parm:
            self.includeParms(include_parm)

        if include_node:
            for n in include_node:
                self.includeParmsFromNode(n)
            
        # set current
        if _add_to_scene:
            if self.set_to_current:
                hou.hscript("takeset " + self.name)
            else:
                hou.hscript("takeset Main")

    def __str__(self):
        
        out = "PyTake '"
        out += self.name + "'\n"
        out += "Members:\n"
        for k, v in self.take_members.iteritems():
            out += "  -{0}:\n {1}\n".format(k, str(v))
        
        return out
    
    def __repr__(self):

        return self.__str__()

    #Create the take and add it to the scene if auto_set
    def _createTake(self):
        
        if self.name in _listTakeNames():
            raise TakeCreationError("Can not add take '{0}', already found in take list.".format(self.name))

        
        result = hou.hscript("takeadd {0} {1}".format(self._parent, self.name))
        
        if not result[1]:
            return True
        
        else:
            raise TakeCreationError("Can not create take named: " + self.name)
    
    # Include a flag (Display / Render ) in the current take.
    def _includeExcludeFlag(self, flag, node, includeFlag, set_flag, flag_value):
        
        # Check if node_path is correct
        node = self._convertNode(node)
        node_path = node.path()
        
        # Check if the node has correct flag
        if flag == "-d":
            try:
                node.isDisplayFlagSet()
                self._updateSavedData(node, parm=None, flag="display_flag")
            except AttributeError:
                raise InvalidFlagType(("Node: {0} does not have"
                                       " display flag.".format(node_path)))

        elif flag == "-b":
            try:
                node.isBypassed()
                self._updateSavedData(node, parm=None, flag="bypass_flag")
            except AttributeError:
                raise InvalidFlagType("Node: {0} does not have bypass flag.".format(node_path))

        else:
            try:
                node.isRenderFlagSet()
                self._updateSavedData(node, parm=None, flag="render_flag")
            except AttributeError:
                raise InvalidFlagType("Node: {0} does not have render flag.".format(node_path))
        
        # Check include / excluse flag
        includeFlag = "-u"
        if includeFlag:
            includeFlag = ""
        

        self.setCurrent()

        result = hou.hscript("takeinclude {0} {1} {2}".format(includeFlag, flag, node_path))
        if result[1]:
            raise TakeError(result[1])
        
        # Set flag if set_flag and return True
        if flag == "-d" and set_flag and includeFlag != "-u":
            node.setDisplayFlag(flag_value)
            return True
            
        if flag == "-r" and set_flag and includeFlag != "-u":
            node.setRenderFlag(flag_value)
            return True
            
        if flag == "-b" and set_flag and includeFlag != "-u":
            node.bypass(flag_value)
            return True

    def _updateSavedData(self, node, parm=None, flag=None, include=True):

        if parm is None and flag is None:
            return

        node = self._convertNode(node)
        node_path = node.path()

        member = self.take_members.get(node_path)

        if not member:
            
            if parm is None:
                _parm = []
            else:
                _parm = [parm]

            member = TakeMember(node=node,
                           parms=_parm,
                           flags=flag)

            if include:
                self.take_members[node_path] = member
        
        if include:

            if flag is not None:
                if not flag in member.flags:
                    member.flags.append(flag)

            if parm:
                pn = parm.name()
                if not pn in member.parms:
                    member.parms.append(pn)
        else:
            if flag is not None:
                if flag in member.flags:
                    member.flags.pop(member.flags.index(flag))

            if parm:
                pn = parm.name()
                if pn in member.parms:
                    member.parms.pop(member.parms.index(pn))

        # flush empty member
        if len(member.flags) == 0 and len(member.parms) == 0:
            self.take_members.pop(node_path)

    def _convertNode(self, node):

        if isinstance(node, str):
            node = hou.node(node)
            if node is None:
                raise InvalidNode(node)
            return node

        if hasattr(node, "__iter__"):
            
            out_node = []
            for n in node:

                if isinstance(n, str):
                    _n = hou.node(n)
                    if _n is None:
                        raise InvalidNode(n)
                    out_node.append(_n)

                elif isinstance(n, hou.Node):
                    out_node.append(n)

            return out_node

        if not isinstance(node, hou.Node):
            raise InvalidNode(str(node))

        return node

    # Include flags
    def includeRenderFlag(self, node, include=True, set_flag=False, flag_value=True):
        '''
            Include render flag of the node_path in the take.
            node: (str) path of the node or instance of hou.Node()
            include: (bool) Flag Include / Exclude switch.
            set_flag: (bool) Set the node's render flag.
            flag_value: (bool) Value of the flag to be set.

            Raise a InvalidFlagType if the given node doesn't have a render flag
            
        '''
        self._includeExcludeFlag("-r", node, include, set_flag, flag_value)
        
    def includeDisplayFlag(self, node, include=True, set_flag=False, flag_value=True):
        '''
            Include display flag of the node_path in the take.
            node: (str) path of the node or instance of hou.Node()
            toggle: (bool) Flag Include / Exclude switch.
            set_flag: (bool) Set the node's render flag.
            flag_value: (bool) Value of the flag to be set.

            Raise a InvalidFlagType if the given node doesn't have a display flag
        '''
        self._includeExcludeFlag("-d", node, include, set_flag, flag_value)
        
    def includeBypassFlag(self, node, include=True, set_flag=False, flag_value=True):
        '''
            Include bypass flag of the node_path in the take.
            node: (str) path of the node or instance of hou.Node()
            toggle: (bool) Flag Include / Exclude switch.
            set_flag: (bool) Set the node's render flag.
            flag_value: (bool) Value of the flag to be set.

            Raise a InvalidFlagType if the given node doesn't have a bypass flag
        '''
        self._includeExcludeFlag("-b", node, include, set_flag, flag_value)
        
    # Include parameters
    def includeParms(self, parms, include=True):
        ''' 
            Include given hou.Parm or hou.ParmTuple object(s) in the take.
        '''

        if not hasattr(parms, "__iter__"):
            parms = [parms]

        self.setCurrent()

        include_flag = ""
        if not include:
            include_flag = "-u"

        for parm in parms:

            node = parm.node()
            node_path = node.path()
            parm_string = parm.name()
            
            result = hou.hscript("takeinclude {0} {1} {2}".format(include_flag,
                                                                  node_path,
                                                                  parm_string))
            if result[1]:
                raise TakeSetError(result[1])

            self._updateSavedData(node, parm)

    def includeParmsFromNode(self, node, parms_name_filter=None, include=True):
        '''
            Include parameters from a given hou.Node or node path object.
            Parameters can be filtered with an houdini-style pattern matching "parms_name_filter"
            which can be either a single string or a list of string.
        '''

        if not hasattr(parms_name_filter, "__iter__"):
            if parms_name_filter is None:
                parms_name_filter = []
            else:
                parms_name_filter = [parms_name_filter]

        # Check node
        node = self._convertNode(node)
        node_path = node.path()
        
        # Include flag
        if include:
            include_flag = ""
        else:
            include_flag = "-u"
        
        self.setCurrent()

        # whole node ( no filer )
        if not parms_name_filter:
            result = hou.hscript("takeinclude {0} {1} *".format(include_flag,
                                                                node_path))
            if result[1]:
                raise TakeSetError(result[1])

            for parm in node.parms():
                self._updateSavedData(node, parm)

        # with filter name
        else:
            parms = []
            for parm in node.parms():
                for f in parms_name_filter:
                    if hou.patternMatch(f, parm.name()) == 1:
                        parms.append(parm)
                        break
            
            self.includeParms(parms)
    
    def includeParmsFromTake(self, take, force=False):
        '''
            Include all parms from a given take to this take.
            The take parameter can be either a Take object or a take name.
            force: (bool) Force a source take has the same included parameter as the destination,
                          the source will overwrite the destination
        '''

        if isinstance(take, Take):
            name = take.getName()
        else:
            name = take

        if name not in _listTakeNames():
            raise TakeError("Can not find take: " + name)
        
        if force:
            force = "-f"
        else:
            force = ""
        
        result = hou.hscript("takemerge {0} {1} {2}".format(force, self.name, name))
        if result[1]:
            raise TakeError(result[1])
        
        tmp = dict(self.take_members.items() + take.getTakeMembers().items())
        self.take_members = tmp
        
        return True
    
    def getTakeMembers(self):
        '''
            return a dictionnary of TakeMembers objects included in the take.
        '''
        
        if self.name not in _listTakeNames():
            raise TakeError("Can not find take: " + self.name)
        
        return self.take_members
    
    def getTakeMembersStr(self):
        '''
            return a string version of take's members.
        '''
        if self.name not in _listTakeNames():
            raise TakeError("Can not find take: " + self.name)
        
        out = "Nodes and parms included in take: "+ self.name + "\n\n"
        
        for key in self.take_members.keys():
            out += key + ":\n"
            if self.take_members[key]:
                for i in self.take_members[key].keys():
                    out += " "*4 + str(i) + " : " + str(self.take_members[key][i]) + "\n"
                out += "\n"
                
        return out
    
    def isCurrent(self):
        ''' 
            Returns True if the take is the current take, False otherwise.
        '''
        if self.name == hou.expandString("$ACTIVETAKE"):
            return True
        return False
    
    def setCurrent(self):
        ''' 
            Set take as current take.
        '''
        result = hou.hscript("takeset " + self.name)
        
        if result[1]:
            raise TakeSetError("Take '{0}' not found.".format(self.name))

        return True
    
    def setName(self, name):
        '''
            Rename the current take.
        '''
        if name == self.name:
            return False
        
        name = _incName(_checkName(name))
        
        result = hou.hscript("takename " + self.name + " " + name)
        if result[1]:
            raise TakeError(result[1])
        
        self.name = name
        return name
       
    def setParent(self, parent):
        '''
            Set the current take's parent, it can be either a Take object, a take name
            or None. 
            If None, the take's parent will be set to Main take.
        '''

        if parent is None:
            result = hou.hscript("takemove {0} Main".format(self.getName()))
            if result[1]:
                raise TakeError(result[1])
            self.parent = "Main"
            self._parent = "-p Main"

        else:

            if isinstance(parent, Take):
                parent = parent.getName()

            if not parent in _listTakeNames():
                raise TakeError("Take {0} not found in take list.".format(parent))

            result = hou.hscript("takemove {0} {1}".format(self.getName(),
                                                           parent))
            if result[1]:
                raise TakeError(result[1])

            self.parent = parent
            self._parent = "-p " + parent

    def getName(self):
        '''
            Return take's name
        '''
        if self.name not in _listTakeNames():
            raise TakeError("Can not find take: " + self.name)
        
        return self.name

    def getParent(self):
        '''
            Return the take's parent as Take object, or None.
        '''
        if not self.parent:
            return None

        return takeFromName(self.parent)
    
    def copy(self, name="", set_current=False):
        '''
            Return a copy of that take and add it to the list of take.
        '''
        if self.name not in _listTakeNames():
            raise TakeError("Can not find take: " + self.name)
        
        if not name:
            name = self.name + "_copy"
            
        out_take = Take(name)
        for k in self.take_members:
            
            p = hou.parm(k)
            if p is None:
                p = hou.parmTuple(k)

            if p is None:
                continue

            out_take.includeParms(k, self.take_members[k])
        
        if set_current:
            setTake(name)
        else:
            returnToMainTake()
        
        return out_take

    def remove(self, recursive=False):
        '''
            Remove the take from the take list.
            recursive: (bool) if True, remove all child takes as well.
        '''
        if recursive:
            recursive = "-R"
        else:
            recursive = ""
        
        result = hou.hscript("takerm " + recursive + " " + self.name)
        if result[1]:
            raise TakeDeleteError(result[1])
        else:
            return True
        
    def existInScene(self):
        '''
            Return True if take exists in the scene, False if not.
        '''
        return self.name in _listTakeNames()
    
    def saveToFile(self, file_path, recursive=False):
        '''
            Save the given take to a external file.
            file_path: (str) A valid path where to save the file.
            recursive: (bool) if True, save as well as children take of the node.
        '''
        
        if not self.name in _listTakeNames():
            raise TakeError(self.name + " not found in take list.")
        
        if recursive:
            recursive = "-R"
        else:
            recursive = ""
        
        result = hou.hscript("takesave -o {0} {1} {2}".format(file_path, recursive, self.name) )
        if result[1]:
            raise TakeError(result[1])
        else:
            return True
        
        
#############
# Utilities #
#############

def _incName(name):
    '''
        Check if any take with the current given "name"
        Already exists, if yes, increment the name of the take by an int.
    ''' 
       
    ind = 1
    digic_len = 0
    while name in _listTakeNames():

        digit_part = ""
        
        rever_name = list(name)[::-1]
        
        for i in rever_name:
            if not i.isdigit():
                break
            else:
                digit_part = str(i) + digit_part
        
        digic_len = len(digit_part)
        
        if digit_part:
            digit_part = int(digit_part)
            name = name[0:-digic_len]
            name += str(digit_part+1)
        
        # Incremente only once
        else:
            name += str(ind)
            ind += 1

    return name

def _checkName(name):
    '''
        Check if the given name has only legal char.
        If not, replace illegal char with _
    '''    
    out_name = ""
    legal_chars = "abcdefghijklmnopqrstuvwxyz0123456789_"
    
    for c in name:
        if c.lower() in legal_chars:
            out_name += c
            
        else:
            out_name += "_"
            
    return out_name

def _listTakeNames():
    '''
        Return all takes' name of the scene
    '''
    
    return [n.replace(" ", "") for n in hou.hscript("takels")[0].split("\n") if n]

def _readScript(take_name, make_current=True):
    '''
        Read take data and create Take() object from it.
    '''
    
    if not take_name in _listTakeNames():
        raise TakeError(take_name + " not found in take list.")
    
    script = hou.hscript("takescript " + take_name)
    if script[1]:
        raise TakeError(script[1])
    
    # Make current take
    if make_current:
        result = hou.hscript("takeset " + take_name)
        if result[1]:
            raise TakeError(result[1])
    
    data_dict = {}
    
    script = [n for n in script[0].split("\n") if n.startswith("takeinclude")]
    
    for line in script:

        line = line.replace(" -q","")
        
        # Display flag found
        def includeFlagToDic(flag, flag_label):
            if flag in line:
                node_path = line.split(" ")[-1]
                
                n = hou.node(node_path)
                if n:
                    if flag == "-d":
                        flag_val = n.isDisplayFlagSet()
                    elif flag == "-r":
                        flag_val = n.isRenderFlagSet()
                    else:
                        flag_val = n.isBypassed()
                    
                    if node_path not in data_dict.keys():
                        data_dict[node_path] = {flag_label:flag_val}
                    else:
                        tmp = data_dict[node_path]
                        tmp[flag_label] = flag_val
                        data_dict[node_path] = tmp
            
        # Render flag found
        if "-r" in line:
            includeFlagToDic("-r", "render_flag")
            
        # Display flag found
        elif "-d" in line:
            includeFlagToDic("-d", "display_flag")
            
        # Bypass flag found
        elif "-b" in line:
            includeFlagToDic("-b", "bypass_flag")
        
        # No flags found
        else:
            line_list = line.split(" ")
            node_path = line_list[1]
            n = hou.node(node_path)
            if not n:
                continue
            
            parm_name = line_list[2]
            
            # If parm exists
            if n.parm(parm_name):
                if node_path in data_dict:
                    tmp = data_dict[node_path]
                    tmp[parm_name] = n.parm(parm_name).eval()
                    data_dict[node_path] = tmp
                else:
                    data_dict[node_path] = {parm_name:n.parm(parm_name).eval()}
            
            else:
                for i in xrange(12):
                    tmp_parm = n.parm(parm_name + str(i))
                    if tmp_parm:
                        if node_path in data_dict:
                            tmp = data_dict[node_path]
                            tmp[tmp_parm.name()] = n.parm(tmp_parm.name()).eval()
                            data_dict[node_path] = tmp
                        else:
                            data_dict[node_path] = {tmp_parm.name():\
                                                    n.parm(tmp_parm.name()).eval()}
                            
                for i in ['x','y','z','u','v','w']:
                    tmp_parm = n.parm(parm_name + str(i))
                    if tmp_parm:
                        if node_path in data_dict:
                            tmp = data_dict[node_path]
                            tmp[tmp_parm.name()] = n.parm(tmp_parm.name()).eval()
                            data_dict[node_path] = tmp
                        else:
                            data_dict[node_path] = {tmp_parm.name():\
                                                    n.parm(tmp_parm.name()).eval()}
            
    
    out_take = Take(take_name, _add_to_scene=False)
    out_take.take_members = data_dict.copy()
    
    #returnToMainTake()
    return out_take

##################
# Errors classes #
##################

class TakeError(Exception):
    def __init__(self, message):
        Exception.__init__(self, message)

class TakeCreationError(TakeError):
    pass
    
class TakeDeleteError(TakeError):
    pass
        
class TakeSetError(TakeError):
    pass
        
class InvalidFlagType(TakeError):
    pass
        
class InvalidNode(TakeError):
    def __init__(self, node_path):
        Exception.__init__(self, "Invalid path: " + node_path)
    
    