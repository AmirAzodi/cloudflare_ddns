#! /usr/bin/env python
# place cf-ddns.py and cf-ddns.conf on your server (e.g. /usr/local/bin/ or ~/)
# run this command:
# chmod +x /PATH_TO_FILE/cf-ddns.sh
# open cf-ddns.conf in a text editor and set the necessary parameters.
# (minimum config: one domain name, one host name, email address and api_key)
# run `crontab -e` and append this line to it:
# 0 */5 * * * * /PATH_TO_FILE/cf-ddns.py >/dev/null 2>&1

try:
    # For Python 3.0 and later
    from urllib.request import urlopen
    from urllib.request import Request
    from urllib.error import URLError
    from urllib.error import HTTPError
    # import urllib.parse
except ImportError:
    # Fall back to Python 2's urllib2
    from urllib2 import urlopen
    from urllib2 import Request
    from urllib2 import HTTPError
    from urllib2 import URLError

import json


config_file_name = 'cf-ddns.conf'

with open(config_file_name, 'r') as config_file:
    try:
        config = json.loads(config_file.read())
    except ValueError:
        print('* problem with the config file')
        exit(0)

if not config['user']['email'] or not config['user']['api_key']:
    print('* missing CloudFlare auth credentials')
    exit(0)

content_header = {'X-Auth-Email': config['user']['email'],
                  'X-Auth-Key': config['user']['api_key'],
                  'Content-type': 'application/json'}

base_url = 'https://api.cloudflare.com/client/v4/zones/'

public_ipv4 = None
public_ipv6 = None
ip_version = None

try:
    public_ipv4 = urlopen(Request(
        'http://ipv4.icanhazip.com/')).read().rstrip().decode('utf-8')
except URLError as e:
    print('* no public IPv4 address detected')

try:
    public_ipv6 = urlopen(Request(
        'http://ipv6.icanhazip.com/')).read().rstrip().decode('utf-8')
except URLError as e:
    print('* no public IPv6 address detected')

if public_ipv4 is None and public_ipv4 is None:
    print('* Failed to get any public IP address')
    exit(0)

update = False

for domain in config['domains']:
    # check to make sure domain name is specified
    if not domain['name']:
        print('* missing domain name')
        continue

    # get domain zone id from CloudFlare if missing
    if not domain['id']:
        try:
            print(
                '* zone id for "{0}" is missing. attempting to '
                'get it from cloudflare...'.format(domain['name']))
            zone_id_req = Request(base_url, headers=content_header)
            zone_id_resp = urlopen(zone_id_req)
            for d in json.loads(zone_id_resp.read().decode('utf-8'))['result']:
                if domain['name'] == d['name']:
                    domain['id'] = d['id']
                    print('* zone id for "{0}" is'
                          ' {1}'.format(domain['name'], domain['id']))
        except HTTPError as e:
            print('* could not get zone id for: {0}'.format(domain['name']))
            print('* possible causes: wrong domain and/or auth credentials')
            continue

    # get domain zone id from CloudFlare if missing
    for host in domain['hosts']:
        fqdn = host['name'] + '.' + domain['name']

        # check to make sure host name is specified
        # otherwise move on to the next host
        if not host['name']:
            print('* host name missing')
            continue

        # get host id from CloudFlare if missing
        if not host['id']:
            print(
                '* host id for "{0}" is missing. attempting'
                ' to get it from cloudflare...'.format(fqdn))
            rec_id_req = Request(
                base_url + domain['id'] + '/dns_records/',
                headers=content_header)
            rec_id_resp = urlopen(rec_id_req)
            parsed_host_ids = json.loads(rec_id_resp.read().decode('utf-8'))
            for h in parsed_host_ids['result']:
                if fqdn == h['name']:
                    host['id'] = h['id']
                    print('* host id for "{0}" is'
                          ' {1}'.format(fqdn, host['id']))

        # iterate over the record types
        for t in host['types']:
            # select which IP to use based on dns record type (e.g. A or AAAA)
            if t not in ('A', 'AAAA'):
                print('* wrong or missing dns record type: {0}'.format(t))
                continue
            elif t == 'A':
                if public_ipv4:
                    public_ip = public_ipv4
                    ip_version = 'ipv4'
                else:
                    print('* cannot set A record because no IPv4 is available')
                    continue
            elif t == 'AAAA':
                if public_ipv6:
                    public_ip = public_ipv6
                    ip_version = 'ipv6'
                else:
                    print('* cannot set AAAA record because'
                          ' no IPv6 is available')
                    continue

            # update ip address if it has changed since last update
            if host[ip_version] != public_ip:
                try:
                    # make sure dns record type is specified (e.g A, AAAA)
                    if not t:
                        raise Exception

                    data = json.dumps({
                        'id': host['id'],
                        'type': t,
                        'name': host['name'],
                        'content': public_ip
                    })
                    url_path = '{0}{1}{2}{3}'.format(base_url,
                                                     domain['id'],
                                                     '/dns_records/',
                                                     host['id'])
                    update_request = Request(
                        url_path,
                        data=data.encode('utf-8'),
                        headers=content_header)
                    update_request.get_method = lambda: 'PUT'
                    update_res_obj = json.loads(
                        urlopen(update_request).read().decode('utf-8'))
                    if update_res_obj['success']:
                        update = True
                        host[ip_version] = public_ip
                        print('* update successful (type: {0}, fqdn: {1}'
                              ', ip: {2})'.format(t, fqdn, public_ip))
                except (Exception, HTTPError) as e:
                    print('* update failed (type: {0}, fqdn: {1}'
                          ', ip: {2})'.format(t, fqdn, public_ip))

# if any records were updated, update the config file accordingly
if update:
    print('* updates completed. bye.')
    with open(config_file_name, 'w') as config_file:
        json.dump(config, config_file, indent=1, sort_keys=True)
else:
    print('* nothing to update. bye.')
