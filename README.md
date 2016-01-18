# Yet Another Dynamic DNS Client 
*Dynamic DNS Client for CloudFlare written in Python*

Unless you have a static public IP address, this is probably the most reliable way to ensure your servers are always accessible to you over the Internet.

#####Features:
* Supports IPv4 and IPv6 records (A, AAAA)
* Supports multiple domains with multiple hosts per domain
* Simultaneous IPv4 and IPv6 support for single host
* No third party libraries used. Only standard python libs.
* Works with Python 2 and 3
* Designed to run on any OS that supports Python (i.e. not dependent on any OS specific tools)
* Only makes changes to CloudFlare's zone files when necessary. Stores last IP address of each host in config file.
* Simple JSON config file
* Automatically collects and saves the zone and host IDs if missing.

#####Simple JSON config file:
```javascript
{
 "domains": [
  {
   "hosts": [
    {
     "id": "", 
     "ipv4": "", 
     "ipv6": "", 
     "name": "HOST_NAME_HERE e.g. www", 
     "types": ["A"]
    }
   ], 
   "id": "", 
   "name": "DOMAIN_NAME_HERE e.g. myserver.com"
  }
 ], 
 "user": {
  "api_key": "CLOUDFLARE_API_KEY_HERE", 
  "email": "CLOUDFLARE_EMAIL_HERE"
 }
}
```

#####Getting Started:
1. Download and place the ```cf-ddns.py``` and ```cf-ddns.conf``` files somewhere on your server (e.g. ```/usr/local/bin/``` or ```~/```). 
2. Open the ```cf-ddns.conf``` file in a text editor and specify your email address, API key, domain name, and host name. The record type is set to A by default. Change it to AAAA or add AAAA to the list if necessary.
3. Set +x permission to the script for your user by running ```chmod +x /PATH_TO_FILE/cf-ddns.py```
4. Run ```crontab -e``` and append this line to it: ```*/5 * * * * /PATH_TO_FILE/cf-ddns.py >/dev/null 2>&1```. be sure to change the path to match your setup.
5. That's it :) 

#####Miscellaneous:
* New features and code improvements are welcomed
* If you find a bug please create a GitHub issue for it
