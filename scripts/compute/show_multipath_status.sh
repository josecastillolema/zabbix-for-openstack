#!/bin/bash

sudo multipath -ll | grep failed > /dev/null
echo $?
