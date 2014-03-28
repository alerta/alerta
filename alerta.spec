%define name alerta
%define version 3.0.0
%define release 8

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
%__mkdir_p %{buildroot}%{_sysconfdir}/init/
%__install -m 0755 etc/upstart/alert-* %{buildroot}%{_sysconfdir}/init/
%__mkdir_p %{buildroot}/opt/alerta/bin
cp %{_builddir}/%{name}-%{version}/alerta/bin/alert* %{buildroot}/opt/alerta/bin/
cp %{_builddir}/%{name}-%{version}/alerta/bin/python* %{buildroot}/opt/alerta/bin/
cp %{_builddir}/%{name}-%{version}/alerta/bin/activate* %{buildroot}/opt/alerta/bin/
cp -r %{_builddir}/%{name}-%{version}/alerta/lib %{buildroot}/opt/alerta/
%__mkdir_p %{buildroot}/var/lib/alerta
%__mkdir_p %{buildroot}%{_sysconfdir}/snmp/
%__install -m 0444 etc/snmptrapd.conf %{buildroot}%{_sysconfdir}/snmp/snmptrapd.conf.%{name}
%__mkdir_p %{buildroot}%{_sysconfdir}/httpd/conf.d/
%__install -m 0755 etc/httpd-alerta.conf %{buildroot}%{_sysconfdir}/httpd/conf.d/alerta.conf
%__install -m 0755 etc/httpd-alerta-dashboard.conf %{buildroot}%{_sysconfdir}/httpd/conf.d/alerta-dashboard.conf

%clean
rm -rf %{buildroot}

%files
%defattr(-,alerta,alerta)
/opt/alerta/bin/alerta
%{_sysconfdir}/httpd/conf.d/alerta.conf
/opt/alerta/bin/alerta-dashboard
%{_sysconfdir}/httpd/conf.d/alerta-dashboard.conf
/opt/alerta/bin/python*
/opt/alerta/bin/activate*
/opt/alerta/lib/*
%dir %attr(0775,alerta,root) /var/lib/alerta

%files extras
%defattr(0644,root,root)
%{_sysconfdir}/init/alert-*
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
/sbin/initctl reload-configuration

%changelog
* Thu Mar 27 2013 Nick Satterly <nick.satterly@theguardian.com> - 3.0.0-8
- Package alerta relase 3.0 command-line tools

