%define name alerta
%{!?_with_teamcity: %define version 3.0.0}
%{!?_with_teamcity: %define release 9}

Name: %{name}
Summary: Alerta monitoring framework
Version: %{version}
Release: %{release}
Source0: %{name}-%{version}.tar.gz
License: Apache License 2.0
Group: Utilities/System
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
Prefix: /opt
BuildArch: x86_64
Vendor: Nick Satterly <nick.satterly@theguardian.com>
Url: https://github.com/guardian/alerta
BuildRequires: python-devel, python-setuptools, python-virtualenv
Requires: httpd, mod_wsgi

%description
Alerta is a monitoring framework that consolidates alerts
from multiple sources like syslog, SNMP, Nagios, Riemann,
Zabbix, and displays them on an alert console.

%package extras
Summary: Alerta monitoring framework - extras
Group: Utilities/System
Requires: alerta, net-snmp
%description extras
UNKNOWN

%prep
%setup

%build
/usr/bin/virtualenv --no-site-packages alerta
alerta/bin/pip install -r requirements.txt --upgrade
alerta/bin/python setup.py install --single-version-externally-managed --root=/
/usr/bin/virtualenv --relocatable alerta

%install
%__mkdir_p %{buildroot}/opt/alerta/bin
cp %{_builddir}/%{name}-%{version}/alerta/bin/alert* %{buildroot}/opt/alerta/bin/
cp %{_builddir}/%{name}-%{version}/alerta/bin/python* %{buildroot}/opt/alerta/bin/
cp %{_builddir}/%{name}-%{version}/alerta/bin/activate* %{buildroot}/opt/alerta/bin/
cp -r %{_builddir}/%{name}-%{version}/alerta/lib %{buildroot}/opt/alerta/
%__mkdir_p %{buildroot}/var/lib/alerta
%__mkdir_p %{buildroot}%{_sysconfdir}/httpd/conf.d/
%__install -m 0755 etc/httpd-alerta.conf %{buildroot}%{_sysconfdir}/httpd/conf.d/alerta.conf
%__install -m 0755 etc/httpd-alerta-dashboard.conf %{buildroot}%{_sysconfdir}/httpd/conf.d/alerta-dashboard.conf
%__mkdir_p %{buildroot}/opt/alerta/apache
%__install -m 0644 %{_builddir}/%{name}-%{version}/alerta/app/app.wsgi %{buildroot}/opt/alerta/apache
%__install -m 0644 %{_builddir}/%{name}-%{version}/alerta/dashboard/dashboard.wsgi %{buildroot}/opt/alerta/apache

%__mkdir_p %{buildroot}%{_sysconfdir}/init.d/
%__install -m 0755 contrib/redhat/alert-* %{buildroot}%{_sysconfdir}/init.d/
%__mkdir_p %{buildroot}%{_sysconfdir}/snmp/
%__install -m 0444 etc/snmptrapd.conf %{buildroot}%{_sysconfdir}/snmp/snmptrapd.conf.%{name}

prelink -u %{buildroot}/opt/alerta/bin/python

%clean
rm -rf %{buildroot}

%files
%defattr(-,alerta,alerta)
/opt/alerta/bin/alerta
%config(noreplace) /opt/alerta/apache/app.wsgi
%config(noreplace) %{_sysconfdir}/httpd/conf.d/alerta.conf
/opt/alerta/bin/alerta-dashboard
%config(noreplace) /opt/alerta/apache/dashboard.wsgi
%config(noreplace) %{_sysconfdir}/httpd/conf.d/alerta-dashboard.conf
/opt/alerta/bin/python*
/opt/alerta/bin/activate*
/opt/alerta/lib/*
%dir %attr(0775,alerta,root) /var/lib/alerta

%files extras
%defattr(0644,root,root)
%{_sysconfdir}/init.d/alert-*
%defattr(-,alerta,alerta)
/opt/alerta/bin/alert-*
%{_sysconfdir}/snmp/snmptrapd.conf.%{name}

%pre
getent group alerta >/dev/null || groupadd -r alerta
getent passwd alerta >/dev/null || \
    useradd -r -g alerta -d /var/lib/alerta -s /sbin/nologin \
    -c "Alerta monitoring tool" alerta
exit 0

%post
for name in alert-cloudwatch alert-dynect alert-ircbot alert-mailer alert-logger \
    alert-pagerduty alert-pinger alert-solarwinds alert-syslog alert-urlmon
do
    /sbin/chkconfig --add $name
done

%preun
if [ "$1" = "0" ]; then
    for name in alert-cloudwatch alert-dynect alert-ircbot alert-mailer alert-logger \
        alert-pagerduty alert-pinger alert-solarwinds alert-syslog alert-urlmon
    do
        /sbin/chkconfig $name off
        /sbin/chkconfig --del $name
    done
fi

%changelog
* Thu Apr 3 2014 Nick Satterly <nick.satterly@theguardian.com> - 3.0.2-1
- Switch back to init scripts because upstart very old on Centos6
* Thu Mar 27 2014 Nick Satterly <nick.satterly@theguardian.com> - 3.0.0-9
- Package alerta release 3.0 application server and components

