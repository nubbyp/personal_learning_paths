import numpy as np

shape = (1,)*21

def featurize(state):
    return np.concatenate(([state['sel']], state['vals']))


