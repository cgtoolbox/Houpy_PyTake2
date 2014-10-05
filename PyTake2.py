import hou

###################
##### PyTake2 #####
###################

# Author: Guillaume Jobst
# Email: contact@guillaume-j.com
# Web: www.guillaume-j.com

# This module allows the creation / editions of takes
# in Houdini through Python. Work with all version of Houdini
# Apprentice, Indie, Master or Escape.

# To create a take:
# import PyTake2 as pt
# my_take = pt.Take("mytake")
# an empty take called "mytake" will by added to the scene
# for more info about editing takes, adding parms / nodes etc.
# have a look on the PyTake2_help.pdf
# or visit www.guillaume-j.com


def currentTake():
    '''
        Return the current take.
        @return: Take
    '''
    currentName = hou.expandString('$ACTIVETAKE')
    if currentName == "Main":
        print("Current take is Main take")
        return None
    else:
        return _readScript(currentName)
    
def ls(pattern=""):
    '''
        Return the list of takes in the scene.
        @param pattern: (str) pattern: *str all take's name which ends with 'str' 
                              pattern: str* all tak's name which starts with 'str'
                              pattern: str take's name which is equal to 'str'.
                              If pattern is empty, returns all takes.
        @return: list
    '''
    out_list = []
    for take in _listTakeNames():
        if take == "Main":
            continue
        
        if pattern:
            
            if pattern.startswith("*"):
                if not take.endswith(pattern.replace("*","")):
                    continue
                
            elif pattern.endswith("*"):
                if not take.startswith(pattern.replace("*","")):
                    continue
                
            else:
                if take != pattern:
                    continue
            
        out_list.append(_readScript(take))
        
    return out_list


def setAutoMode(toggle=True):
    '''
        Set the take mode "automode" on / off
        @param toggle: (bool) Switch automode on / off. 
        @return: bool
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
        @return: bool
    '''
    n = take.name
    result = hou.hscript("takeset " + n)
    
    if result[1]:
        raise TakeSetError("Take '{0}' not found.".format(n))
    
    else:
        return True
    
def returnToMainTake():
    '''
        Set Main take as current take.
        @return: bool
    '''
    result = hou.hscript("takeset Main")
    if result[1]:
        raise TabError(result[1])

    return True

def takeFromName(take_name):
    '''
        Return a Take object from a given take name.
        @return: Take
    '''
    if not take_name in _listTakeNames():
        raise TakeError(take_name + " not found in take list.")

    out_take = _readScript(take_name)
    return out_take

def takeFromFile(file_path, parent=""):
    '''
        Create a take from a file saved with Take.saveToFile().
        @param file_path: (str) File to load.
        @param parent:  (str) Name of parent take, if empty, parent take will be current take
        @return: Take
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

###################
# Main take class #
###################
class Take(object):
    '''
        The Take class, to create a new take instanciate this class.
        @param name: (str) Name of the take.
        @param parent: (Take) Parent take, if empty, parent take will be current take.
        @param set_to_current: (bool) If set to True, the take will be set as current take.
        @param parms_dict: (dict) This will add parms / objects to the take. must be : { node_path : { parmName : parmValue }, ...}. 'ParmValue can be None.
        @param add_to_scene: (bool) Must be set to True.
        @return: Take
    '''
    
    def __init__(self, name="pytake", parent="", set_to_current=False, parms_dict={}, set_parms=False, add_to_scene=True):
        
        if not isinstance(parms_dict, dict):
            msg = "'parms_dict' must be a dictionary of "
            msg += "{ object : {parm_name : parm_value} } "
            msg += "parm_value can be None."
            raise TakeError(msg)
            
        self.set_to_current = set_to_current
        self.node_included = {}
        
        self.parms_dict = parms_dict
        
        # Construc take's name
        if add_to_scene:
            self.name = _incName(_checkName(name))
        else:
            self.name = _checkName(name)
            
        # Construct parent string
        if parent:
            if parent not in _listTakeNames() and parent != "Main":
                msg = "ERROR: Can not find parent take: " + parent
                msg += " Main take will be set as parent."
                print(msg)
                parent = "Main"
                
            self.parent = "-p " + parent
        else:
            self.parent = ""
            
        # Create Take and add it to the list of takes
        if add_to_scene:
            self._createTake()
            
        # Constuct parameters dict
        if parms_dict != {}:
            for key in parms_dict.keys():
                n = hou.node(key)
                if n:
                    self.includeParms(key, parms_dict[key], include=True, set_parms_value=set_parms)
            
        if self.set_to_current:
            hou.hscript("takeset " + self.name)
        else:
            hou.hscript("takeset Main")


    def __str__(self):
        
        out = "PyTake '"
        out += self.name + "' "
        out += "Members: "
        out += str(self.parms_dict)
        
        return out
    
    #Create the take and add it to the scene if auto_set
    def _createTake(self):
        
        if self.name in _listTakeNames():
            raise TakeCreationError("Can not add take '{0}', already found in take list.".format(self.name))

        
        hs_out = hou.hscript("takeadd {0} {1}".format(self.parent, self.name))
        
        if not hs_out[1]:
            return True
        
        else:
            raise TakeCreationError("Can not create take named: " + self.name)

    
    # Include a flag (Display / Render ) in the current take.
    def _includeExcludeFlag(self, flag, node_path, includeFlag, set_flag, flag_value):
        
        # Check if node_path is correct
        n = None
        if not isinstance(node_path, hou.Node):
        
            if not hou.node(node_path):
                raise InvalidNode(node_path)
            n = hou.node(node_path)
            
        else:
            if not node_path:
                raise InvalidNode()
            n = node_path
            node_path = node_path.path()
        
        # Method to update the flag_included dict
        def includeFlagToDic(flag_to_dic):

            flag_val = None
            if flag_to_dic == "display_flag":
                flag_val = n.isDisplayFlagSet()
            elif flag_to_dic == "render_flag":
                flag_val = n.isDisplayFlagSet()
            else:
                flag_val = n.isBypassed()
            
            # Include flag in the dic
            if includeFlag:
                
                if node_path in self.node_included.keys():
                    tmp = self.node_included[node_path]
                    tmp[flag_to_dic] = flag_val
                    self.node_included[node_path] = tmp
                else:
                    self.node_included[node_path] = {flag_to_dic : flag_val}
            
            # Remove flag from the dic
            else:
                tmp = self.node_included[node_path]
                tmp.pop(flag_to_dic, None)
                self.node_included[node_path] = tmp
        
        # Check if the node has correct flag
        
        if flag == "-d":
            try:
                n.isDisplayFlagSet()
                includeFlagToDic("display_flag")
                
            except AttributeError:
                raise InvalidFlagType("Node: {0} does not have display flag.".format(node_path))

        elif flag == "-b":
            try:
                n.isBypassed()
                includeFlagToDic("bypass_flag")
                
            except AttributeError:
                raise InvalidFlagType("Node: {0} does not have bypass flag.".format(node_path))

        else:
            try:
                n.isRenderFlagSet()
                includeFlagToDic("render_flag")
                
            except AttributeError:
                raise InvalidFlagType("Node: {0} does not have render flag.".format(node_path))

                
        # Set current take as current
        self.setCurrent()
        
        # Check include / excluse flag
        if includeFlag:
            includeFlag = ""
        else:
            includeFlag = "-u"
            
        # Clean the dict with empty parms dict
        if node_path in self.node_included.keys():
            if self.node_included[node_path] == {}:
                self.node_included.pop(node_path, None)

        result = hou.hscript("takeinclude {0} {1} {2}".format(includeFlag, flag, node_path))
        if result[1]:
            raise TakeError(result[1])

        
        else:
            # Set flag if set_flag and return True
            if flag == "-d" and set_flag and includeFlag != "-u":
                n.setDisplayFlag(flag_value)
                return True
            
            if flag == "-r" and set_flag and includeFlag != "-u":
                n.setRenderFlag(flag_value)
                return True
            
            if flag == "-b" and set_flag and includeFlag != "-u":
                n.bypass(flag_value)
                return True

    def includeRenderFlag(self, node, include=True, set_flag=False, flag_value=True):
        '''
            Include render flag of the node_path in the take.
            @param node: (str) path of the node or instance of hou.Node()
            @param toggle: (bool) Flag Include / Exclude switch.
            @param set_flag: (bool) Set the node's render flag.
            @param flag_value: (bool) Value of the flag to be set.
            @return: bool
        '''
        self._includeExcludeFlag("-r", node, include, set_flag, flag_value)
        
        
    def includeDisplayFlag(self, node, include=True, set_flag=False, flag_value=True):
        '''
            Include display flag of the node_path in the take.
            @param node: (str) path of the node or instance of hou.Node()
            @param toggle: (bool) Flag Include / Exclude switch.
            @param set_flag: (bool) Set the node's render flag.
            @param flag_value: (bool) Value of the flag to be set.
            @return: bool
        '''
        self._includeExcludeFlag("-d", node, include, set_flag, flag_value)
        
    def includeBypassFlag(self, node, include=True, set_flag=False, flag_value=True):
        '''
            Include bypass flag of the node_path in the take.
            @param node: (str) path of the node or instance of hou.Node()
            @param toggle: (bool) Flag Include / Exclude switch.
            @param set_flag: (bool) Set the node's render flag.
            @param flag_value: (bool) Value of the flag to be set.
            @return: bool
        '''
        self._includeExcludeFlag("-b", node, include, set_flag, flag_value)
        

    def includeParms(self, node, parms_dict={}, include=True,  set_parms_value=False):
        '''
            Include / exclude the given node - parms in the take.
            @param node: (str or hou.Node) The node path or the a hou.Node instance, to be included in the take.
            @param parms_dict: (dict) Dictionary of parms:value to be included, value can be None, if empty all the parms of the node will be added.
            @param include: (bool) The toggle include / exclude datas from / to the take.
            @param set_parms_value: (bool) The switch on/off to set parms value from the parms dict.
            @return: dictionary of parms / object
        '''
        # Check node
        
        if not isinstance(node, hou.Node):
            n = hou.node(str(node))
            if not n:
                raise InvalidNode(node)
        else:
            n = node
            if not n:
                raise InvalidNode(node.path())

        node_path = n.path()
        
        # Include flag
        if include:
            include_flag = ""
        else:
            include_flag = "-u"
        
        # Set Current take
        self.setCurrent()
        
        # Do parms string
        parms_included = {}
        
        # If dic is empty, add all parms
        if parms_dict == {}:
            
            all_parms = [p.name() for p in n.parms()]
            for parm in all_parms:
                parms_included[parm] = n.parm(parm).eval()
                
            result = hou.hscript("takeinclude {0} {1} *".format(include_flag,
                                                                  node_path))
            if result[1]:
                raise TakeSetError(result[1])
            
        # Add parms dict
        else:

            for key in parms_dict.keys():
                
                if key == "display_flag":
                    result = hou.hscript("takeinclude {0} -d {1}".format(include_flag,
                                                                          node_path))
                    
                    if result[1]:
                        raise TakeSetError(result[1])

                    parms_included[key] = parms_dict[key]
                    continue
                
                elif key == "render_flag":
                    result = hou.hscript("takeinclude {0} -r {1}".format(include_flag,
                                                                          node_path))
                    
                    if result[1]:
                        raise TakeSetError(result[1])

                    parms_included[key] = parms_dict[key]
                    continue
                
                elif key == "bypass_flag":
                    result = hou.hscript("takeinclude {0} -b {1}".format(include_flag,
                                                                          node_path))
                    
                    if result[1]:
                        raise TakeSetError(result[1])

                    parms_included[key] = parms_dict[key]
                    continue
                
                else:
                    if n.parm(key):
                        parms_string = str(key)
                        parms_included[key] = parms_dict[key]
                        
                    else:
                        print("Warning, parm: '" + key + "' not found on node '" + node_path + "', skiped.")
                        parms_string = ""
            
                    result = hou.hscript("takeinclude {0} {1} {2}".format(include_flag,
                                                                          node_path,
                                                                          parms_string))
                    if result[1]:
                        raise TakeSetError(result[1])
        
        
        # Set params value if set_parms_value
        if set_parms_value and include and parms_dict != {}:
            for k in parms_dict.keys():
                if k == "display_flag":
                    try:
                        n.setDisplayFlag(parms_dict[k])
                    except AttributeError:
                        print(n.path() + " do not have display flag, skipped.")
                        
                elif k == "render_flag":
                    try:
                        n.setRenderFlag(parms_dict[k])
                    except AttributeError:
                        print(n.path() + " do not have render flag, skipped.")
                        
                elif k == "bypass_flag":
                    try:
                        n.bypass(parms_dict[k])
                    except AttributeError:
                        print(n.path() + " do not have bypass flag, skipped.")
                else:
                    if  n.parm(k):
                        if parms_dict[k]:
                            try:
                                n.parm(k).set(parms_dict[k])
                            except TypeError as e:
                                print(e)
                                print("Error: Base value type for parm '" + k + "', skipped.")
                    else:
                        print("Warning, node '" + n.path() + "' does not have parm '" + k +"', skipped.")
    

        # Add data
        if include:
            if node_path not in self.node_included.keys():
                self.node_included[node_path] = parms_included
            else:
                tmp = self.node_included[node_path]
                for j in parms_included.keys():
                    
                    tmp[j] = parms_included[j]
                    
                self.node_included[node_path] = tmp
        
        # Remove data
        else:
            # Remove all datas 
            if node_path in self.node_included.keys():
                if self.node_included[node_path] == parms_included:
                    self.node_included.pop(node_path, None)
                else:
                    # remove only data found in common
                    for k in parms_included.keys():
                        if k in self.node_included[node_path].keys():
                            self.node_included[node_path].pop(k, None)
                            
                # Clean the dict with empty parms dict
                if node_path in self.node_included.keys():
                    if self.node_included[node_path] == {}:
                        self.node_included.pop(node_path, None)
                
        return self.node_included
    
    def includeParmsFromTake(self, take, force=False):
        '''
            Include all parms from a giver take to this take.
            @param force: (bool) Ff a source take has the same included parameter as the destination, the source will overwrite the destination
            @return: bool
        '''
        name = take.getName()
        if name not in _listTakeNames():
            raise TakeError("Can not find take: " + name)
        
        if force:
            force = "-f"
        else:
            force = ""
        
        result = hou.hscript("takemerge {0} {1} {2}".format(force, self.name, name))
        if result[1]:
            raise TakeError(result[1])
        
        tmp = dict(self.node_included.items() + take.getNodeIncluded().items())
        self.node_included = tmp
        
        return True
    
    def getNodeIncluded(self):
        '''
            Return a dictionary node / parms included to the take.
            @return: dictionary of node / parms
        '''
        
        if self.name not in _listTakeNames():
            raise TakeError("Can not find take: " + self.name)
        
        return self.node_included
    
    def getNodeIncludedStr(self):
        '''
            Return a clean string of node / parms included to the take.
            @return: dictionary of node / parms
        '''
        if self.name not in _listTakeNames():
            raise TakeError("Can not find take: " + self.name)
        
        out = "Nodes and parms included in take: "+ self.name + "\n\n"
        
        for key in self.node_included.keys():
            out += key + ":\n"
            if self.node_included[key]:
                for i in self.node_included[key].keys():
                    out += " "*4 + str(i) + " : " + str(self.node_included[key][i]) + "\n"
                out += "\n"
                
        print out
        return out
    
    def isCurrent(self):
        ''' 
           
            Check if this take if the current take.
            @return: bool
        '''
        if self.name == hou.expandString("$ACTIVETAKE"):
            return True
        return False
    
    def setCurrent(self):
        ''' 
            Set take as current take.
            @return: bool
        '''
        result = hou.hscript("takeset " + self.name)
        
        if result[1]:
            raise TakeSetError("Take '{0}' not found.".format(self.name))

        else:
            return True
    
    def setName(self, name):
        '''
            Rename the current take.
            @return: string
        '''
        if name == self.name:
            return False
        
        name = _incName(_checkName(name))
        
        result = hou.hscript("takename " + self.name + " " + name)
        if result[1]:
            raise TakeError(result[1])

        else:
            self.name = name
            return name
    
    def copy(self, name="", set_current=False):
        '''
            Return a copy of that take and add it to the list
            @param name: (str) Name of the new take, if empty, name will be 'take'_copy
            @param set_current: (bool) if True, the copied take will be set as current Take.
            @return: Take
        '''
        if self.name not in _listTakeNames():
            raise TakeError("Can not find take: " + self.name)
        
        if not name:
            name = self.name + "_copy"
            
        out_take = Take(name)
        for k in self.node_included:
            out_take.includeParms(k, self.node_included[k])
        
        if set_current:
            setTake(name)
        else:
            returnToMainTake()
        
        return out_take
        
    def getName(self):
        '''
            Return take's name
            @return: string
        '''
        if self.name not in _listTakeNames():
            raise TakeError("Can not find take: " + self.name)
        
        return self.name
    
    def remove(self, recursive=False):
        '''
            Remove the take from the take list.
            @param recursive: (bool) if True, remove all children take as well.
            @return: bool
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
        
    def existInList(self):
        '''
            Return True if take exists in the scene, False if not.
            @return: bool
        '''
        return self.name in _listTakeNames()
    
    def saveToFile(self, file_path, recursive=False):
        '''
            Save the given take to a external file.
            @param file_path: (str) A valid path where to save the file.
            @param recursive: (bool) if True, save as well as children take of the node.
            @return: bool
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

#Check if any take with the current given "name"
#Already exists, if yes, increment the name of the take by an int.
def _incName(name):
    
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
            print("digit_part " + str(digit_part))
            name = name[0:-digic_len]
            print("name " + str(name))
            name += str(digit_part+1)
        
        # Incremente only once
        else:
            name += str(ind)
            ind += 1

    return name

#Check if the given name has only legal char.
#If not, replace illegal char with _
def _checkName(name):
    
    out_name = ""
    legal_chars = "abcdefghijklmnopqrstuvwxyz0123456789_"
    
    for c in name:
        if c.lower() in legal_chars:
            out_name += c
            
        else:
            out_name += "_"
            
    return out_name


# Return all takes' name of the scene
def _listTakeNames():
    
    return [n.replace(" ", "") for n in hou.hscript("takels")[0].split("\n") if n]


# Read take data and create Take() object
def _readScript(take_name):
    
    if not take_name in _listTakeNames():
        raise TakeError(take_name + " not found in take list.")
    
    script = hou.hscript("takescript " + take_name)
    if script[1]:
        raise TakeError(script[1])
    
    # Make current take
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
                            data_dict[node_path] = {tmp_parm.name():n.parm(tmp_parm.name()).eval()}
                            
                for i in ['x','y','z','u','v','w']:
                    tmp_parm = n.parm(parm_name + str(i))
                    if tmp_parm:
                        if node_path in data_dict:
                            tmp = data_dict[node_path]
                            tmp[tmp_parm.name()] = n.parm(tmp_parm.name()).eval()
                            data_dict[node_path] = tmp
                        else:
                            data_dict[node_path] = {tmp_parm.name():n.parm(tmp_parm.name()).eval()}
            
    
    out_take = Take(take_name, add_to_scene=False)
    out_take.node_included = data_dict.copy()
    
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
    
    