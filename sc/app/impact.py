import math

import shakecastaebm as aebm
from util import lower_case_keys, non_null

class ImpactInterface(dict):
    '''
    Non-ORM object storing facility impact data. Their data can be
    extracted later and imported into the database. This object is
    a dictionary
    '''
    def __init__(self, metric=None, facility_id=None, shakemap_id=None, **kwargs):
        super(ImpactInterface, self).__init__()

        self.update({
            'gray': 0,
            'green': 0,
            'yellow': 0,
            'orange': 0,
            'red': 0,
            'alert_level': '',
            'weight': 0,
            'MMI': 0,
            'PGA': 0,
            'PSA03': 0,
            'PSA10': 0,
            'PSA30': 0,
            'PGV': 0,
            'aebm_extras': None,
            'metric': metric,
            'facility_id': facility_id,
            'shakemap_id': shakemap_id
        })

        self.update(kwargs)

    def set_alert_level(self):
        '''
        Sets the 'alert_level' key on this object
        '''
        levels = ['gray', 'green', 'yellow', 'orange', 'red']
        max_level = 0
        for level in levels:
            if self[level] > max_level:
                max_level = self[level]
                self['alert_level'] = level

    def set_weight(self):
        '''
        Sets the 'weight' key on this object. Defined by the addition
        of the probability of exceedance of being in the 'alert_level'
        damage state or higher
        '''
        fragilities = [
            {'level': 'red', 'rank': 4},
            {'level': 'orange', 'rank': 3},
            {'level': 'yellow', 'rank': 2},
            {'level': 'green', 'rank': 1},
            {'level': 'gray', 'rank': 0}
        ]

        for level in fragilities:
            if level['level'] == self['alert_level']:
                rank = level['rank']

        self['weight'] = rank
        for level in fragilities:
            if level['rank'] >= rank:
                self['weight'] += self[level['level']] / 100

def get_impact(facility, shaking_point, shakemap):
    impact = None
    if facility.aebm and facility.aebm.has_required():
        impact = compute_aebm_impact(facility, shaking_point, shakemap)
    else:
        impact = compute_hazus_impact(facility, shaking_point, shakemap)

    return lower_case_keys(impact)

def compute_aebm_impact(facility, shaking_point, shakemap):
    '''
    Computing damage calculcations with a multi-period spectrum
    '''
    fac_shake = ImpactInterface(
        'AEBM',
        facility.shakecast_id,
        shakemap.shakecast_id
    )

    hazard = get_psa_spectrum(shaking_point)
    capacity = aebm.capacity.get_capacity(**non_null(facility.aebm.__dict__))
    r_rup = get_gps_distance(
        facility.lat,
        facility.lon,
        shakemap.event.lat,
        shakemap.event.lon
    )

    (damage_probabilities,
    capacity,
    demand,
    lower_demand,
    upper_demand,
    median_intersection,
    lower_intersection,
    upper_intersection) = aebm.run(
        capacity,
        hazard,
        shaking_point.get('URAT', .5),
        shakemap.event.magnitude,
        r_rup
    )

    fac_shake['gray'] = damage_probabilities['none'] * 100
    fac_shake['green'] = damage_probabilities['slight'] * 100
    fac_shake['yellow'] = damage_probabilities['moderate'] * 100
    fac_shake['orange'] = damage_probabilities['extensive'] * 100
    fac_shake['red'] = damage_probabilities['complete'] * 100

    fac_shake.update(shaking_point)
    fac_shake.set_alert_level()
    fac_shake.set_weight()

    pp = median_intersection
    rounded_period = round(pp['period'] * 100) / 100
    fac_shake['aebm'] = ('PSA ({} sec): {}'
            .format(rounded_period, pp['acc']))
    fac_shake['aebm_extras'] = {
        'capacity': capacity,
        'demand': demand,
        'lower_demand': lower_demand,
        'upper_demand': upper_demand,
        'median_intersections': median_intersection,
        'lower_intersections':  lower_intersection,
        'upper_intersections': upper_intersection
    }

    return fac_shake

def compute_hazus_impact(facility, shaking_point, shakemap):
    '''
    Computing damage calculations with a single metric
    '''
    shaking_level = shaking_point.get(facility.metric, None)

    fac_shake = ImpactInterface(
        facility.metric,
        facility.shakecast_id,
        shakemap.shakecast_id
    )
    
    if shaking_level is None:
        fac_shake['alert_level'] = 'gray'
    
    else:
        # add shaking levels to fac_shake for record in db
        fac_shake.update(shaking_point)
            
        # get_exceedence green
        fragility = [{'med': facility.red, 'spread': facility.red_beta, 'level': 'red'},
                      {'med': facility.orange, 'spread': facility.orange_beta, 'level': 'orange'},
                      {'med': facility.yellow, 'spread': facility.yellow_beta, 'level': 'yellow'},
                      {'med': facility.green, 'spread': facility.green_beta, 'level': 'green'}]
                    
        prob_sum = 0
        large_prob = 0
        for level in fragility:
            
            # skips non-user-defined levels 
            if level['med'] < 0 or level['spread'] < 0:
                continue
            
            # calculate probability of exceedence
            p = lognorm_opt(med=level['med'],
                            spread=level['spread'],
                            shaking=shaking_level)
            
            # alter based on total probability of higher states
            p -= prob_sum
            prob_sum += p
            fac_shake[level['level']] = p
            
            # keep track of the largest probability
            if p > large_prob:
                large_prob = p
        
        # put remaining exceedance into grey damage state
        fac_shake['gray'] = 100 - prob_sum
        fac_shake.set_alert_level()
        fac_shake.set_weight()

    return fac_shake

def get_psa_spectrum(shaking):
    '''
    Create a sorted PSA spectrum from the values in the shakemap grid
    '''
    spectrum = []
    for key in shaking.keys():
        if 'PSA' in key:
            psa = float('.' + key.split('A')[1])
            spectrum.append({'x': psa, 'y': shaking[key]})

    # return a sorted spectrum
    return sorted(spectrum, key=lambda x: x['x'])

def degreesToRadians(degrees):
  return degrees * math.pi / 180

def get_gps_distance(lat1, lon1, lat2, lon2):
  earthRadiusKm = 6371
  latDiff = degreesToRadians(lat2-lat1)
  lonDiff = degreesToRadians(lon2-lon1)

  lat1 = degreesToRadians(lat1)
  lat2 = degreesToRadians(lat2)

  a = (math.sin(latDiff/2) * math.sin(latDiff/2) +
          math.sin(lonDiff/2) * math.sin(lonDiff/2) *
          math.cos(lat1) * math.cos(lat2))

  c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
  return earthRadiusKm * c

def get_event_impact(shakemap):
    impact_sum = {'gray': 0,
             'green': 0,
             'yellow': 0,
             'orange': 0,
             'red': 0}

    fac_shaking = shakemap.facility_shaking
    
    for s in fac_shaking:
        # record number of facs at each alert level
        impact_sum[s.alert_level] += 1

    return impact_sum

def lognorm_opt(med=0, spread=0, shaking=0):
    '''
    Lognormal calculation to determine probability of exceedance

    Args:
        med (float): Median value that might be exceeded
        spread (float): Uncertainty in the median value
        shaking (float): recorded shaking value

    Returns:
        float: probability of exceedance as a human readable percentage
    '''

    p_norm = (math.erf((shaking-med)/(math.sqrt(2) * spread)) + 1)/2
    return p_norm * 100

def make_inspection_priority(facility=None,
                          shakemap=None,
                          grid=None):
    '''
    Determines inspection priorities for the input facility
    
    Args:
        facility (Facility): A facility to be processed
        shakemap (ShakeMap): The ShakeMap which is associated with the shaking
        grid (ShakeMapGrid): The grid built from the ShakeMap
        notifications (list): List of Notification objects which should be associated with the shaking
        
    Returns:
        dict: A dictionary with all the parameters needed to make a FacilityShaking entry in the database
        ::
            fac_shaking = {'gray': PDF Value,
                           'green': PDF Value,
                           'yellow': PDF Value,
                           'orange': PDF Value,
                           'red': PDF Value,
                           'metric': which metric is used to compute PDF values,
                           'facility_id': shakecast_id of the facility that's shaking,
                           'shakemap_id': shakecast_id of the associated ShakeMap,
                           '_shakecast_id': ID for the FacilityShaking entry that will be created,
                           'update': bool -- True if an ID already exists for this FacilityShaking,
                           'alert_level': string ('gray', 'green', 'yellow' ...),
                           'weight': float that determines inspection priority,
                           'notifications': list of notifications associated with this shaking}
    '''
    
    # get the largest shaking level affecting the facility
    shaking_point = grid.max_shaking(facility=facility)
    if shaking_point is None:
        return False
    
    # use the max shaking value to create fragility curves for the
    # damage states
    fac_shaking = facility.make_alert_level(shaking_point=shaking_point,
                                            shakemap=shakemap)
    return fac_shaking