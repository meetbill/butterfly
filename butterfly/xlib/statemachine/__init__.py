# coding=utf8
"""
# File Name: statemachine
# Description:

+--------------------------------------------
|from statemachine import StateMachine, State
|
|class TrafficLightMachine(StateMachine):
|    green = State('Green', initial=True)
|    yellow = State('Yellow')
|    red = State('Red')
|
|    slowdown = green.to(yellow)
|    stop = yellow.to(red)
|    go = red.to(green)
|
|
|traffic_light = TrafficLightMachine()
+--------------------------------------------

> traffic_light.states
```
[
    State('Green', identifier='green', value='green', initial=True),
    State('Red', identifier='red', value='red', initial=False),
    State('Yellow', identifier='yellow', value='yellow', initial=False)
]
```
> traffic_light.transitions
```
[
    Transition(
        State('Red', identifier='red', value='red', initial=False),
        (State('Green', identifier='green', value='green', initial=True),),
        identifier='go'
        ),
    Transition(
        State('Green', identifier='green', value='green', initial=True),
        (State('Yellow', identifier='yellow', value='yellow', initial=False),),
        identifier='slowdown'
        ),
    Transition(
        State('Yellow', identifier='yellow', value='yellow', initial=False),
        (State('Red', identifier='red', value='red', initial=False),),
        identifier='stop'
        )
]
```
> traffic_light.states_map
```
{
    'green': State('Green', identifier='green', value='green', initial=True),
    'yellow': State('Yellow', identifier='yellow', value='yellow', initial=False),
    'red': State('Red', identifier='red', value='red', initial=False)
}
```
"""
# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import
from .statemachine import StateMachine, State, Transition

__author__ = """Fernando Macedo"""
__email__ = 'fgmacedo@gmail.com'
__version__ = '0.8.0'

__all__ = ['StateMachine', 'State', 'Transition']
