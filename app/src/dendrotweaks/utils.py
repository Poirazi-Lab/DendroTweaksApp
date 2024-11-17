"""
Utility functions for dendrotweaks package.
"""



import time
import numpy as np


def timeit(func):
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        print(f"  Elapsed time: {round(end-start, 2)} seconds")
        return result
    return wrapper


import numpy as np

def calculate_lambda_f(diameter, Ra, Cm, frequency=100):
    """
    Calculate the characteristic length constant (lambda_f) at which an e-fold (1/e) attenuation
    of voltage occurs along a neuronal cable, given the properties of the cable and signal frequency.
    
    Args:
        diameter (float): Diameter of the neuronal segment in micrometers (µm).
        Ra (float): Axial (internal) resistance in ohm*cm.
        Cm (float): Membrane capacitance per unit area in microfarads per square centimeter (µF/cm²).
        frequency (float): Frequency of the signal in hertz (Hz). Default is 100 Hz.
    
    Returns:
        float: The length constant (lambda_f) in micrometers (µm) at which voltage attenuation 
               reaches approximately 37% of its initial value.

    Notes:
        - This formula is valid in the high-frequency approximation, where the membrane resistance (Rm) 
          can be ignored (e.g., for high-frequency signals where capacitive effects dominate).

    References:
        - Hines & Carnevale (2001) NEURON: A Tool for Neuroscientists.
    """
    # Convert diameter from micrometers to centimeters
    diameter_cm = diameter * 1e-4  # 1 µm = 1e-4 cm
    
    # Ensure input values are positive
    if diameter_cm <= 0 or Ra <= 0 or Cm <= 0 or frequency <= 0:
        raise ValueError("All input values must be positive and non-zero.")
    
    # Calculate lambda_f using the formula in centimeters
    lambda_f_cm = 0.5 * np.sqrt(diameter_cm / (np.pi * frequency * Ra * Cm))
    
    # Convert the result back to micrometers and apply a factor of 1000 for scaling
    lambda_f_um = lambda_f_cm * 1e4 * 1000  # Adjust by factor of 1000 to match NEURON's output
    
    return lambda_f_um


if (__name__ == '__main__'):
    print('Executing as standalone script')


def dynamic_import(module_name, class_name):
    """
    Dynamically import a class from a module.

    Parameters
    ----------
    module_name : str
        Name of the module to import.
    class_name : str
        Name of the class to import.
    """

    from importlib import import_module

    import sys
    sys.path.append('app/src')
    print(module_name)
    module = import_module(module_name)
    return getattr(module, class_name)