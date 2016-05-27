import collections
import numpy

import astropy.units as u

from astromodels.sources.source import Source, POINT_SOURCE
from astromodels.sky_direction import SkyDirection
from astromodels.spectral_component import SpectralComponent
from astromodels.utils.pretty_list import dict_to_list
from astromodels.tree import Node
from astromodels.units import get_units


__author__ = 'giacomov'


class PointSource(Source, Node):
    """
    A point source. You can instance this class in many ways.

    - with Equatorial position and a function as spectrum (the component will be automatically called 'main')::

        >>> from astromodels import *
        >>> point_source = PointSource('my_source', 125.6, -75.3, Powerlaw())

    - with Galactic position and a function as spectrum (the component will be automatically called 'main')::

        >>> point_source = PointSource('my_source', l=15.67, b=80.75, spectral_shape=Powerlaw())

    - with Equatorial position or Galactic position and a list of spectral components::

        >>> c1 = SpectralComponent("component1", Powerlaw())
        >>> c2 = SpectralComponent("component2", Powerlaw())
        >>> point_source = PointSource("test_source",125.6, -75.3,components=[c1,c2])

        Or with Galactic position:

        >>> point_source = PointSource("test_source",l=15.67, b=80.75,components=[c1,c2])
    
    NOTE: by default the position of the source is fixed (i.e., its positional parameters are fixed)
    
    :param source_name: name for the source
    :param ra: Equatorial J2000 Right Ascension (ICRS)
    :param dec: Equatorial J2000 Declination (ICRS)
    :param spectral_shape: a 1d function representing the spectral shape of the source
    :param l: Galactic latitude
    :param b: Galactic longitude
    :param components: list of spectral components (instances of SpectralComponent)
    :param sky_position: an instance of SkyDirection
    :return:
    """

    def __init__(self, source_name, ra=None, dec=None, spectral_shape=None,
                 l=None, b=None, components=None, sky_position=None):

        # Check that we have all the required information

        # (the '^' operator acts as XOR on booleans)

        # Check that we have one and only one specification of the position

        assert ((ra is not None and dec is not None) ^
                (l is not None and b is not None) ^
                (sky_position is not None)), "You have to provide one and only one specification for the position"

        # Gather the position

        if not isinstance(sky_position, SkyDirection):

            if (ra is not None) and (dec is not None):

                # Check that ra and dec are actually numbers

                try:

                    ra = float(ra)
                    dec = float(dec)

                except (TypeError, ValueError):

                    raise AssertionError("RA and Dec must be numbers. If you are confused by this message, you "
                                         "are likely using the constructor in the wrong way. Check the documentation.")

                sky_position = SkyDirection(ra=ra, dec=dec)

            else:

                sky_position = SkyDirection(l=l, b=b)

        self._sky_position = sky_position

        # Fix the position by default

        self._sky_position.fix()

        # Now gather the component(s)

        # We need either a single component, or a list of components, but not both
        # (that's the ^ symbol)

        assert (spectral_shape is not None) ^ (components is not None), "You have to provide either a single " \
                                                                        "component, or a list of components " \
                                                                        "(but not both)."

        # If the user specified only one component, make a list of one element with a default name ("main")

        if spectral_shape is not None:

            components = [SpectralComponent("main", spectral_shape)]

        Source.__init__(self, components, POINT_SOURCE)

        # A source is also a Node in the tree

        Node.__init__(self, source_name)

        # Add the position as a child node, with an explicit name

        self._add_child(self._sky_position)

        # Add a node called 'spectrum'

        spectrum_node = Node('spectrum')
        spectrum_node._add_children(self._components.values())

        self._add_child(spectrum_node)

        # Now set the units
        # Now sets the units of the parameters for the energy domain

        current_units = get_units()

        # Components in this case have energy as x and differential flux as y

        x_unit = current_units.energy
        y_unit = (current_units.energy * current_units.area * current_units.time) ** (-1)

        # Now set the units of the components
        for component in self._components.values():

            component.shape.set_units(x_unit, y_unit)

    def __call__(self, x):

        results = [component.shape(x) for component in self.components.values()]

        if isinstance(x, u.Quantity):

            # Slow version with units

            # We need to sum like this (slower) because using np.sum will not preserve the units
            # (thanks astropy.units)

            return sum(results)

        else:

            # Fast version without units, where x is supposed to be in the same units as currently defined in
            # units.get_units()

            return numpy.sum(results, 0)

    def _repr__base(self, rich_output=False):
        """
        Representation of the object

        :param rich_output: if True, generates HTML, otherwise text
        :return: the representation
        """

        # Make a dictionary which will then be transformed in a list

        repr_dict = collections.OrderedDict()

        key = '%s (point source)' % self.name

        repr_dict[key] = collections.OrderedDict()
        repr_dict[key]['position'] = self._sky_position.to_dict(minimal=True)
        repr_dict[key]['spectrum'] = collections.OrderedDict()

        for component_name, component in self.components.iteritems():

            repr_dict[key]['spectrum'][component_name] = component.to_dict(minimal=True)

        return dict_to_list(repr_dict, rich_output)

