#
# SdParamSyslogParser.py
#
# @param string text
#   Syslog STRUCTURED-DATA eg. [SD-ID PARAM-NAME="PARAM-VALUE" PARAM-NAME= ... ]
#   eg. [origin software="rsyslogd" swVersion="4.6.2" x-pid="2867" x-info="http://www.rsyslog.com"]
#
# @return array tags
#   SD-ID + '-' + PARAM-NAME + '=' + PARAM-VALUE
#   eg. ['origin-software=rsyslogd', 'origin-swVersion=4.6.2', 'origin-x-pid=2867', 'origin-x-info=http://www.rsyslog.com']

sd_elements = re.findall('\[([^\]]+)', text)
for sd_element in sd_elements:
    m = re.match('(?P<sd_id>\S+) (?P<sd_params>.*)', sd_element)
    if m:
        param_bits = m.groupdict()
        sd_params = re.findall('(?P<param>[^="\s]+="[^"]+")', param_bits['sd_params'])
        for idx, el in enumerate(sd_params):
            sd_params[idx] = param_bits['sd_id']+'-'+el.replace('"','')
        tags.extend(sd_params)
