%define name alerta
%define version 2.0.alpha.1
%define unmangled_version 2.0.alpha.1
%define unmangled_version 2.0.alpha.1
%define release 1

Name: %{name}
Summary: Alerta monitoring framework
Version: %{version}
Release: %{release}
Source0: %{name}-%{unmangled_version}.tar.gz
License: Apache License 2.0
Group: Development/Libraries
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
Prefix: %{_prefix}
BuildArch: noarch
Vendor: Nick Satterly <nick.satterly@guardian.co.uk>
Url: https://github.com/guardian/alerta
%description
UNKNOWN

%package server
Summary: Alerta monitoring framework
%description server
UNKNOWN

%package client
Summary: Alerta monitoring framework
%description client
UNKNOWN

%package common
Summary: Alerta monitoring framework
%description common
UNKNOWN

%prep
%setup -n %{name}-%{unmangled_version} -n %{name}-%{unmangled_version}

%build
python setup.py build

%install
python setup.py install --single-version-externally-managed --root=$RPM_BUILD_ROOT --record=INSTALLED_FILES

%clean
rm -rf $RPM_BUILD_ROOT

%files server
%defattr(-,root,root)
/usr/local/bin/alert-aws
/usr/local/bin/alert-checker
/usr/local/bin/alert-dynect
/usr/local/bin/alert-ganglia
/usr/local/bin/alert-ircbot
/usr/local/bin/alert-logger
/usr/local/bin/alert-mailer
/usr/local/bin/alert-notify
/usr/local/bin/alert-query
/usr/local/bin/alert-snmptrap
/usr/local/bin/alert-syslog
/usr/local/bin/alert-urlmon
/usr/local/bin/alerta
/usr/local/bin/alerta-api

%files client
%defattr(-,root,root)
/usr/local/bin/alert-sender

%files common
/usr/local/lib/python2.6/dist-packages/alerta/
/usr/local/lib/python2.6/dist-packages/alerta-2.0.alpha.1.egg-info/
%defattr(-,root,root)
