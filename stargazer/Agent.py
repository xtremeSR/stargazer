#! python

'''
    File: Agent.py
    Description: Agent abstract class representing a pokemon Showdown agent.
'''
import abc

class Agent:
    def __init__(self):
        __metaclass__ = abc.ABCMeta
        pass

    def __str__(self):
        pass

    def __repr__(self):
        pass

    @abc.abstractmethod
    def move(self):
        pass

    @abc.abstractmethod
    def switch(self):
        pass
