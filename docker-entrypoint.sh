#!/bin/bash
set -ex

ADMIN_USER=${ADMIN_USERS%%,*}
ADMIN_PASSWORD=${ADMIN_PASSWORD:-alerta}
MAXAGE=${ADMIN_KEY_MAXAGE:-315360000}  # default=10 years

# Generate minimal server config, if not supplied
if [ ! -f "${ALERTA_SVR_CONF_FILE}" ]; then
  echo "# Create server configuration file."
  cat >"${ALERTA_SVR_CONF_FILE}" << EOF
SECRET_KEY = '$(< /dev/urandom tr -dc A-Za-z0-9_\!\@\#\$\%\^\&\*\(\)-+= | head -c 32)'
EOF
fi

# Init admin users and API keys
if [ -n "${ADMIN_USERS}" ]; then
  echo "# Create admin users."
  alertad user --all --password "${ADMIN_PASSWORD}"
  echo "# Create admin API keys."
  alertad key --all

  # Create user-defined API key, if required
  if [ -n "${ADMIN_KEY}" ]; then
    echo "# Create user-defined admin API key."
    alertad key --username "${ADMIN_USER}" --key "${ADMIN_KEY}" --duration "${MAXAGE}"
  fi
fi

# Generate minimal client config, if not supplied
if [ ! -f "${ALERTA_CONF_FILE}" ]; then
  echo "# Create client configuration file."
  cat >${ALERTA_CONF_FILE} << EOF
[DEFAULT]
endpoint = $ALERTA_ENDPOINT
EOF

  # Add API key to client config, if required
  if [ "${AUTH_REQUIRED}" == "True" ]; then
    echo "# Auth enabled; add admin API key to client configuration."
    API_KEY=$(alertad key --username "${ADMIN_USER}" --scope read --scope write:alerts --duration "${MAXAGE}" --text "Housekeeping")
    echo ${API_KEY}
    cat >>${ALERTA_CONF_FILE} << EOF
key = ${API_KEY}
EOF
  fi
fi

echo
echo 'Alerta init process complete; ready for start up.'
echo

exec "$@"
