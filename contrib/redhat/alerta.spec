%define name alerta
%define version 2.0.0
%define unmangled_version 2.0.0
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

%description
Alerta is an monitoring framework that uses a message broker
for alert transport, mongoDB as the alert status database,
elasticsearch for long-term alert archiving and has a
JavaScript web interface for an alert console.

%package server
Summary: Alerta monitoring framework
Group: Utilities/System
Requires: python-argparse, stomppy, pymongo, python-flask, PyYAML, pytz, python-boto, python-dynect-api
Requires: alerta-common, httpd, mongo-10gen-server, rabbitmq-server, logrotate
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
%setup -n %{name}-%{unmangled_version} -n %{name}-%{unmangled_version}

%build
python setup.py build

%install
python setup.py install --single-version-externally-managed --root=$RPM_BUILD_ROOT --record=INSTALLED_FILES

%__mkdir_p %{buildroot}%{_initrddir}/
%__mkdir_p %{buildroot}%{_sysconfdir}/%{name}/
%__cp etc/%{name}/%{name}.conf %{buildroot}%{_sysconfdir}/%{name}/%{name}.conf
%__install -m 0755 etc/init.d/* %{buildroot}%{_initrddir}/
%__mkdir_p %{buildroot}%{_sysconfdir}/httpd/conf.d/
%__install -m 0755 contrib/apache/%{name}.conf %{buildroot}%{_sysconfdir}/httpd/conf.d/%{name}.conf
%__mkdir_p %{buildroot}%{_var}/www/html/%{name}/
%__install -m 0755 contrib/apache/%{name}.wsgi %{buildroot}%{_var}/www/html/%{name}/%{name}.wsgi
%__mkdir_p %{buildroot}%{_var}/www/html/%{name}/dashboard/
%__cp -r dashboard/* %{buildroot}%{_var}/www/html/%{name}/dashboard/
%__install -m 0775 -d %{buildroot}%{_var}/log/%{name}
%__mkdir_p %{buildroot}%{_sysconfdir}/logrotate.d/
%__cp etc/%{name}.logrotate %{buildroot}%{_sysconfdir}/logrotate.d/%{name}
%__mkdir_p %{buildroot}%{_var}/run/%{name}

%clean
rm -rf $RPM_BUILD_ROOT

%files server
%defattr(-,root,root)
%config(noreplace) %{_sysconfdir}/%{name}/%{name}.conf
%config(noreplace) %{_sysconfdir}/httpd/conf.d/%{name}.conf
%config(noreplace) /var/www/html/%{name}/%{name}.wsgi
%{_var}/www/html/%{name}/dashboard/
%{_sysconfdir}/logrotate.d/%{name}
%dir %attr(775,alerta,apache) /var/log/%{name}
%dir %attr(-,alerta,alerta) /var/run/%{name}
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
%config(noreplace) %{_sysconfdir}/%{name}/%{name}.conf
%{_sysconfdir}/logrotate.d/%{name}
%dir %attr(775,alerta,apache) /var/log/%{name}
%dir %attr(-,alerta,alerta) /var/run/%{name}
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
for name in alerta alert-aws alert-dynect alert-ganglia alert-ircbot \
    alert-logger alert-mailer alert-notify alert-syslog alert-urlmon
do
    /sbin/chkconfig --add $name
done

%preun server
if [ "$1" = "0" ]; then
    for name in alerta alert-aws alert-dynect alert-ganglia alert-ircbot \
        alert-logger alert-mailer alert-notify alert-syslog alert-urlmon
    do
        /sbin/chkconfig $name off
        /sbin/chkconfig --del $name
    done
fi

%changelog
* Thu Mar 21 2013 Nick Satterly <nick.satterly@guardian.co.uk> - 2.0.0-1
- Initial package for alerta v2
