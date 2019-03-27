#!/usr/bin/python

import os
import os.path
import re
import shutil
from datetime import timedelta, datetime

debug = False
basedir = "{{ disk_base }}"
too_old = datetime.now() - timedelta(days={{ keep_artifacts }})

for dir in os.listdir(basedir):
  if re.match("\d\.x|Develop", dir) is not None: #If it's a branch (Y.x), or Develop
    candidate = os.path.join(basedir, dir)
    candidates = os.listdir(candidate)
    candidates = [os.path.join(candidate, c) for c in candidates] #Prepend the path to the listed item
    if debug:
      for c in candidates:
        print(candidate + ": " + str(datetime.fromtimestamp(os.path.getmtime(c))) + " <= " + str(too_old) + " = " + str(datetime.fromtimestamp(os.path.getmtime(c)) <= too_old))
    candidates = list(filter(lambda c: datetime.fromtimestamp(os.path.getmtime(c)) <= too_old, candidates))
    candidates.sort(key=os.path.getmtime) #Sort by modification time
    if len(candidates) == 1:
      if debug:
        print("Skipping " + candidates[0] + " because there is only one build in that branch")
      continue
    for c in candidates:
      if debug:
        print("Removing " + c)
      shutil.rmtree(c)
