import GeoIP
from bottle import request


def ip_country(addr):
    gp = request.app.config['geoip']
    cc = gp.country_code_by_addr(addr)
    if cc is None:
        return cc
    return cc.lower()


def pre_init(config):
    data_path = config['data.geoip']
    config['geoip'] = GeoIP.open(data_path, GeoIP.GEOIP_MEMORY_CACHE)
