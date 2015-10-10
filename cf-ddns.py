#!/usr/bin/python
# place cf-ddns.py and cf-ddns.conf on your server (e.g. /usr/local/bin/ or ~/)
# run this command:
# chmod +x /PATH_TO_FILE/cf-ddns.sh
# open cf-ddns.conf in a text editor and set the necessary parameters. 
# (minimum config: one domain name, one host name, email address and api_key)
# run `crontab -e` and append this line to it:
# 0 */5 * * * * /PATH_TO_FILE/cf-ddns.py >/dev/null 2>&1

import urllib2, json

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

content_header = {'X-Auth-Email':config['user']['email'],
                  'X-Auth-Key':config['user']['api_key'],
                  'Content-type':'application/json'}

base_url = 'https://api.cloudflare.com/client/v4/zones/'

public_IPv4 = None
public_IPv6 = None
ip_version = None

try:
  # http://ipv4.icanhazip.com/
  # IPv4 alternatives: 104.238.145.30, 104.238.136.31, 104.238.141.75
  public_IPv4 = urllib2.urlopen(urllib2.Request('104.238.145.30')).read().rstrip()
except urllib2.URLError as e:
  print('* no public IPv4 address detected')

try:
  # http://ipv6.icanhazip.com/
  # IPv6 alternatives: 2001:19f0:6400:8745::30, 2001:19f0:9000:8945::31, 2001:19f0:6000:8e68::75
  public_IPv6 = urllib2.urlopen(urllib2.Request('[2001:19f0:9000:8945::30]')).read().rstrip()
except urllib2.URLError as e:
  print('* no public IPv6 address detected')

if public_IPv4 is None and public_IPv4 is None:
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
      print('* zone id for \"{0}\" is missing. attempting to get it from cloudflare...'.format(domain['name']))
      zone_id_req = urllib2.Request(base_url, headers=content_header)
      zone_id_resp = urllib2.urlopen(zone_id_req)
      for d in json.loads(zone_id_resp.read())['result']:
        if domain['name'] == d['name']:
          domain['id'] = d['id']
          print('* zone id for \"{0}\" is {1}'.format(domain['name'], domain['id']))
    except urllib2.HTTPError as e:
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
      print('* host id for \"{0}\" is missing. attempting to get it from cloudflare...'.format(fqdn))
      rec_id_req = urllib2.Request(base_url + domain['id'] + '/dns_records/', headers=content_header)
      rec_id_resp = urllib2.urlopen(rec_id_req)
      parsed_host_ids = json.loads(rec_id_resp.read())
      for h in parsed_host_ids['result']:
        if fqdn == h['name']:
          host['id'] = h['id']
          print('* host id for \"{0}\" is {1}'.format(fqdn, host['id']))

    # iterate over the record types
    for t in host['types']:
      # select which IP to use based on dns record type (e.g. A or AAAA)
      if t not in ("A", "AAAA"):
        print('* wrong or missing dns record type: {0}'.format(t))
        continue
      elif t == 'A':
        if public_IPv4:
          public_IP = public_IPv4
          ip_version = 'ipv4'
        else:
          print('* cannot set A record because no IPv4 is available')
          continue
      elif t == 'AAAA':
        if public_IPv6:
          public_IP = public_IPv6
          ip_version = 'ipv6'
        else:
          print('* cannot set AAAA record because no IPv6 is available')
          continue

      # update ip address if it has changed since last update
      if host[ip_version] != public_IP:
        try:
          # check to make sure dns record type is specified (e.g A, AAAA)
          if not t:
            raise Exception 
          data = json.dumps({"id":host['id'],"type":t,"name":host['name'],"content":public_IP})
          url_path = '{0}{1}{2}{3}'.format(base_url,domain['id'],'/dns_records/',host['id'])
          update_request = urllib2.Request(url_path, data=data, headers=content_header)
          update_request.get_method = lambda: 'PUT'
          update_res_obj = json.loads(urllib2.urlopen(update_request).read())
          if update_res_obj['success']:
            update = True
            host[ip_version] = public_IP
            print('* update successful (type: {0}, fqdn: {1}, IP: {2})'.format(t, fqdn, public_IP))
        except (Exception, urllib2.HTTPError) as e:
          print('* update failed (type: {0}, fqdn: {1}, IP: {2})'.format(t, fqdn, public_IP))

# if any records were updated, update the config file accordingly
if update:
  print('* updates completed. bye.')
  with open(config_file_name, 'w') as config_file:
    json.dump(config, config_file, indent=1, sort_keys=True)
else:
  print('* nothing to update. bye.')
