#!/bin/bash

#################################################
#          show_mysql_variable.sh - v1.2
#################################################
# Script para listar variáveis mysql
#################################################
# Copyright 2018 - Diego Galhardo
#################################################
#!/bin/bash

# - Declarando as variaveis de ambiente
SERVICO=$1
MYSQL_BIN=`whereis mysql | awk '{print $2}'`

# Executando comando
RETURN=`$MYSQL_BIN -p'password' -uzabbix -e "SHOW GLOBAL STATUS LIKE '$1';" | grep wsrep | awk '{print $2}'`

if [ $RETURN ]; then
   echo $RETURN
else
   echo "9"
fi

# - FIM

