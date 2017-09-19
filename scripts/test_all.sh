#!/bin/sh

export DATABASE_ENGINE=mongodb
nosetests
export DATABASE_ENGINE=elasticsearch
nosetests
export DATABASE_ENGINE=postgres
nosetests
