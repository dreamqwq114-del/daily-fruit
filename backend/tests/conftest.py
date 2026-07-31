import os


# Unit and API tests must never inherit the local production database config.
os.environ["APP_ENV"] = "test"
os.environ["DEBUG"] = "false"
os.environ["DATABASE_URL"] = " "
