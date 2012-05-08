#!/bin/sh 
 
# Generates a self-signed certificate. 
# Edit dovecot-openssl.cnf before running this. 
 
OPENSSL=openssl 
OPENSSLCONFIG=myserv-openssl.cnf 
 
CERTFILE=myserv.cert
KEYFILE=myserv.key
 
if [ -f $CERTFILE ]; then 
  echo "$CERTFILE already exists, won't overwrite" 
  exit 1 
fi 
 
if [ -f $KEYFILE ]; then 
  echo "$KEYFILE already exists, won't overwrite" 
  exit 1 
fi 
 
$OPENSSL req -new -x509 -nodes -config $OPENSSLCONFIG -out $CERTFILE -keyout $KEYFILE -days 365 || exit 2 
chmod 0600 $KEYFILE 
echo  
$OPENSSL x509 -subject -fingerprint -noout -in $CERTFILE || exit 2 
 
