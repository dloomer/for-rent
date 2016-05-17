import datetime, time

class Central_tzinfo(datetime.tzinfo):
    """Implementation of the Central timezone."""
    def utcoffset(self, dt):
        return datetime.timedelta(hours=-6) + self.dst(dt)

    def _FirstSunday(self, dt):
        """First Sunday on or after dt."""
        return dt + datetime.timedelta(days=(6-dt.weekday()))

    def dst(self, dt):
        # 2 am on the second Sunday in March
        dst_start = self._FirstSunday(datetime.datetime(dt.year, 3, 8, 2))
        # 1 am on the first Sunday in November
        dst_end = self._FirstSunday(datetime.datetime(dt.year, 11, 1, 1))

        if dst_start <= dt.replace(tzinfo=None) < dst_end:
            return datetime.timedelta(hours=1)
        else:
            return datetime.timedelta(hours=0)

    def tzname(self, dt):
        if self.dst(dt) == datetime.timedelta(hours=0):
            return "CST"
        else:
            return "CDT"

class Eastern_tzinfo(datetime.tzinfo):
    """Implementation of the Eastern timezone."""
    def utcoffset(self, dt):
        return datetime.timedelta(hours=-5) + self.dst(dt)

    def _FirstSunday(self, dt):
        """First Sunday on or after dt."""
        return dt + datetime.timedelta(days=(6-dt.weekday()))

    def dst(self, dt):
        # 2 am on the second Sunday in March
        dst_start = self._FirstSunday(datetime.datetime(dt.year, 3, 8, 2))
        # 1 am on the first Sunday in November
        dst_end = self._FirstSunday(datetime.datetime(dt.year, 11, 1, 1))

        if dst_start <= dt.replace(tzinfo=None) < dst_end:
            return datetime.timedelta(hours=1)
        else:
            return datetime.timedelta(hours=0)

    def tzname(self, dt):
        if self.dst(dt) == datetime.timedelta(hours=0):
            return "CST"
        else:
            return "CDT"

class Pacific_tzinfo(datetime.tzinfo):
    """Implementation of the Eastern timezone."""
    def utcoffset(self, dt):
        return datetime.timedelta(hours=-8) + self.dst(dt)

    def _FirstSunday(self, dt):
        """First Sunday on or after dt."""
        return dt + datetime.timedelta(days=(6-dt.weekday()))

    def dst(self, dt):
        # 2 am on the second Sunday in March
        dst_start = self._FirstSunday(datetime.datetime(dt.year, 3, 8, 2))
        # 1 am on the first Sunday in November
        dst_end = self._FirstSunday(datetime.datetime(dt.year, 11, 1, 1))

        if dst_start <= dt.replace(tzinfo=None) < dst_end:
            return datetime.timedelta(hours=1)
        else:
            return datetime.timedelta(hours=0)

    def tzname(self, dt):
        if self.dst(dt) == datetime.timedelta(hours=0):
            return "PST"
        else:
            return "PDT"

class UTC_tzinfo(datetime.tzinfo):
    """Implementation of the UTC timezone."""
    def utcoffset(self, dt):
        return datetime.timedelta(hours=0) + self.dst(dt)

    def _FirstSunday(self, dt):
        """First Sunday on or after dt."""
        return dt + datetime.timedelta(days=(6-dt.weekday()))

    def dst(self, dt):
        return datetime.timedelta(hours=0)

    def tzname(self, dt):
        return "UTC"

def round_datetime_to_month(d, round_down=False):
    if round_down:
        return datetime.datetime(d.year, d.month, 1)
    else:
        if d.month == 12:
            return datetime.datetime(d.year, 12, 31)
        else:
            return datetime.datetime(d.year, d.month+1, 1) - datetime.timedelta(days=1)

def utc_to_central(d):
    return d.replace(tzinfo=UTC_tzinfo()).astimezone(Central_tzinfo()).replace(tzinfo=None)

def central_to_utc(d):
    return d.replace(tzinfo=Central_tzinfo()).astimezone(UTC_tzinfo()).replace(tzinfo=None)

def now_central():
    return utc_to_central(datetime.datetime.now())

def utc_to_pacific(d):
    return d.replace(tzinfo=UTC_tzinfo()).astimezone(Pacific_tzinfo()).replace(tzinfo=None)

def central_to_utc(d):
    return d.replace(tzinfo=Pacific_tzinfo()).astimezone(UTC_tzinfo()).replace(tzinfo=None)

def now_pacific():
    return utc_to_pacific(datetime.datetime.now())
