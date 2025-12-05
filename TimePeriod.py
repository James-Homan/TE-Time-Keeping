import time

#----------------------------------------------------------------------------------------------------------
# TimePeriod Class
#----------------------------------------------------------------------------------------------------------
class TimePeriod:
    def __init__(self, start_time=None, stop_time=None, area_name=None):
        self._start_time = start_time
        self._stop_time = stop_time
        self._area_name = area_name

    # Getters
    def get_start_time(self):
        return self._start_time
    
    def get_stop_time(self):
        return self._stop_time
    
    def get_area_name(self):
        return self._area_name
    
    # Setters
    def set_start_time(self, value):
        self._start_time = value

    def set_stop_time(self, value):
        self._stop_time = value

    def set_area_name(self, value):
        self._area_name = value