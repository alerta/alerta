from alerta.database.backends.postgres import Backend as PGBackend


class Backend(PGBackend):

    def create_engine(self, app, uri, dbname=None, raise_on_error=True):
        uri = f"postgresql://{uri.split('://')[1]}"
        super().create_engine(app, uri, dbname, raise_on_error)

    def create_alert(self, alert):
        alert.attributes['custom_attribute'] = 'value'
        return super().create_alert(alert)
