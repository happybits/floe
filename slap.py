#!/usr/bin/env python

import floe
from uuid import uuid4
import os
import sys
from time import time, sleep


def xid():
    return uuid4().hex

random_binary_chunk = os.urandom(200)

ct = 0


BATCHSIZE = 100

conn = floe.get_connection('test')
conn.flush()

while True:
    try:
        mapping = {xid(): random_binary_chunk for _ in range(1,  BATCHSIZE)}
        start = time()
        conn.set_multi(mapping)
        end = time()
        ct += len(mapping)
        sys.stdout.write('\rinserted: %s     latency: %.5f' %
                         (ct, ((end - start) / BATCHSIZE)))
    except (KeyboardInterrupt, SystemExit):
        break
    except Exception as e:
        sys.stdout.write('\n\nEXCEPTION %s\n' % str(e))
        sleep(1)

sys.stdout.write('\n\nDONE\n')
