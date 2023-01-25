import curses
import re
import os, sys

from typing import *

stack = []

base = os.path.dirname(os.path.realpath(__file__))

import __init__ as fterm # hack thing?
import colors
import control
import formatting

import platform

class Scripter:
    def __init__(self, rows: int=100, cols: int=500, skip_key: Union[int, List[int]]=10, return_key: Union[int, List[int]]=10):
        self.rows = rows
        self.cols = cols
        self.skip_key = skip_key
        self.return_key = return_key

        self.stack = []

        self.cached = {}

        self.loop_started = False
        self.fterm = fterm.FTerm(rows, cols, skip_key=skip_key, return_key=return_key)
        self.offset = 0

    def load(self, file, label=None, absolute_path=False, indentation="    "):
        filename = file
        if not label:
            label = "init"
        if not absolute_path:
            target = os.path.join(base, file)
        else:
            target = file
        with open(target) as f:
            text = f.read()
        expression = r"\s?label (.+):\n"
        labels = re.findall(expression, text)
        split = re.split(expression, text)
        split = split[1:]
        split = dict(zip(split[::2], split[1::2]))
        for key in split:
            split[key] = "\n".join([line[len(indentation):] for line in split[key].splitlines()])
        if label not in labels:
            raise ValueError(f"label \"{label}\" not found in file \"{file}\"")

        for item in split:
            self.cached[(target, item)] = split[item]

        if label != "options":
            self.stack.insert(0, (target, label, 0))
        if "options" in split:
            self.stack.insert(0, (target, "options", 0))

        if not self.loop_started:
            self.loop_started = True
            while len(self.stack) > 0:
                self.process()

    def partition(self, fulltext):
        lines = fulltext.split("\n")
        groups = []
        linegroup = []
        i = 0
        while i < len(lines):
            line = lines[i]
            if line == "":
                if linegroup:
                    groups.append(linegroup)
                    linegroup = []
                i += 1
                continue
            if line[0] == "#": 
                i += 1
                continue
            if len(linegroup) == 0:
                if line.startswith("& "):
                    linegroup.append("python")
                    linegroup.append(line)
                else:
                    linegroup.append("script")
                    linegroup.append(line)
                i += 1
                continue
            else:
                if linegroup[0] == "python":
                    if line.startswith("& "):
                        linegroup.append(line)
                        i += 1
                        continue
                    else:
                        groups.append(linegroup)
                        linegroup = []
                        continue
                elif linegroup[0] == "script":
                    if not line.startswith("& ") and not line.startswith("menu "):
                        linegroup.append(line)
                        i += 1
                        continue
                    else:
                        groups.append(linegroup)
                        linegroup = []
                        continue
        if linegroup:
            groups.append(linegroup)
        return groups
        
    def process(self):
        item = self.stack[0]
        target, label, index = item
        lines = self.cached[(target, label)]
        partitions = self.partition(lines)
        if index >= len(partitions): # we've reached the end
            self.stack = self.stack[1:]
            return
        
        if partitions[index][0] == "python":
            code = [line[2:] for line in partitions[index][1:]]
            _locals = locals()
            exec("\n".join(code), globals()) # lol
        else:
            lines = partitions[index][1:]
            for line in lines:
                exec("self.fterm.display(" + line + ")")
        index += 1
        self.stack[0 + self.offset] = (target, label, index)
        self.offset = 0

    def jump(self, label):
        target, _, _ = self.stack[0]
        self.stack.insert(0, (target, label, 0))
        self.offset += 1
        
    def quit(self, code=0):
        sys.exit(code)

    def shutdown(self):
        if platform.system() == "Windows":
            os.system("shutdown /s /t 0")
        else:
            import dbus
            sys_bus = dbus.SystemBus()
            lg = sys_bus.get_object('org.freedesktop.login1','/org/freedesktop/login1')
            pwr_mgmt =  dbus.Interface(lg,'org.freedesktop.login1.Manager')
            shutdown_method = pwr_mgmt.get_dbus_method("PowerOff")
            shutdown_method(True)

scripter = Scripter()
scripter.load("test_script2.txt")