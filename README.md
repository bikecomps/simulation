Simulation of Bike Share Networks
=================================

The goal of this project is to provide a webapp that will allow bikeshare 
network managers to analyze and optimize their networks.

Setup
-----
You must create a new PostGres user/owner called `bikecomps`. For 
a guide on how to create users, see [this]
(http://www.cyberciti.biz/faq/howto-add-postgresql-user-account/).
The `<username>` and `<password>` that you must use can be found in `utils/hidden.py`

To import the database file into postgres, run:
`psql -U <username> data_model < models/data_model.sql`

Should you run into any problems, see [documentation](http://www.postgresql.org/docs/9.1/static/backup-dump.html).

Running Files
-------------
We've modularized our entire directory. 
In order to run any program you'd
have to use this syntax: `python -m <sub-dir>.<file-name>`. For example,
if you want to run `views/app.py`, invoke `python -m views.app` from
the `simulation` base directory.

