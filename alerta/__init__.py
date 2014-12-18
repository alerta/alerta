import pkg_resources
pkg_resources.declare_namespace(__name__)

version = pkg_resources.require("alerta-server")[0].version
