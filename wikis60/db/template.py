#!/usr/bin/env python
# TODO

import re
import xml.etree.cElementTree as ET

template_re  = re.compile('\{\{(.*?)\}\}')