#!/usr/bin/env python3

import os
import sys
from celery import Celery
from celery_app import celery_app

if __name__ == '__main__':
    # Start Celery worker
    celery_app.start(['worker', '--loglevel=info'])
