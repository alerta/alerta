%define name alerta
%define release 1
# %%define version # Specified in the wrapper script

Name: %{name}
Summary: Alerta monitoring framework
Version: %{version}
Release: %{release}
License: Apache License 2.0
Group: Utilities/System
# BuildRoot: Specified in the wrapper script
Prefix: %{_prefix}
BuildArch: noarch
Vendor: Nick Satterly <nick.satterly@guardian.co.uk>
Url: https://github.com/guardian/alerta

%description
Alerta is an monitoring framework that uses a message broker
for alert transport, mongoDB as the alert status database,
elasticsearch for long-term alert archiving and has a
JavaScript web interface for an alert console.

%package server
Summary: Alerta monitoring framework
Group: Utilities/System
Requires: python-argparse, stomppy, python-flask, PyYAML, pytz
Requires: python-boto, python-dynect, alerta-common, httpd, python-suds
Requires: python-pymongo, mongo-10gen-server, rabbitmq-server, logrotate
%description server
UNKNOWN

%package client
Summary: Alerta monitoring framework
Group: Utilities/System
Requires: python-argparse, alerta-common
%description client
UNKNOWN

%package common
Summary: Alerta monitoring framework
Group: Utilities/System
%description common
UNKNOWN

%prep
# we ensure that the sources are in the right place before calling rpmbuild

%build
python setup.py build

%install
python setup.py install --single-version-externally-managed --root=$RPM_BUILD_ROOT --record=INSTALLED_FILES

%__mkdir_p %{buildroot}%{_initrddir}/
%__install -m 0755 etc/init.d/* %{buildroot}%{_initrddir}/
%__mkdir_p %{buildroot}%{_sysconfdir}/%{name}/
%__cp etc/%{name}/%{name}.conf %{buildroot}%{_sysconfdir}/%{name}/%{name}.conf
%__mkdir_p %{buildroot}%{_sysconfdir}/httpd/conf.d/
%__install -m 0755 contrib/apache/%{name}.conf %{buildroot}%{_sysconfdir}/httpd/conf.d/%{name}.conf
%__mkdir_p %{buildroot}%{_var}/www/html/%{name}/
%__install -m 0755 contrib/apache/%{name}.wsgi %{buildroot}%{_var}/www/html/%{name}/%{name}.wsgi
%__mkdir_p %{buildroot}%{_var}/www/html/%{name}/dashboard/
%__cp -r dashboard/* %{buildroot}%{_var}/www/html/%{name}/dashboard/
%__mkdir_p %{buildroot}%{_sysconfdir}/snmp/
%__install -m 0444 etc/snmptrapd.conf %{buildroot}%{_sysconfdir}/snmp/snmptrapd.conf.%{name}
%__mkdir_p %{buildroot}%{_sysconfdir}/logrotate.d/
%__cp etc/%{name}.logrotate %{buildroot}%{_sysconfdir}/logrotate.d/%{name}
%__install -m 0775 -d %{buildroot}%{_var}/log/%{name}
%__mkdir_p %{buildroot}%{_var}/run/%{name}

%clean
rm -rf $RPM_BUILD_ROOT

%files server
%defattr(-,root,root)
%{_initrddir}/
%config(noreplace) %{_sysconfdir}/httpd/conf.d/%{name}.conf
%config(noreplace) /var/www/html/%{name}/%{name}.wsgi
%{_var}/www/html/%{name}/dashboard/
%{_sysconfdir}/snmp/snmptrapd.conf.%{name}
%{_sysconfdir}/logrotate.d/%{name}
%dir %attr(775,alerta,apache) /var/log/%{name}
%dir %attr(-,alerta,alerta) /var/run/%{name}
%{_bindir}/alerta
%{_bindir}/alerta-api
%{_bindir}/alert-aws
%{_bindir}/alert-dynect
%{_bindir}/alert-ircbot
%{_bindir}/alert-logger
%{_bindir}/alert-mailer
%{_bindir}/alert-pagerduty
%{_bindir}/alert-pinger
%{_bindir}/alert-snmptrap
%{_bindir}/alert-solarwinds
%{_bindir}/alert-syslog
%{_bindir}/alert-urlmon

%files client
%defattr(-,root,root)
%{_sysconfdir}/logrotate.d/%{name}
%dir %attr(775,alerta,apache) /var/log/%{name}
%dir %attr(-,alerta,alerta) /var/run/%{name}
%{_bindir}/alert-query
%{_bindir}/alert-sender
%{_bindir}/alert-checker

%files common
%{python_sitelib}/*
%defattr(-,root,root)
%config(noreplace) %{_sysconfdir}/%{name}/%{name}.conf
%dir %attr(775,alerta,apache) /var/log/%{name}
%dir %attr(-,alerta,alerta) /var/run/%{name}

%pre server
if ! getent group alerta >/dev/null 2>&1; then
  /usr/sbin/groupadd -g 799 alerta
fi

if ! getent passwd alerta >/dev/null 2>&1; then
  /usr/sbin/useradd -g alerta -u 799 -d %{prefix} -r -s /sbin/nologin alerta >/dev/null 2>&1 || exit 1
fi

%post server
for name in alerta alert-aws alert-dynect alert-ircbot alert-logger alert-mailer \
    alert-pagerduty alert-pinger alert-solarwinds alert-syslog alert-urlmon
do
    /sbin/chkconfig --add $name
done

%preun server
if [ "$1" = "0" ]; then
    for name in alerta alert-aws alert-dynect alert-ircbot alert-logger alert-mailer \
        alert-pagerduty alert-pinger alert-solarwinds alert-syslog alert-urlmon
    do
        /sbin/chkconfig $name off
        /sbin/chkconfig --del $name
    done
fi

%changelog
* Wed May 15 2013 Nick Satterly <nick.satterly@guardian.co.uk> - 2.0.29-1
- Sundry enhancements
* Tue May 14 2013 Nick Satterly <nick.satterly@guardian.co.uk> - 2.0.28-1
- Fade out unselected alert status indicators
* Mon May 13 2013 Nick Satterly <nick.satterly@guardian.co.uk> - 2.0.27-1
- Solarwinds event correlation and multiline SNMP trap varbinds
* Mon May 06 2013 Nick Satterly <nick.satterly@guardian.co.uk> - 2.0.26-1
- Enhancements to SolarWinds integration
* Thu May 02 2013 Nick Satterly <nick.satterly@guardian.co.uk> - 2.0.25-1
- Minor bug fixes and enhancements
* Thu May 02 2013 Nick Satterly <nick.satterly@guardian.co.uk> - 2.0.24-1
- Add support for solarwinds integration
* Thu Apr 25 2013 Nick Satterly <nick.satterly@guardian.co.uk> - 2.0.23-1
- Retire alert-ganglia in favour of Riemann
* Tue Apr 23 2013 Nick Satterly <nick.satterly@guardian.co.uk> - 2.0.22-1
- Minor fixs and change pymongo to python-pymongo
* Mon Apr 15 2013 Nick Satterly <nick.satterly@guardian.co.uk> - 2.0.21-1
- Minor fix to pinger
* Mon Apr 15 2013 Nick Satterly <nick.satterly@guardian.co.uk> - 2.0.20-1
- Replace alert-notify with alert-pagerduty
- Simplify emailer and fix pinger option for Linux
- Ensure modified alerts pushed back onto queue
* Fri Apr 12 2013 Nick Satterly <nick.satterly@guardian.co.uk> - 2.0.19-1
- Get alert-mailer working again
* Thu Apr 11 2013 Nick Satterly <nick.satterly@guardian.co.uk> - 2.0.18-1
- Sundry fixes
* Thu Apr 11 2013 Nick Satterly <nick.satterly@guardian.co.uk> - 2.0.17-1
- Fix to alert-aws
* Wed Apr 10 2013 Nick Satterly <nick.satterly@guardian.co.uk> - 2.0.16-2
- Make requires python-dynect consistent
* Wed Apr 10 2013 Nick Satterly <nick.satterly@guardian.co.uk> - 2.0.16-1
- Fix init scripts and other sundry bug fixes
* Mon Apr 08 2013 Nick Satterly <nick.satterly@guardian.co.uk> - 2.0.15-1
- Sundry bug fixes
* Mon Apr 08 2013 Nick Satterly <nick.satterly@guardian.co.uk> - 2.0.14-2
- Fix alerta.conf conflict
* Mon Apr 08 2013 Nick Satterly <nick.satterly@guardian.co.uk> - 2.0.14-1
- Add alert-pinger and standard alert de-duplication module
* Thu Apr 04 2013 Nick Satterly <nick.satterly@guardian.co.uk> - 2.0.12-1
- Make severity widget click through to details widget for dashboards
* Thu Apr 04 2013 Nick Satterly <nick.satterly@guardian.co.uk> - 2.0.11-1
- Make API port configurable, add switchboard and kill auto-refresh
* Wed Apr 03 2013 Nick Satterly <nick.satterly@guardian.co.uk> - 2.0.10-1
- Add management URLs and fix widget
* Wed Apr 03 2013 Nick Satterly <nick.satterly@guardian.co.uk> - 2.0.9-1
- Move alert console to templates directory
* Tue Apr 02 2013 Nick Satterly <nick.satterly@guardian.co.uk> - 2.0.8-1
- Add alert widget
* Tue Apr 02 2013 Nick Satterly <nick.satterly@guardian.co.uk> - 2.0.7-1
- Add status filter to console
* Sat Mar 30 2013 Nick Satterly <nick.satterly@guardian.co.uk> - 2.0.6-1
- Sundry fixes
* Thu Mar 28 2013 Nick Satterly <nick.satterly@guardian.co.uk> - 2.0.5-1
- Add moreInfo and graphUrls and fix alert-ganglia
* Thu Mar 28 2013 Nick Satterly <nick.satterly@guardian.co.uk> - 2.0.4-1
- Add support for complex queries and resource list
* Thu Mar 28 2013 Nick Satterly <nick.satterly@guardian.co.uk> - 2.0.3-1
- Fix SNMP trap parser
* Wed Mar 27 2013 Nick Satterly <nick.satterly@guardian.co.uk> - 2.0.2-1
- Add heartbeat support to API endpoint
* Wed Mar 27 2013 Nick Satterly <nick.satterly@guardian.co.uk> - 2.0.1-1
- Fix alert-sender origin and version
* Wed Mar 27 2013 Nick Satterly <nick.satterly@guardian.co.uk> - 2.0.0-2
- Add default snmptrapd.conf
* Thu Mar 21 2013 Nick Satterly <nick.satterly@guardian.co.uk> - 2.0.0-1
- Initial package for alerta v2

