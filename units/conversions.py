# -*- coding: utf-8 -*-
from numpy import pi
import re

from constants import *

#{ Main functions

def convert(_from,_to,*args,**kwargs):
    """
    Convert one unit to another.
    
    Keyword arguments can give extra information, for example when converting
    from Flambda to Fnu, and should be tuples (float,'unit').
    
    The unit strings should by default be given in the form
    
    C{erg s-1 cm-2 A-1}
    
    Common alternatives are also accepted, but don't drive this to far:
    
    C{erg/s/cm2/A}
    
    The crasiest you're allowed to go is
    
    >>> print(convert('10mW m-2 nm-1','erg s-1 cm-2 A-1',1.))
    1.0
    
    Parentheses are in no circumstances accepted. Some common aliases are also
    resolved (for a full list, see dictionary C{_aliases}):
    
    C{erg/s/cm2/angstrom}
    
    Examples:
    
    B{Spectra}:
    
    >>> convert('km','cm',1.)
    100000.0
    >>> convert('A','km/s',4553.,wave=(4552.,'A'))
    65.859503075576129
    >>> convert('nm','m/s',455.3,wave=(0.4552,'mum'))
    65859.503075645873
    >>> convert('km/s','A',65.859503075576129,wave=(4552.,'A'))
    4553.0
    >>> convert('nm','Ghz',1000.)
    299792.45799999993
    >>> convert('km h-1','nRsun s-1',1.)
    0.39939292275740873
    >>> convert('erg s-1 cm-2 A-1','SI',1.)
    10000000.0
    
    B{Fluxes}:
    
    >>> convert('erg/s/cm2/A','Jy',1e-10,wave=(10000.,'angstrom'))
    333.56409519815202
    >>> convert('erg/s/cm2/A','Jy',1e-10,freq=(cc/1e-6,'hz'))
    333.56409519815202
    >>> convert('erg/s/cm2/A','Jy',1e-10,freq=(cc,'Mhz'))
    333.56409519815202
    >>> convert('Jy','erg/s/cm2/A',333.56409519815202,wave=(10000.,'A'))
    1e-10
    >>> convert('Jy','erg/s/cm2/A',333.56409519815202,freq=(cc,'Mhz'))
    1e-10
    >>> convert('W/m2/mum','erg/s/cm2/A',1e-10,wave=(10000.,'A'))
    1.0000000000000001e-11
    >>> convert('Jy','W/m2/Hz',1.)
    1e-26
    >>> print convert('W/m2/Hz','Jy',1.)
    1e+26
    >>> print convert('Jy','erg/cm2/s/Hz',1.)
    1e-23
    >>> print convert('erg/cm2/s/Hz','Jy',1.)
    1e+23
    >>> convert('Jy','erg/s/cm2',1.,wave=(2.,'micron'))
    1.49896229e-09
    >>> convert('erg/s/cm2','Jy',1.,wave=(2.,'micron'))
    667128190.39630413
    >>> convert('Jy','erg/s/cm2/micron/sr',1.,wave=(2.,'micron'),diam=(3.,'mas'))
    4511059.8298101583
    >>> convert('erg/s/cm2/micron/sr','Jy',1.,wave=(2.,'micron'),diam=(3.,'mas'))
    2.2167739682629828e-07
    >>> convert('Jy','erg/s/cm2/micron',1.,wave=(2,'micron'))
    7.4948114500000012e-10
    >>> print(convert('10mW m-2 nm-1','erg s-1 cm-2 A-1',1.))
    1.0
    
    B{Frequency analysis}:
    
    >>> convert('cy/d','muHz',1.)
    11.574074074074074
    >>> convert('muhz','cy/d',11.574074074074074)
    1.0
    
    B{Interferometry}:
    
    >>> convert('m','cy/arcsec',85.,wave=(2.2,'micron'))
    187.3143767923207
    >>> convert('cm','cy/arcmin',8500.,wave=(2200,'nm'))/60.
    187.31437679232073
    >>> convert('cy/arcsec','m',187.,wave=(2.2,'mum'))
    84.857341290055444
    >>> convert('cyc/arcsec','m',187.,wave=(1,'mum'))
    38.571518768207014
    >>> convert('cycles/arcsec','m',187.,freq=(300000.,'Ghz'))
    38.54483473437972
    >>> convert('cycles/mas','m',0.187,freq=(300000.,'Ghz'))
    38.544834734379712
    
    @param from_units: units to convert from
    @param to_units: units to convert to
    @return: converted value
    @rtype: float
    """
    #-- break down the from and to units to their basic elements
    fac_from,uni_from = breakdown(_from)
    if _to!='SI':
        fac_to,uni_to = breakdown(_to)
    else:
        fac_to,uni_to = 1.,uni_from
    
    #-- convert the kwargs to SI units
    kwargs_SI = {}
    for key in kwargs:
        fac_key,uni_key = breakdown(kwargs[key][1])
        kwargs_SI[key] = fac_key*kwargs[key][0]
    
    #-- easy if same units
    if uni_from==uni_to:
        #-- if nonlinear conversions from or to:
        if isinstance(fac_from,NonLinearConverter):
            return fac_from(args[0])/fac_to
        elif isinstance(fac_to,NonLinearConverter):
            return fac_to(fac_from*args[0],inv=True)
        #-- otherwise
        else:
            return fac_from * args[0] / fac_to
    else:
        uni_from_ = uni_from.split()
        uni_to_ = uni_to.split()
        only_from = "".join(sorted(list(set(uni_from_) - set(uni_to_))))
        only_to = "".join(sorted(list(set(uni_to_) - set(uni_from_))))
        
        if only_to[-4:]=='sr-1':
            args = _switch['_to_sr-1'](args[0],**kwargs_SI),
            only_to = only_to[:-4]
        if only_from[-4:]=='sr-1':
            args = _switch['sr-1_to_'](args[0],**kwargs_SI),
            only_from = only_from[:-4]
        
        return _switch['%s_to_%s'%(only_from,only_to)](fac_from*args[0],**kwargs_SI)/fac_to

#}
#{ Conversions basics
def solve_aliases(unit):
    """
    Resolve simple aliases in a unit's name.
    
    Resolves aliases and replaces division signs with negative power.
    
    @param unit: unit (e.g. erg s-1 angstrom-1)
    @type unit: str
    @return: aliases-resolved unit (e.g. erg s-1 A-1)
    @rtype: str
    """
    #-- resolve aliases
    for alias in _aliases:
        unit = unit.replace(alias[0],alias[1])
    
    #-- replace slash-forward with negative powers
    if '/' in unit:
        unit_ = [uni.split('/') for uni in unit.split()]
        for i,uni in enumerate(unit_):
            for j,after_div in enumerate(uni[1:]):
                if not after_div[-1].isdigit(): after_div += '1'
                m = re.search(r'(\d*)(.+?)(-{0,1}\d+)',after_div)
                if m is not None:
                    factor,basis,power = m.group(1),m.group(2),int(m.group(3))
                    if factor: factor = float(factor)
                    else: factor = 1.
                else:
                    factor,basis,power = 1.,after_div,1
                uni[1+j] = '%s%d'%(basis,-power)
                if factor!=1: uni[1+j] = '%d%s'%(factor,uni[1+j])
        ravelled = []
        for uni in unit_:
            ravelled += uni
        unit = " ".join(ravelled)
    return unit
    

def components(unit):
    """
    Decompose a unit into: a factor, SI base unit, power.
    
    Examples:
    
    >>> print(components('m'))
    (1.0, 'm', 1)
    >>> print(components('g2'))
    (0.001, 'kg', 2)
    >>> print(components('hg3'))
    (0.10000000000000001, 'kg', 3)
    >>> print(components('Mg4'))
    (1000.0, 'kg', 4)
    >>> print(components('mm'))
    (0.001, 'm', 1)
    >>> print(components('W3'))
    (1.0, 'kg m2 s-3', 3)
    >>> print(components('s-2'))
    (1.0, 's', -2)
    
    @param unit: unit name
    @type unit: str
    @return: 3-tuple with factor, SI base unit and power
    @rtype: (float,str,int)
    """
    if not unit[-1].isdigit(): unit += '1'
    #-- decompose unit in base name and power
    m = re.search(r'(\d*)(.+?)(-{0,1}\d+)',unit)
    if m is not None:
        factor,basis,power = m.group(1),m.group(2),int(m.group(3))
        if factor: factor = float(factor)
        else: factor = 1.
    else:
        factor,basis,power = 1.,unit,1
    #-- decompose the base name (which can be a composition of a prefix
    #   (e.g., 'mu') and a unit name (e.g. 'm')) into prefix and unit name
    #-- check if basis is part of _factors dictionary. If not, find the
    #   combination of _scalings and basis which is inside the dictionary!
    for scale in _scalings:
        scale_unit,base_unit = basis[:len(scale)],basis[len(scale):]
        if scale_unit==scale and base_unit in _factors:
            factor *= _scalings[scale]
            basis = base_unit
            break
    #-- if we didn't find any scalings, check if the 'raw' unit is already
    #   a base unit
    else:
        if not basis in _factors:
            raise ValueError, 'Unknown unit %s'%(basis)
        
    #-- switch from base units to SI units
    if hasattr(_factors[basis][0],'__call__'):
        factor = factor*_factors[basis][0]()
    else:
        factor *= _factors[basis][0]
    basis = _factors[basis][1]
    
    return factor,basis,power

def breakdown(unit):
    """
    Decompose a unit into SI base units containing powers.
    
    Examples:
    
    >>> print(breakdown('erg s-1 W2 kg2 cm-2'))
    (0.001, 'kg5 m4 s-9')
    >>> print(breakdown('erg s-1 cm-2 A-1'))
    (10000000.0, 'kg1 m-1 s-3')
    >>> print(breakdown('W m-3'))
    (1.0, 'kg1 m-1 s-3')
    
    @param unit: unit's name
    @type unit: str
    @return: 2-tuple factor, unit's base name
    @rtype: (float,str)
    """
    #-- solve aliases
    unit = solve_aliases(unit)
    #-- break down in basic units
    units = unit.split()
    total_factor = 1.
    total_units = []
    total_power = []
    for unit in units:
        factor,basis,power = components(unit)
        
        total_factor = total_factor*factor**power
        basis = basis.split()
        for base in basis:
            factor_,basis_,power_ = components(base)
            if basis_ in total_units:
                index = total_units.index(basis_)
                total_power[index] += power_*power
            else:
                total_units.append(basis_)
                total_power.append(power_*power)
    
    #-- make sure to return a sorted version
    total_units = sorted(['%s%s'%(i,j) for i,j in zip(total_units,total_power) if j!=0])
    
    return total_factor," ".join(total_units)

#}
#{ Linear change-of-base conversions
        
def distance2velocity(arg,**kwargs):
    """
    Switch from distance to velocity via a reference wavelength.
    
    @param arg: distance (SI, m)
    @type arg: float
    @keyword wave: reference wavelength (SI, m)
    @type wave: float
    @return: velocity (SI, m/s)
    @rtype: float
    """
    if 'wave' in kwargs:
        wave = kwargs['wave']
        velocity = (arg-wave) / wave * cc
    else:
        raise ValueError,'reference wavelength (wave) not given'
    return velocity

def velocity2distance(arg,**kwargs):
    """
    Switch from velocity to distance via a reference wavelength.
    
    @param arg: velocity (SI, m/s)
    @type arg: float
    @keyword wave: reference wavelength (SI, m)
    @type wave: float
    @return: distance (SI, m)
    @rtype: float
    """
    if 'wave' in kwargs:
        wave = kwargs['wave']
        distance = wave / cc * arg + wave
    else:
        raise ValueError,'reference wavelength (wave) not given'
    return distance

def fnu2flambda(arg,**kwargs):
    """
    Switch from Fnu to Flambda via a reference wavelength.
    
    Flambda and Fnu are spectral irradiance in wavelength and frequency,
    respectively
    
    @param arg: spectral irradiance (SI,W/m2/Hz)
    @type arg: float
    @keyword wave: reference wavelength (SI, m)
    @type wave: float
    @keyword freq: reference frequency (SI, Hz)
    @type freq: float
    @return: spectral irradiance (SI, W/m2/m)
    @rtype: float
    """
    if 'wave' in kwargs:
        wave = kwargs['wave']
        flambda = cc/wave**2 * arg
    elif 'freq' in kwargs:
        freq = kwargs['freq']
        flambda = freq**2/cc * arg
    else:
        raise ValueError,'reference wave/freq not given'
    return flambda

def flambda2fnu(arg,**kwargs):
    """
    Switch from Flambda to Fnu via a reference wavelength.
    
    Flambda and Fnu are spectral irradiance in wavelength and frequency,
    respectively
    
    @param arg: spectral irradiance (SI, W/m2/m)
    @type arg: float
    @keyword wave: reference wavelength (SI, m)
    @type wave: float
    @keyword freq: reference frequency (SI, Hz)
    @type freq: float
    @return: spectral irradiance (SI,W/m2/Hz)
    @rtype: float
    """
    if 'wave' in kwargs:
        wave = kwargs['wave']
        fnu = wave**2/cc * arg
    elif 'freq' in kwargs:
        freq = kwargs['freq']
        fnu = cc/freq**2 * arg
    else:
        raise ValueError,'reference wave/freq not given'
    return fnu

def fnu2nufnu(arg,**kwargs):
    """
    Switch from Fnu to nuFnu via a reference wavelength.
    
    Flambda and Fnu are spectral irradiance in wavelength and frequency,
    respectively
    
    @param arg: spectral irradiance (SI,W/m2/Hz)
    @type arg: float
    @keyword wave: reference wavelength (SI, m)
    @type wave: float
    @keyword freq: reference frequency (SI, Hz)
    @type freq: float
    @return: spectral irradiance (SI, W/m2/m)
    @rtype: float
    """
    if 'wave' in kwargs:
        wave = kwargs['wave']
        fnu = cc/wave * arg
    elif 'freq' in kwargs:
        freq = kwargs['freq']
        fnu = freq/cc * arg
    else:
        raise ValueError,'reference wave/freq not given'
    return fnu

def nufnu2fnu(arg,**kwargs):
    """
    Switch from nuFnu to Fnu via a reference wavelength.
    
    Flambda and Fnu are spectral irradiance in wavelength and frequency,
    respectively
    
    @param arg: spectral irradiance (SI,W/m2/Hz)
    @type arg: float
    @keyword wave: reference wavelength (SI, m)
    @type wave: float
    @keyword freq: reference frequency (SI, Hz)
    @type freq: float
    @return: spectral irradiance (SI, W/m2/m)
    @rtype: float
    """
    if 'wave' in kwargs:
        wave = kwargs['wave']
        fnu = wave/cc * arg
    elif 'freq' in kwargs:
        freq = kwargs['freq']
        fnu = cc/freq * arg
    else:
        raise ValueError,'reference wave/freq not given'
    return fnu

def distance2frequency(arg,**kwargs):
    """
    Switch from distance to frequency via the speed of light, or vice versa.
    
    @param arg: distance (SI, m)
    @type arg: float
    @return: frequency (SI, Hz)
    @rtype: float
    """
    return cc/arg

def distance2spatialfreq(arg,**kwargs):
    """
    Switch from distance to spatial frequency via a reference wavelength.
    
    @param arg: distance (SI, m)
    @type arg: float
    @keyword wave: reference wavelength (SI, m)
    @type wave: float
    @keyword freq: reference frequency (SI, Hz)
    @type freq: float
    @return: spatial frequency (SI, cy/as)
    @rtype: float
    """
    if 'wave' in kwargs:
        spatfreq = 2*pi*arg/kwargs['wave']
    elif 'freq' in kwargs:
        spatfreq = 2*pi*arg*cc*kwargs['freq']
    else:
        raise ValueError,'reference wave/freq not given'
    return spatfreq

def spatialfreq2distance(arg,**kwargs):
    """
    Switch from spatial frequency to distance via a reference wavelength.
    
    @param arg: spatial frequency (SI, cy/as)
    @type arg: float
    @keyword wave: reference wavelength (SI, m)
    @type wave: float
    @keyword freq: reference frequency (SI, Hz)
    @type freq: float
    @return: distance (SI, m)
    @rtype: float
    """
    if 'wave' in kwargs:
        distance = kwargs['wave']*arg/(2*pi)
    elif 'freq' in kwargs:
        distance = cc/kwargs['freq']*arg/(2*pi)
    else:
        raise ValueError,'reference wave/freq not given'
    return distance

def per_sr(arg,**kwargs):
    """
    Switch from [Q] to [Q]/sr
    
    @param arg: some SI unit
    @type arg: float
    @return: some SI unit per steradian
    @rtype: float
    """
    if 'diam' in kwargs:
        radius = kwargs['diam']/2.
    elif 'radius' in kwargs:
        radius = kwargs['radius']
    else:
        raise ValueError,'angular size (diam/radius) not given'
    Qsr = arg/(pi*(2*pi*radius)**2)
    return Qsr

def times_sr(arg,**kwargs):
    """
    Switch from [Q]/sr to [Q]
    
    @param arg: some SI unit per steradian
    @type arg: float
    @return: some SI unit
    @rtype: float
    """
    if 'diam' in kwargs:
        radius = kwargs['diam']/2.
    elif 'radius' in kwargs:
        radius = kwargs['radius']
    else:
        raise ValueError,'angular size (diam/radius) not given'
    Q = arg*(pi*(2*pi*radius)**2)
    return Q
#}

#{ Nonlinear change-of-base functions


class NonLinearConverter():
    def __init__(self,prefix=1.,power=1.):
        self.prefix = prefix
        self.power = power
    def __rmul__(self,other):
        if type(other)==type(5) or type(other)==type(5.):
            return self.__class__(prefix=self.prefix*other)
    def __div__(self,other):
        if type(other)==type(5) or type(other)==type(5.):
            return self.__class__(prefix=self.prefix*other)
    def __pow__(self,other):
        if type(other)==type(5) or type(other)==type(5.):
            return self.__class__(prefix=self.prefix,power=self.power+other)

class Fahrenheit(NonLinearConverter):
    def __call__(self,a,inv=False):
        if not inv:
            return (a*self.prefix+459.67)*5./9.
        else:
            return (a*9./5.-459.67)/self.prefix

class Celcius(NonLinearConverter):
    def __call__(self,a,inv=False):
        if not inv:
            return a*self.prefix-273.15
        else:
            return (a+273.15)/self.prefix

class VegaMag(NonLinearConverter):
    def __call__(self,meas,photband=None,inv=False):
        #-- this part should include something where the zero-flux is retrieved
        F0 = 1e-09
        if not inv:
            return 10**(-meas/2.5)*F0
        else:
            return -2.5*log10(meas/F0)

class ABMag(NonLinearConverter):
    def __call__(self,meas,photband=None,inv=False):
        F0 = 3.6307805477010024e-23
        if not inv:
            return 10**(-meas/2.5)*F0
        else:
            return -2.5*log10(meas/F0)

class STMag(NonLinearConverter):
    def __call__(self,meas,photband=None,inv=False):
        F0 = 0.036307805477010027
        if not inv:
            return 10**(-meas/-2.5)*F0
        else:
            return -2.5*log10(meas/F0)


#-- basic units which the converter should know about
_factors = {
# DISTANCE
           'm':     (  1e+00,       'm'),
           'A':     (  1e-10,       'm'),
           'AU':    (au,            'm'),
           'pc':    (pc,            'm'),
           'ly':    (ly,            'm'),
           'Rsun':  (Rsun,          'm'),
# MASS
           'g':     (  1e-03,       'kg'),
           'Msun':  (Msun,          'kg'),
# TIME
           's':     (  1e+00,       's'),
           'min':   (  60.,         's'),
           'h':     (3600.,         's'),
           'd':     (24*3600.,      's'),
           'yr':    (365*24*3600.,  's'),
           'cr':    (100*365*24*3600,'s'),
           'hz':    (1e+00,         'cy s-1'),
# ANGLES
           'rad':         (0.15915494309189535, 'cy'),
           'cy':          (1e+00,               'cy'),
           'deg':         (1./360.,             'cy'),
           'am':      (1./360./60.,         'cy'),
           'as':          (1./360./3600.,       'cy'),
           'sr':          (1e+00,                'sr'),
# FORCE
           'N':     (1e+00,         'kg m s-2'),
           'dy':    (1e-05,         'kg m s-2'),
# TEMPERATURE
           'K':      (1e+00,        'K'),
           'F':      (Fahrenheit,   'K'),
           'C':      (Celcius,      'K'),
# ENERGY & POWER
           'J':     (  1e+00,       'kg m2 s-2'),
           'W':     (  1e+00,       'kg m2 s-3'),
           'erg':   (  1e-07,       'kg m2 s-2'),
           'eV':    (1.60217646e-19,'kg m2 s-2'),
           'cal':   (4.184,         'kg m2 s-2'),
# FLUX
           'Jy':      (1e-26,         'kg s-2 cy-1'),
           'vegamag': (VegaMag,       'kg m-1 s-3'),  # in W/m2/m
           'STmag':   (STMag,         'kg m-1 s-3'),  # in W/m2/m
           'ABmag':   (ABMag,         'kg s-2 cy-1'), # in W/m2/Hz
           }
            
#-- scaling factors for prefixes            
_scalings = {
            'n':       1e-09,
            'mu':      1e-06,
            'm':       1e-03,
            'c':       1e-02,
            'd':       1e-01,
            'da':      1e+01,
            'h':       1e+02,
            'k':       1e+03,
            'M':       1e+06,
            'G':       1e+09}
 
#-- some common aliases
_aliases = [('micron','mum'),
            ('micro','mu'),
            ('milli','m'),
            ('kilo','k'),
            ('mega','M'),
            ('giga','G'),
            ('nano','n'),
            ('watt','W'),
            ('Watt','W'),
            ('Hz','hz'),
            ('joule','J'),
            ('Joule','J'),
            ('jansky','Jy'),
            ('Jansky','Jy'),
            ('arcsec','as'),
            ('arcmin','am'),
            ('cycles','cy'),
            ('cycle','cy'),
            ('cyc','cy'),
            ('angstrom','A'),
            ('Angstrom','A'),
            (' mag',' vegamag'), # with space! otherwise confusion with ST/AB mag
            ('/mag',' /vegamag'),# with space! otherwise confusion with ST/AB mag
            ('^',''),
            ('**','')
            ]
 
#-- Change-of-base function definitions
_switch = {'_to_s-1':distance2velocity, # switch from wavelength to velocity
           's-1_to_':velocity2distance, # switch from wavelength to velocity
           'm1_to_cy1s-1':distance2frequency,  # switch from wavelength to frequency
           'cy1s-1_to_m1':distance2frequency,  # switch from frequency to wavelength
           'm1_to_':distance2spatialfreq, # for interferometry
           '_to_m1':spatialfreq2distance, # for interferometry
           'cy-1s-2_to_m-1s-3':fnu2flambda,
           'm-1s-3_to_cy-1s-2':flambda2fnu,
           'cy-1s-2_to_s-3':fnu2nufnu,
           's-3_to_cy-1s-2':nufnu2fnu,
           '_to_sr-1':per_sr,
           'sr-1_to_':times_sr} 
 
 
if __name__=="__main__":
    import doctest
    doctest.testmod()
    print convert('F','K',1000.)
    print convert('kF','K',1.)
    print convert('K','F',1000.)
    print convert('kK','F',1000.)
    
    print "Celcius"
    print convert('C','K',0.)
    print convert('C','SI',0.)
    print convert('K','C',0.)
    
    
    print "Magnitudes"
    print convert('vegamag','SI',0.)
    print convert('ABmag','Jy',0.)
    print convert('STmag','erg cm-2 s-1 A-1',0.)