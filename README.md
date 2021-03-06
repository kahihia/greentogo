# GreenToGo

[![forthebadge made-with-python](http://ForTheBadge.com/images/badges/made-with-python.svg)](https://www.python.org/)
[![PyPI pyversions](https://img.shields.io/pypi/pyversions/ansicolortags.svg)](https://pypi.python.org/pypi/ansicolortags/)
[![Website shields.io](https://img.shields.io/website-up-down-green-red/http/shields.io.svg)](https://app.durhamgreentogo.com/)
[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://github.com/greentogo/greentogo/graphs/commit-activity)
[![GitHub issues](https://img.shields.io/github/issues/greentogo/greentogo.svg)](https://github.com/greentogo/greentogo/issues)
[![Build Status](https://travis-ci.org/greentogo/greentogo.svg?branch=master)](https://travis-ci.org/greentogo/greentogo)


This project contains both the GreenToGo mobile app made in react-native/expo, and the Django web application with an API.

The files are laid out in accordance with recommendations from Two Scoops of Django.

## Django setup

1. This application uses Python 3.6, so ensure you have that installed.
1. Setup PostgreSQL. On a Mac with Homebrew, run `brew install postgresql`. If you are on a Mac without Homebrew, download and install [Postgres.app](https://postgresapp.com/). If you are on Windows, see https://www.postgresql.org/download/windows/. If you are on Linux, you know what to do.
1. Make sure you are in a virtualenv. Using [direnv](https://direnv.net/) or [pyenv-installer](https://github.com/pyenv/pyenv-installer) is a very easy way to make this happen.
1. Run `make check` to make sure you have all the required programs installed.
1. Run `make requirements`. If that worked, you should be ready for the next part!
1. Run `make greentogo/greentogo/.env`. This will create a file to hold the database URL and API keys that you will need. (See "Environment Setup" below.)
1. Make sure that the `node-sass` command is installed on by running `npm i -g node-sass`.
1. Run `./greentogo/manage.py migrate`.
1. Run `./greentogo/manage.py runserver` and navigate to the address provided. 

## Environment setup

Database configuration and API keys are held in `greentogo/greentogo/.env`, which can be created by running `make greentogo/greentogo/.env`. The `.env` file looks like the following:

```
DEBUG=1
DATABASE_URL=postgres://user@/greentogo
EMAIL_ADDRESS=purchases@durhamgreentogo.com
EMAIL_REPLY_TO=info@durhamgreentogo.com
GOOGLE_API_KEY=ADD_KEY_HERE
STRIPE_SECRET_KEY=ADD_KEY_HERE
STRIPE_PUBLISHABLE_KEY=ADD_KEY_HERE
STRIPE_WEBHOOK_SECRET=ADD_KEY_HERE
ROLLBAR_KEY=ADD_KEY_HERE
```

For `DATABASE_URL`, change this to match your local database setup. If you have a local database named `greentogo` owned by your user account, you should be able to replace `user` with your own username and be set up.

For the Stripe keys, you will need to create an account at [Stripe](https://stripe.com/). Once you have an account, you can get your secret and publishable keys at <https://dashboard.stripe.com/account/apikeys>. For development, you can ignore `STRIPE_WEBHOOK_SECRET` and `ROLLBAR_KEY`.

Rollbar is our error reporting dashboard. It can be viewed here:
https://rollbar.com/ClintonDreisbach/GreenToGo-backend/

For your Google API key, you can generate a key at <https://console.developers.google.com/apis/credentials>. This key will need access to the Google Maps API. However, you can also ignore this in development unless working on part of the application that uses maps.


## Create a test user

First, make sure the server is running (`./greentogo/manage.py runserver`). If you haven't already, make an account on the developer instance. Since this is a fake account and you can grant access to whatever you like, the email does not matter. Make sure you have a fresh install of the `g2g` database in postgres. Then, begin using postgres' cli with `psql greentogo`.

Next, run `UPDATE core_user SET is_superuser = TRUE, is_staff = TRUE, is_active = TRUE WHERE username = '<your-username>'`. This will grant you access to a lot of priveleges in the site, including the `/admin/` page. 

## Stripe Testing

Here are fake cards for stripe testing:
https://stripe.com/docs/testing#cards

## Other docs

Are you a server administrator? [Check out our admin docs.](./docs/server-admin.md)

Kanban Board:

https://trello.com/b/Ie0XvutP/greentogo-kanban-board
