%{!?_with_teamcity: %define version 4.1.8}
%{!?_with_teamcity: %define release 1}

Name: alerta-server
Summary: Alerta monitoring system
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
Alerta is a monitoring system that consolidates alerts from
multiple sources like syslog, SNMP, Nagios, Riemann, AWS
CloudWatch and Pingdom, and displays them on an alert console.

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
cat > %{buildroot}%{_sysconfdir}/httpd/conf.d/alerta.conf << EOF
Listen 8080
WSGISocketPrefix /var/run/wsgi
<VirtualHost *:8080>
  ServerName localhost
  WSGIDaemonProcess alerta processes=5 threads=5
  WSGIProcessGroup alerta
  WSGIScriptAlias / /var/www/api.wsgi
  WSGIPassAuthorization On
  ErrorLog ${APACHE_LOG_DIR}/error.log
  CustomLog ${APACHE_LOG_DIR}/access.log combined
</VirtualHost>
<VirtualHost *:80>
  ProxyPass /api http://localhost:8080
  ProxyPassReverse /api http://localhost:8080
  DocumentRoot /var/www
</VirtualHost>
EOF

%__mkdir_p %{buildroot}/var/www
cat > %{buildroot}/var/www/api.wsgi << EOF
#!/usr/bin/env python
activate_this = '/opt/alerta/bin/activate_this.py'
execfile(activate_this, dict(__file__=activate_this))
from alerta.app import app as application
EOF

#prelink -u %{buildroot}/opt/alerta/bin/python

%clean
rm -rf %{buildroot}

%files
%defattr(-,root,root)
%config(noreplace) %{_sysconfdir}/httpd/conf.d/alerta.conf
%defattr(-,alerta,alerta)
/opt/alerta/bin/alerta
/opt/alerta/bin/alertad
%config(noreplace) /var/www/api.wsgi
/opt/alerta/bin/python*
/opt/alerta/bin/activate*
/opt/alerta/lib/*

%pre
getent group alerta >/dev/null || groupadd -r alerta
getent passwd alerta >/dev/null || \
    useradd -r -g alerta -d /var/lib/alerta -s /sbin/nologin \
    -c "Alerta monitoring system" alerta
exit 0

%changelog
* Thu Mar 12 2015 Nick Satterly <nick.satterly@theguardian.com> - 4.1.0-1
- Update RPM SPEC file for Release 4.1
