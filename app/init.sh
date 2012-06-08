#!/bin/bash

export PGUSER=ratehere
export PGPASSWORD=r4t00t13
export PGHOST=localhost
export PGOPTIONS=--client-min-messages=warning

psql -d ratehere -f schema.sql
psql -d ratehere -f testdata.sql
