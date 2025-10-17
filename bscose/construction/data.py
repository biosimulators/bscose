
"""

How to break down types?

quantity [units] of Classification<category_subtype> ?

1.5 Mol of Species<Ag2+>
25 m/s of Velocity
[3, 0, 4] m/s2 of Acceleration
500 s of Time
"""
#TODO: Add "unit-system" class

class Unit:
    def __str__(self):
        return f"[{self.__class__.__name__}]"

class NoneUnit(Unit):
    pass

class Classification:
    def get_default_unit(self):
        raise NotImplementedError("This has not been implemented yet.")

    def __str__(self):
        return f"|{self.__class__.__name__}|"

class NoneClassification(Classification):
    pass

class Length(Classification):
    pass

class Mass(Classification):
    pass

class Time(Classification):
    pass

class ElectricalCurrent(Classification):
    pass

class Temperature(Classification):
    pass

class SubstanceAmount(Classification):
    pass

class LuminousIntensity(Classification):
    pass

class Quantity(Classification):
    pass


class Type:
    def __init__(self, clsf: type[Classification] = NoneClassification, unit: type[Unit] = NoneUnit):
        self._clsf = clsf() # construct a default classification
        self._unit = unit() # construct a default unit

    def get_default_value(self):
        raise NotImplementedError("This has not been implemented yet.")

    def __str__(self):
        return f'{str(self._unit)} of `{str(self._clsf)}`'

    def __eq__(self, other):
        if not isinstance(other, Type):
            return False
        return str(self) == str(other)