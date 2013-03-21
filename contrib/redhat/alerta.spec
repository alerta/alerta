%define name alerta
%define version 2.0.alpha.1
%define unmangled_version 2.0.alpha.1
%define release 1

Name: %{name}
Summary: Alerta monitoring framework
Version: %{version}
Release: %{release}
Source0: %{name}-%{unmangled_version}.tar.gz
License: Apache License 2.0
Group: Utilities/System
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
Prefix: %{_prefix}
BuildArch: noarch
Vendor: Nick Satterly <nick.satterly@guardian.co.uk>
Url: https://github.com/guardian/alerta
Requires: stomppy, pymongo, Flask, PyYAML, pytz, python-boto, python-dynect

%description
Alerta is an monitoring framework that uses a message broker
for alert transport, mongoDB as the alert status database,
elasticsearch for long-term alert archiving and has a
JavaScript web interface for an alert console.

%package server
Summary: Alerta monitoring framework
Group: Utilities/System
%description server
UNKNOWN

%package client
Summary: Alerta monitoring framework
Group: Utilities/System
%description client
UNKNOWN

%package common
Summary: Alerta monitoring framework
Group: Utilities/System
%description common
UNKNOWN

%prep
%setup -n %{name}-%{unmangled_version} -n %{name}-%{unmangled_version}

%build
python setup.py build

%install
python setup.py install --single-version-externally-managed --root=$RPM_BUILD_ROOT --record=INSTALLED_FILES

%__mkdir_p %{buildroot}%{_initrddir}/
%__install -m 0755 etc/init.d/* %{buildroot}%{_initrddir}/
%__install -m 0775 -d %{buildroot}%{_var}/log/%{name}
%__mkdir_p %{buildroot}%{_sysconfdir}/logrotate.d/
%__cp etc/%{name}.logrotate %{buildroot}%{_sysconfdir}/logrotate.d/%{name}
%__mkdir_p %{buildroot}%{_var}/run/%{name}

%clean
rm -rf $RPM_BUILD_ROOT

%files server
%defattr(-,root,root)
%{_bindir}/alerta
%{_bindir}/alerta-api
%{_bindir}/alert-aws
%{_bindir}/alert-dynect
%{_bindir}/alert-ganglia
%{_bindir}/alert-ircbot
%{_bindir}/alert-logger
%{_bindir}/alert-mailer
%{_bindir}/alert-notify
%{_bindir}/alert-snmptrap
%{_bindir}/alert-syslog
%{_bindir}/alert-urlmon

%files client
%defattr(-,root,root)
%{_bindir}/alert-query
%{_bindir}/alert-sender
%{_bindir}/alert-checker

%files common
%{python_sitelib}/*
%defattr(-,root,root)

%{_initrddir}/
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
for name in alerta alerta-api alert-aws alert-dynect alert-ganglia alert-ircbot \
    alert-logger alert-mailer alert-notify alert-syslog alert-urlmon
do
    /sbin/chkconfig --add $name
done

%preun server
if [ "$1" = "0" ]; then
    for name in alerta alerta-api alert-aws alert-dynect alert-ganglia alert-ircbot \
        alert-logger alert-mailer alert-notify alert-syslog alert-urlmon
    do
        /sbin/chkconfig $name off
        /sbin/chkconfig --del $name
    done
fi

%changelog
* Thu Mar 21 2013 Nick Satterly <nick.satterly@guardian.co.uk> - 2.0.0-1
- Initial package for alerta v2
