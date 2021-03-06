import os
import xml.etree.ElementTree as ET

class Point(dict):
    
    '''
    Keeps track of shaking data associated with a location. A list of
    these is made in the ShakeMapGrid class and can be sorted by a metric
    using the ShakeMapGrid.sort_by method
    '''
    
    sort_by = ''

    def __cmp__(self, other):
        if int(self[self.sort_by] * 10000) > int(other[self.sort_by] * 10000):
            return 1
        elif int(self[self.sort_by] * 10000) < int(other[self.sort_by] * 10000):
            return -1
        else:
            return 0


class ShakeMapGrid(object):
    
    '''
    Object that reads a grid.xml file and compares shaking data with
    input from user data
    '''
    
    def __init__(self,
                 lon_min = 0,
                 lon_max = 0,
                 lat_min = 0,
                 lat_max = 0,
                 nom_lon_spacing = 0,
                 nom_lat_spacing = 0,
                 num_lon = 0,
                 num_lat = 0,
                 event_id = '',
                 magnitude = 0,
                 depth = 0,
                 lat = 0,
                 lon = 0,
                 description = '',
                 directory_name = '',
                 xml_file = ''):
        
        self.lon_min = lon_min
        self.lon_max = lon_max
        self.lat_min = lat_min
        self.lat_max = lat_max
        self.nom_lon_spacing = nom_lon_spacing
        self.nom_lat_spacing = nom_lat_spacing
        self.num_lon = num_lon
        self.num_lat = num_lat
        self.event_id = event_id
        self.magnitude = magnitude
        self.depth = depth
        self.lat = lat
        self.lon = lon
        self.description = description
        self.directory_name = directory_name
        self.xml_file = xml_file
        self.tree = None
        self.fields = []
        self.grid = []
        
        self.points = []
    
    def load(self, file_ = ''):
        """
        Loads data from a specified grid.xml file into the object
        """
        self.tree = ET.parse(file_)
        root = self.tree.getroot()
        
        # set the ShakeMapGrid's attributes
        all_atts = {}
        for child in root:
            all_atts.update(child.attrib)
        
        self.lat_min = float(all_atts.get('lat_min'))
        self.lat_max = float(all_atts.get('lat_max'))
        self.lon_min = float(all_atts.get('lon_min'))
        self.lon_max = float(all_atts.get('lon_max'))
        self.nom_lon_spacing = float(all_atts.get('nominal_lon_spacing'))
        self.nom_lat_spacing = float(all_atts.get('nominal_lat_spacing'))
        self.num_lon = int(all_atts.get('nlon'))
        self.num_lat = int(all_atts.get('nlat'))
        self.event_id = all_atts.get('event_id')
        self.magnitude = float(all_atts.get('magnitude'))
        self.depth = float(all_atts.get('depth'))
        self.lat = float(all_atts.get('lat'))
        self.lon = float(all_atts.get('lon'))
        self.description = all_atts.get('event_description')
        
        self.sorted_by = ''
        
        self.fields = [child.attrib['name']
                        for child in root
                        if 'grid_field' in child.tag]
        
        grid_str = [child.text
                    for child in root
                    if 'grid_data' in child.tag][0]
        
        #get rid of trailing and leading white space
        grid_str = grid_str.lstrip().rstrip()
        
        # break into point strings
        grid_lst = grid_str.split('\n')
        
        # split points and save them as Point objects
        for point_str in grid_lst:
            point_str = point_str.lstrip().rstrip()
            point_lst = point_str.split(' ')
        
            point = Point()
            for count, field in enumerate(self.fields):
                point[field] = float(point_lst[count])
                    
            self.grid += [point]
        
    def sort_grid(self, metric= ''):
        """
        Sorts the grid by a specified metric
        """
        Point.sort_by = metric
        self.grid = sorted(self.grid)
        self.sorted_by = metric
        return True
    
    def in_grid(self, facility=None, lon_min=0, lon_max=0, lat_min=0, lat_max=0):
        """
        Check if a point is within the boundaries of the grid
        """
        if facility is not None:
            lon_min = facility.lon_min
            lon_max = facility.lon_max
            lat_min = facility.lat_min
            lat_max = facility.lat_max

        return ((lon_min > self.lon_min and
                    lon_min < self.lon_max and
                    lat_min > self.lat_min and
                    lat_min < self.lat_max) or
                (lon_min > self.lon_min and
                    lon_min < self.lon_max and
                    lat_max > self.lat_min and
                    lat_max < self.lat_max) or
                (lon_max > self.lon_min and
                    lon_max < self.lon_max and
                    lat_min > self.lat_min and
                    lat_min < self.lat_max) or
                (lon_max > self.lon_min and
                    lon_max < self.lon_max and
                    lat_max > self.lat_min and
                    lat_max < self.lat_max))
    
    def max_shaking(self,
                    lon_min=0,
                    lon_max=0,
                    lat_min=0,
                    lat_max=0,
                    metric=None,
                    facility=None):
        
        '''
        Will return a float with the largest shaking in a specified
        region. If no grid points are found within the region, the
        region is made larger until a point is present
        
        Returns:
            int: -1 if max shaking can't be determined, otherwise shaking level
        '''
    
        if facility is not None:
            try:
                lon_min = facility.lon_min
                lon_max = facility.lon_max
                lat_min = facility.lat_min
                lat_max = facility.lat_max
                metric = facility.metric
            except:
                return -1
            
        if not self.grid:
            return None

        # check if the facility lies in the grid
        if not facility.in_grid(self):
            return {facility.metric: 0}
        
        # check if the facility's metric exists in the grid
        if not self.grid[0].get(facility.metric, None):
            return {facility.metric: None}
        
        # sort the grid in an attempt to speed up processing on
        # many facilities
        if self.sorted_by != 'LON':
            self.sort_grid('LON')
        
        # figure out where in the point list we should look for shaking
        in_each = len(self.grid) / self.num_lon
        start = int((lon_min - self.grid[0]['LON']) / self.nom_lon_spacing * in_each)
        end = int((lon_max - self.grid[0]['LON']) / self.nom_lon_spacing * in_each)
        if start < 0:
            start = 0
        
        shaking = []
        while not shaking:
            shaking = [point for point in self.grid[start:end] if
                                        (point['LAT'] > lat_min and
                                         point['LAT'] < lat_max)]
            
            # make the rectangle we're searching in larger to encompass
            # more points
            lon_min -= .01
            lon_max += .01
            lat_min -= .01
            lat_max += .01
            start -= 1
        
        Point.sort_by = metric
        shaking = sorted(shaking)
        return shaking[-1]


def create_grid(shakemap=None):
    """
    Creates a grid object from a specific ShakeMap
    
    Args:
        shakemap (ShakeMap): A ShakeMap with a grid.xml to laod
    
    Returns:
        ShakeMapGrid: With loaded grid.xml
    """
    grid = ShakeMapGrid()
    grid_location = os.path.join(shakemap.directory_name, 'grid.xml')
    grid.load(grid_location)
    
    return grid