%{!?_with_teamcity: %define version 3.2.6}
%{!?_with_teamcity: %define release 1}

Name: alerta-server
Summary: Alerta monitoring framework
Version: %{version}
Release: %{release}
Source0: alerta-%{version}.tar.gz
License: Apache License 2.0
Group: Utilities/System
BuildRoot: %{_tmppath}/alerta-%{version}-%{release}-buildroot
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

%prep
%setup -n alerta-%{version}

%build
/usr/bin/virtualenv --no-site-packages alerta
alerta/bin/pip install -r requirements.txt --upgrade
alerta/bin/python setup.py install --single-version-externally-managed --root=/
/usr/bin/virtualenv --relocatable alerta

%install
%__mkdir_p %{buildroot}/opt/alerta/bin
cp %{_builddir}/alerta-%{version}/alerta/bin/alert* %{buildroot}/opt/alerta/bin/
cp %{_builddir}/alerta-%{version}/alerta/bin/python* %{buildroot}/opt/alerta/bin/
cp %{_builddir}/alerta-%{version}/alerta/bin/activate* %{buildroot}/opt/alerta/bin/
cp -r %{_builddir}/alerta-%{version}/alerta/lib %{buildroot}/opt/alerta/
%__mkdir_p %{buildroot}%{_sysconfdir}/httpd/conf.d/
%__install -m 0444 etc/httpd-alerta.conf %{buildroot}%{_sysconfdir}/httpd/conf.d/alerta.conf
%__mkdir_p %{buildroot}/opt/alerta/apache
%__install -m 0644 %{_builddir}/alerta-%{version}/alerta/app/app.wsgi %{buildroot}/opt/alerta/apache

prelink -u %{buildroot}/opt/alerta/bin/python

%clean
rm -rf %{buildroot}

%files
%defattr(-,root,root)
%config(noreplace) %{_sysconfdir}/httpd/conf.d/alerta.conf
%defattr(-,alerta,alerta)
/opt/alerta/bin/alertad
%config(noreplace) /opt/alerta/apache/app.wsgi
/opt/alerta/bin/python*
/opt/alerta/bin/activate*
/opt/alerta/lib/*

%pre
getent group alerta >/dev/null || groupadd -r alerta
getent passwd alerta >/dev/null || \
    useradd -r -g alerta -d /var/lib/alerta -s /sbin/nologin \
    -c "Alerta monitoring tool" alerta
exit 0

%changelog
* Wed Sep 24 2014 Nick Satterly <nick.satterly@theguardian.com> - 3.2.6-1
- Release 3.2
* Fri Aug 01 2014 Nick Satterly <nick.satterly@theguardian.com> - 3.1.0-2
- Remove references to alerta dashboard
* Fri May 06 2014 Nick Satterly <nick.satterly@theguardian.com> - 3.1.0-1
- Remove references to alerta dashboard
* Thu Apr 03 2014 Nick Satterly <nick.satterly@theguardian.com> - 3.0.3-1
- Bug fixes
* Thu Apr 03 2014 Nick Satterly <nick.satterly@theguardian.com> - 3.0.2-3
- Switch back to init scripts because upstart very old on Centos6
* Thu Mar 27 2014 Nick Satterly <nick.satterly@theguardian.com> - 3.0.0-9
- Package alerta release 3.0 application server and components

