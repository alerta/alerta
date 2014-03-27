%define name alerta
%define version 3.0.0
%define release 3

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
BuildRequires: python-devel, python-setuptools, python-pip, python-virtualenv

%description
Alerta is a monitoring framework that consolidates alerts
from multiple sources like syslog, SNMP, Nagios, Riemann,
Zabbix, and displays them on an alert console.

%package server
Summary: Alerta monitoring framework - sever
Group: Utilities/System
Requires: alerta-common, mongodb, mongodb-server, rabbitmq-server
%description server
UNKNOWN

%package extras
Summary: Alerta monitoring framework - extras
Group: Utilities/System
Requires: alerta-common, net-snmp
%description extras
UNKNOWN

%package web
Summary: Alerta monitoring framework - web dashboard
Group: Utilities/System
Requires: alerta-common
%description web
UNKNOWN

%package common
Summary: Alerta monitoring framework - common libraries
Group: Utilities/System
%description common
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
cp -r %{_builddir}/%{name}-%{version}/alerta/lib %{buildroot}/opt/alerta/lib
%__mkdir_p %{buildroot}/var/lib/alerta
%__mkdir_p %{buildroot}%{_sysconfdir}/snmp/
%__install -m 0444 etc/snmptrapd.conf %{buildroot}%{_sysconfdir}/snmp/snmptrapd.conf.%{name}

%clean
rm -rf %{buildroot}

%files server
%defattr(-,alerta,alerta)
/opt/alerta/bin/alerta

%files extras
%defattr(-,alerta,alerta)
/opt/alerta/bin/alert-*
%{_sysconfdir}/snmp/snmptrapd.conf.%{name}

%files web
%defattr(-,alerta,alerta)
/opt/alerta/bin/alerta-dashboard

%files common
%defattr(-,alerta,alerta)
/opt/alerta/bin/python*
/opt/alerta/bin/activate*
/opt/alerta/lib/*
%dir %attr(0775,alerta,root) /var/lib/alerta

%pre common
getent group alerta >/dev/null || groupadd -r alerta
getent passwd alerta >/dev/null || \
    useradd -r -g alerta -d /var/lib/alerta -s /sbin/nologin \
    -c "Alerta monitoring tool" alerta
exit 0

%changelog
* Thu Mar 27 2013 Nick Satterly <nick.satterly@theguardian.com> - 3.0.0-3
- Package alerta relase 3.0 command-line tools
