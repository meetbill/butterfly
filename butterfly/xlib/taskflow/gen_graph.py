#!/usr/bin/env python
"""
#
# This is a script to create a dot graph from database.
# Usage: $script >| task_graph.dot
#
#
"""

import datetime
import os
import sys
import time
from xlib.taskflow import model
from xlib.db import shortcuts


def _timeStampToTimeStr(ts):
    """
    converts time.time() output to timenow() string
    """
    return datetime.datetime.utcfromtimestamp(ts).isoformat()


def _timeStrNow():
    """
    time str
    """
    return _timeStampToTimeStr(time.time())


def _cmdline():
    """
    cmdline
    """
    return " ".join(sys.argv)


class Bunch(object):
    """
    generic struct with named argument constructor
    """

    def __init__(self, **kwds):
        self.__dict__.update(kwds)


class LogGlobals(object):
    """
    Log globals
    """
    isFsync = True


class TaskNodeConstants(object):
    """
    TaskNodeConstants
    """

    validRunstates = ("finished", "started", "pending", "waiting", "failed")


class DotConfig(object):
    """
    A static container of configuration data for dot graph output
    """

    runstateDotColor = {"waiting": "grey",
                        "started": "green",
                        "pending": "yellow",
                        "failed": "red",
                        "finished": "blue"}

    runstateDotStyle = {"waiting": "dashed",
                        "started": None,
                        "pending": None,
                        "failed": "bold",
                        "finished": None}

    @staticmethod
    def getRunstateDotAttrib(runstate):
        """
        getRunstateDotAttrib
        """
        color = DotConfig.runstateDotColor[runstate]
        style = DotConfig.runstateDotStyle[runstate]
        attrib = ""
        if color is not None:
            attrib += " color=%s" % (color)
        if style is not None:
            attrib += " style=%s" % (style)
        return attrib

    @staticmethod
    def getTypeDotAttrib(nodeType):
        """
        getTypeDotAttrib
        """
        attrib = ""
        return attrib

    @staticmethod
    def getDotLegend():
        """
        getDotLegend
        """
        string = '{ rank = source; Legend [shape=none, margin=0, label=<\n'
        string += '<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="4">\n'
        string += '<TR><TD COLSPAN="2">Legend</TD></TR>\n'
        for state in TaskNodeConstants.validRunstates:
            color = DotConfig.runstateDotColor[state]
            string += '<TR> <TD>%s</TD> <TD BGCOLOR="%s"></TD> </TR>\n' % (state, color)
        string += '</TABLE>>];}\n'
        return string


def _getTaskInfoDepSet(s):
    """
    getTaskInfoDepSet
    """
    # reconstruct dependencies allowing for extraneous whitespace in the file:
    s = s.strip()
    if s == "":
        return []
    return set([d.strip() for d in s.split(",")])


def write_dot_graph(job_id, filename="./graph.dot"):
    """
    write out the current graph state in dot format
    """

    dot_dir = os.path.dirname(filename)
    if not os.path.isdir(dot_dir):
        os.makedirs(dot_dir)

    task_list = []
    record_list = model.Task.select().where(model.Task.job_id == int(job_id))
    for record in record_list:
        task_dict = shortcuts.model_to_dict(record)
        task_list.append(task_dict)

    addOrder = []
    taskInfo = {}
    headNodes = set()
    tailNodes = set()

    for task in task_list:
        label = task["task_label"]
        namespace = ""
        depStr = task["task_dependencies"]
        runState = task["task_status"]
        tid = (namespace, label)
        addOrder.append(tid)
        taskInfo[tid] = Bunch(parentLabels=_getTaskInfoDepSet(depStr))

        if len(taskInfo[tid].parentLabels) == 0:
            headNodes.add(tid)

        tailNodes.add(tid)
        for plabel in taskInfo[tid].parentLabels:
            ptid = (namespace, plabel)
            if ptid in tailNodes:
                tailNodes.remove(ptid)

        taskInfo[tid].runState = runState

    with open(filename, "w") as dotFp:
        dotFp.write("// Task graph from pyflow object\n")
        dotFp.write("// Process command: '%s'\n" % (_cmdline()))
        dotFp.write("// Process working dir: '%s'\n" % (os.getcwd()))
        dotFp.write("// Graph capture time: %s\n" % (_timeStrNow()))
        dotFp.write("\n")
        dotFp.write("digraph {\n")
        dotFp.write("\tcompound=true;\nrankdir=LR;\nnode[fontsize=10];\n")
        labelToSym = {}
        namespaceGraph = {}
        for (i, (namespace, label)) in enumerate(addOrder):
            tid = (namespace, label)
            if namespace not in namespaceGraph:
                namespaceGraph[namespace] = ""
            sym = "n%i" % i
            labelToSym[tid] = sym
            attrib1 = DotConfig.getRunstateDotAttrib(taskInfo[tid].runState)
            namespaceGraph[namespace] += "\t\t%s [label=\"%s\"%s];\n" % (sym, label, attrib1)

        for (namespace, label) in addOrder:
            tid = (namespace, label)
            sym = labelToSym[tid]
            for plabel in taskInfo[tid].parentLabels:
                ptid = (namespace, plabel)
                namespaceGraph[namespace] += ("\t\t%s -> %s;\n" % (labelToSym[ptid], sym))

        for (i, ns) in enumerate(namespaceGraph.keys()):
            isNs = ((ns is not None) and (ns != ""))
            dotFp.write("\tsubgraph cluster_sg%i {\n" % (i))
            if isNs:
                dotFp.write("\t\tlabel = \"%s\";\n" % (ns))
            else:
                dotFp.write("\t\tlabel = \"%s\";\n" % ("workflow"))
            dotFp.write(namespaceGraph[ns])
            dotFp.write("\t\tbegin%i [label=\"begin\" shape=diamond];\n" % (i))
            dotFp.write("\t\tend%i [label=\"end\" shape=diamond];\n" % (i))
            for (namespace, label) in headNodes:
                if namespace != ns:
                    continue
                sym = labelToSym[(namespace, label)]
                dotFp.write("\t\tbegin%i -> %s;\n" % (i, sym))
            for (namespace, label) in tailNodes:
                if namespace != ns:
                    continue
                sym = labelToSym[(namespace, label)]
                dotFp.write("\t\t%s -> end%i;\n" % (sym, i))
            dotFp.write("\t}\n")
            if ns in labelToSym:
                dotFp.write("\t%s -> begin%i [style=dotted];\n" % (labelToSym[ns], i))
                # in LR orientation this will make the graph look messy:
                # dotFp.write("\tend%i -> %s [style=invis];\n" % (i,labelToSym[ns]))

        dotFp.write(DotConfig.getDotLegend())
        dotFp.write("}\n")


if __name__ == '__main__':
    import sys
    import inspect
    if len(sys.argv) < 2:
        print "Usage:"
        for k, v in sorted(globals().items(), key=lambda item: item[0]):
            if inspect.isfunction(v) and k[0] != "_":
                args, __, __, defaults = inspect.getargspec(v)
                if defaults:
                    print sys.argv[0], k, str(args[:-len(defaults)])[1:-1].replace(",", ""), \
                        str(["%s=%s" % (a, b) for a, b in zip(args[-len(defaults):], defaults)])[1:-1].replace(",", "")
                else:
                    print sys.argv[0], k, str(v.func_code.co_varnames[:v.func_code.co_argcount])[1:-1].replace(",", "")
        sys.exit(-1)
    else:
        func = eval(sys.argv[1])
        args = sys.argv[2:]
        try:
            r = func(*args)
        except Exception as e:
            print "Usage:"
            print "\t", "python %s" % sys.argv[1], str(func.func_code.co_varnames[:func.func_code.co_argcount])[
                1:-1].replace(",", "")
            if func.func_doc:
                print "\n".join(["\t\t" + line.strip() for line in func.func_doc.strip().split("\n")])
            print e
            r = -1
            import traceback
            traceback.print_exc()
        if isinstance(r, int):
            sys.exit(r)
